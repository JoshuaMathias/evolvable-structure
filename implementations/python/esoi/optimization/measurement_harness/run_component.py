"""Run one implementation of a solution over that solution's cases, and record the result with its provenance.

A component is a folder under the evaluation directory with a ``score.py`` (``score_case(fn, case)``, optionally
``aggregate(rows)`` for a headline, recorded as the row's ``details``, and ``load_cases()`` when the cases live elsewhere), ``cases.json`` (or
``cases.csv``) and ``impls/<name>.py`` exposing ``build(meter) -> fn``. The harness never imports a solution by
name, so a new implementation is one new function; ``--impl module:build`` also accepts one that lives outside
the repository. ``esoi run <component> --impl <name>`` drives it:

  * ``CallMeter`` counts every model call a run makes, so cost is checked against the harness, not guessed;
    ``--max-calls`` aborts a run that exceeds its budget (``BudgetExceeded``).
  * ``--only`` runs named cases, ``--sample N`` runs N cases spread over the strata (the same cases every time;
    a smaller N is a prefix of a larger one, so a cheap first run is part of the bigger run).
  * ``--record`` appends the summary to the results log with ``git_sha`` (suffixed ``-dirty`` when the measured
    code has uncommitted changes) and ``cases_sha`` (a hash of the case files), the provenance the leaderboard
    and the check (rules S16, S20) rely on, and ``sample`` (``sample:N`` for ``--sample N``, ``only:ids`` for
    ``--only``, blank for the full set), so the leaderboard compares arms only on the same cases.
  * an implementation needs no ``impls/<name>.py`` wrapper when the code declares it (``@implementation`` in
    ``esoi.runtime.implementation_selection.declare``): the harness imports the module the records name, and calls the implementation with each case's
    ``args`` as keyword arguments (a ``score.py`` may define ``adapt(implementation, meter) -> fn`` to say otherwise).
    Wrapper files stay for baselines and reference arms, and for implementations that need the meter.
  * an arm that meters a deterministic stand-in for a model (it counts the calls the real model would make, with no
    tokens) declares ``SIMULATED = True``: its runs record model ``simulated`` and cost 0.0, it is never treated as paid,
    and the leaderboard compares it on calls.
  * ``esoi run --stale`` re-runs a stale arm on the sample its latest row used (``--full`` runs the whole set), and a
    rival on the selected arm's sample, so a re-record stays comparable.
"""
from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import circumstances
from esoi.optimization.leaderboard.case_identity import cases_digest
from esoi.optimization.measurement_harness import access
from esoi.optimization.measurement_harness import balance
from esoi.optimization.measurement_harness import cassette as cassettes
from esoi.optimization.measurement_harness import code_provenance
from esoi.optimization.measurement_harness import run_log
from esoi.optimization.measurement_harness.arm_loading import load_impl
from esoi.optimization.measurement_harness.call_meter import CallMeter
from esoi.optimization.measurement_harness.case_loading import load_cases, sample_label, stratified_sample
from esoi.optimization.measurement_harness.check_guards import check_guards
from esoi.optimization.measurement_harness.offline_guard import OfflineGuard, refuse_offline_network
from esoi.optimization.measurement_harness.per_case_log import write_per_case
from esoi.optimization.measurement_harness.record_result import record_result
from esoi.optimization.measurement_harness.record_slices import record_slices
from esoi.optimization.measurement_harness.run_cost import run_cost
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.optimization.when_metrics_are_run import run_guards
from esoi.optimization.when_metrics_are_run.paid_gating import BudgetExceeded, SIMULATED_MODEL, declared_live, declares_simulated, impl_path
from esoi.runtime.consumer_check import foundation
from esoi.runtime.implementation_selection import variants
from esoi.structure.intent_registry.config import Config


def cassette_folder(config: Config, given: Optional[str]) -> Optional[Path]:
    """The cassette folder: ``--cassette``, else ``[harness] cassette`` (relative to the repository root), else None (off)."""
    chosen = given or (config.harness.get("cassette") if isinstance(config.harness, dict) else "") or ""
    if not chosen:
        return None
    path = Path(str(chosen)).expanduser()
    return path if path.is_absolute() else (config.root / path if not given else Path(str(chosen)))


def details_text(headline: Any, limit: int = 300) -> str:
    """The recorded ``details`` cell for a component's ``aggregate(rows)``: a mapping becomes ``key=value`` pairs joined by
    ``; `` (secondary numbers such as nDCG next to the pass count), anything else its text; clipped to ``limit``."""
    if isinstance(headline, dict):
        text = "; ".join(f"{key}={value}" for key, value in headline.items())
    else:
        text = "" if headline is None else str(headline)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 3] + "..."


def run_component(component: str, scorer: Callable, argv: List[str], config: Config,
                  say: Callable[[str], None] = print, guards: bool = True) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Drive one implementation over a component's cases; print each case; optionally record. Returns (summary, rows)."""
    ap = argparse.ArgumentParser(prog=f"esoi run {component}", description=f"Evaluate the {component} component on its own.")
    ap.add_argument("--impl", required=True, help="implementation name (impls/<name>.py) or module:build")
    ap.add_argument("--only", default=None, help="comma-separated case ids")
    ap.add_argument("--failed", action="store_true",
                    help="run only the cases whose latest run (of this implementation, on these cases) failed; cannot be combined with --only or --sample")
    ap.add_argument("--keep-going", action="store_true",
                    help="run past a failing case; without it an unrecorded run stops at the first failure so the implementation can be improved at once")
    ap.add_argument("--fresh", action="store_true",
                    help="run every case, including ones already run for this implementation version (a --sample or whole run reuses those)")
    ap.add_argument("--sample", type=int, default=None, metavar="N",
                    help="run N cases spread over the strata (same cases every time; N=3 is a prefix of N=10)")
    ap.add_argument("--max-calls", type=int, default=None, help="abort when model calls exceed this")
    ap.add_argument("--cassette", default=None, metavar="DIR",
                    help="record every wrapped model call in DIR and replay a call it already holds without calling the model (default: [harness] cassette, else off)")
    ap.add_argument("--cassette-only", action="store_true",
                    help="with a cassette, error on a call it does not hold: proves a variant that should be free is free")
    ap.add_argument("--out", default=None, help="results json path (default: a temporary folder)")
    ap.add_argument("--record", action="store_true", help="append the summary to the results log")
    ap.add_argument("--force", default=None, metavar="REASON",
                    help="run although a guard refuses (a perfect arm already caps this one, or a public result exists); the reason is recorded in details")
    ap.add_argument("--differs", default=None, metavar="WHAT",
                    help='run although a public result exists, saying what differs: "harness: ...", "prompt: ...", "settings", "corpus" or "metric"')
    args = ap.parse_args(argv)
    cases = load_cases(component, config)
    whole = len(cases)
    try:
        circs = circumstances.for_component(config, component)   # an unreadable circumstance fails here, before any model call
        circumstances.check_fields(circs, cases)
    except ValueError as exc:
        raise RunError(str(exc)) from exc
    impl = args.impl if ":" in args.impl else variants.canonical(args.impl)   # one spelling of a variant in every record
    refuse_offline_network(config, component, impl)
    runs_path, cases_sha = config.root / config.runs_log, cases_digest(component, config.evaluation)
    if args.failed:
        if args.only or args.sample is not None:
            raise RunError("--failed already names the cases to run (the ones that failed last); drop --only or --sample")
        failing = run_log.failed_cases(runs_path, component, impl, cases_sha)
        if not failing:
            raise RunError(f"no failing case is logged for {impl} on these cases, so there is nothing to rerun "
                           f"(the log is {config.runs_log}); run it without --failed")
        args.only = ",".join(failing)
    elif guards and not (args.only or args.sample is not None or args.record or args.force is not None):
        unsolved = run_guards.unsolved_cases(config, component, impl)
        if unsolved:   # the failing cases are rerun by themselves; the whole set waits until they pass
            say(f"{len(unsolved)} case(s) failed in the latest run and have not passed since, so only those run ({', '.join(unsolved[:8])}"
                f"{' ...' if len(unsolved) > 8 else ''}); pass --force \"reason\" to run the whole set")
            args.only = ",".join(unsolved)
    if args.only:
        keep = {c.strip() for c in args.only.split(",")}
        cases = [c for c in cases if c["id"] in keep]
        if not cases:
            raise RunError(f"--only {args.only!r} matches no case of {component}")
    if args.sample is not None:
        if args.sample < 1:
            raise RunError("--sample needs a number of cases of at least 1")
        cases = stratified_sample(cases, args.sample)
    sample = sample_label(args, cases, whole)
    budget = args.max_calls if args.max_calls is not None else "none"
    say(f"{component}: {len(cases)} case(s), impl {args.impl}, model-call budget {budget}: "
        f"{', '.join(str(c['id']) for c in cases[:12])}{' ...' if len(cases) > 12 else ''}")
    notes = check_guards(config, component, impl, sample, args, say) if guards else []
    meter = CallMeter(args.max_calls)
    guard = None if declared_live(config, component, impl, args.max_calls) else OfflineGuard(meter)
    meter.offline = guard is not None
    chosen = cassette_folder(config, args.cassette)
    if args.cassette_only and not chosen:
        raise RunError("--cassette-only needs a cassette: pass --cassette DIR or set [harness] cassette in the configuration")
    if chosen:
        try:
            meter.cassette = cassettes.Cassette(chosen, only=args.cassette_only)
        except ValueError as exc:
            raise RunError(str(exc)) from exc
    meter.access = config.balance.get(component)
    fn = load_impl(impl, component, config)(meter)
    score = importlib.import_module(f"{component}.score")
    builds = foundation.declared(config, component) if not (args.only or args.sample is not None) else []   # composition is for whole sets
    if foundation.declared(config, component) and not builds:
        say("note: a sampled or --only run scores the consumer's own cases only; the foundation parts are not composed")
    git_sha = code_provenance.current_sha(config, component, impl)
    reuse = {} if (args.fresh or args.only) else run_log.reusable(runs_path, component, impl, cases_sha, git_sha)
    stop_at_fail = not (args.keep_going or args.record)   # a recorded run is a whole measurement; a development run is for fixing
    log = run_log.RunLog(runs_path, dict(component=component, impl=impl, cases_sha=cases_sha, git_sha=git_sha, sample=sample,
                                         recorded="yes" if args.record else "no"))
    log.begin()
    rows: List[Dict[str, Any]] = []
    reused = dict(calls=0, tokens_in=0, tokens_out=0, cost=0.0, seconds=0.0, cases=0)
    stopped, parts, own_at = "", [], None
    started = time.time()
    if guard:
        guard.start()
    try:
        for case in cases:
            before, t0, in0, out0, cost0 = meter.calls, time.time(), meter.tokens_in, meter.tokens_out, meter.cost_usd
            replayed0, reads0 = meter.calls_replayed, meter.reads.copy()
            if str(case["id"]) in reuse:
                row = dict(reuse[str(case["id"])])
                spent = float(row.pop("cost", 0) or 0)
                for name, key in (("calls", "calls"), ("tokens_in", "tokens_in"), ("tokens_out", "tokens_out"), ("seconds", "seconds")):
                    reused[name] += row.get(key) or 0
                reused["cost"] += spent
                reused["cases"] += 1
                rows.append(row)
                log.case(row, spent, reused=True)
                say(f"[{row['id']:9}] {'PASS' if row['ok'] else 'FAIL'} reused from an earlier run of this implementation version")
                continue
            try:
                row = scorer(fn, case)
            except BudgetExceeded:
                raise
            except Exception as exc:
                row = dict(ok=False, note=f"{type(exc).__name__}: {exc}")
            row.update(id=case["id"], area=case.get("area"), calls=meter.calls - before, seconds=round(time.time() - t0, 1),
                       tokens_in=meter.tokens_in - in0, tokens_out=meter.tokens_out - out0)
            if meter.access and (bad := access.violation(meter.reads.minus(reads0), meter.access)):   # a read gate: the request fails
                row.update(ok=False, note=f"{bad}; {row.get('note', '')}".strip("; "))
            if meter.calls_replayed > replayed0:
                row["calls_replayed"] = meter.calls_replayed - replayed0
            rows.append(row)
            log.case(row, meter.cost_usd - cost0)
            say(f"[{row['id']:9}] {'PASS' if row['ok'] else 'FAIL'} calls={row['calls']} {row.get('got', '')} | {row.get('note', '')}")
            if stop_at_fail and not row["ok"]:
                stopped = f"stopped at the first failing case, {row['id']}"
                break
        own_at = (meter.calls, meter.tokens_in, meter.tokens_out, meter.cost_usd, time.time())   # the consumer's own spend, before the foundation part
        if builds and not stopped:   # the foundation's part: reused when current, else run through the foundation's own scorer
            parts = foundation.measure(config, component, impl, fn, getattr(score, "foundation_fn", None), meter, say)
    except BaseException as exc:   # Ctrl-C, a spent call budget or a crash: what was scored stays in the log
        log.end(f"stopped: {type(exc).__name__}")
        raise
    finally:
        if guard:
            guard.stop()
    log.end("done" if not stopped else stopped.replace("stopped at", "stopped: at"))
    cases = cases[:len(rows)]
    passed = sum(bool(r["ok"]) for r in rows)
    held = [r for r, c in zip(rows, cases) if c.get("heldout")]
    summary = dict(component=component, impl=impl, cases=len(rows), passed=passed,
                   dev=f"{sum(bool(r['ok']) for r in rows if r not in held)}/{len(rows) - len(held)}",
                   heldout=f"{sum(bool(r['ok']) for r in held)}/{len(held)}",
                   model_calls=own_at[0] + reused["calls"], tokens_in=own_at[1] + reused["tokens_in"],
                   tokens_out=own_at[2] + reused["tokens_out"],
                   cli_reported_cost_usd=round(own_at[3] + reused["cost"], 4),
                   seconds=round(own_at[4] - started + reused["seconds"], 1),
                   model=SIMULATED_MODEL if declares_simulated(impl_path(config, component, variants.base_of(impl))) else meter.model,
                   sample=sample)
    cost = run_cost(config, summary, summary["model"])
    if parts:
        summary.update(foundation.blend(summary, cost, parts, builds, config.balance.get(component)))
        passed, total, cost = summary["passed"], summary["cases"], run_cost(config, summary, summary["model"])
    else:
        total = len(rows)
        summary.update(balance.balanced(passed, total, cost, summary["seconds"], config.balance.get(component)))
    say(f"\n{component} / {args.impl}: {passed}/{total} passed (dev {summary['dev']}, held-out "
        f"{summary['heldout']}), {summary['model_calls']} model calls, {summary['tokens_in']} in / {summary['tokens_out']} out tokens, "
        f"cost {'$' + str(cost) if cost != '' else 'unknown (no price for the model in `prices`)'}, {summary['seconds']}s")
    if "balanced" in summary:
        say(f"balanced score {summary['balanced']} = accuracy {summary['accuracy']}, ${summary['cost_per_case']}/case, "
            f"{summary['seconds_per_case']}s/case (weights and budgets: [balance.{component}] in the configuration)")
    if hasattr(score, "aggregate"):
        headline = score.aggregate(rows)
        say(f"{component}: {headline}")
        summary["details"] = details_text(headline)
    if hasattr(score, "disqualify") and (barred := score.disqualify(rows)):   # a hard fail: the run records a zero balanced score, so it cannot rank
        summary["balanced"] = 0.0
        summary["details"] = f"DISQUALIFIED {barred}; {summary.get('details', '')}".strip("; ")
        say(f"{component}: DISQUALIFIED, {barred}")
    if meter.attempted:
        notes.append(f"offline guard refused {meter.attempted} attempted model call(s) (metered {meter.calls}); declare the arm live (PAID = True) to call a model")
    if meter.calls_replayed:
        notes.append(f"replayed {meter.calls_replayed} model call(s) from the cassette (replayed cost: {meter.replayed_tokens_in} in / "
                     f"{meter.replayed_tokens_out} out tokens, ${round(meter.replayed_cost_usd, 4)}, {round(meter.replayed_seconds, 1)}s; "
                     "not part of this row's spend)")
    if reused["cases"]:
        notes.append(f"reused {reused['cases']} case(s) already run for this implementation version")
    notes.extend(foundation.note_for(p, next(f.share for f in builds if f.name == p.name)) for p in parts)
    if meter.reads.calls or meter.reads.records:
        notes.append(f"source reads: {meter.reads.records} records, {meter.reads.bytes} bytes, {meter.reads.calls} calls")
    if notes:
        summary["details"] = run_guards.note_details(summary.get("details", ""), notes)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(summary=summary, rows=rows), indent=1), encoding="utf-8")
        say(f"results: {out}")
    if stopped:
        say(f"{stopped}: fix it and rerun just the failing case(s) with --failed; every case run is saved in {config.runs_log} "
            "(this run is not recorded; add --keep-going to run past failures)")
    if args.record:
        record_result(summary, config)
        say(f"recorded in {config.results}")
        if not sample.startswith("only:"):
            for part in record_slices(config, component, circs, summary, cases, rows):
                say(f"recorded {part['sample']}: {part['passed']}/{part['cases']} (derived from this run)")
        if parts:   # the foundation's per-case outcomes join the consumer's log, so the paired test sees every case the number rests on
            key = dict(component=component, impl=summary["impl"], cases_sha=cases_digest(component, config.evaluation),
                       circumstances_sha=circumstances.digest(circs) if circs else "", sample=summary["sample"])
            joined = [dict(key, case_id=f"{p.name}:{r['case_id']}", heldout="", ok=r["ok"], calls=r.get("calls", 0), tokens_in=0,
                           tokens_out=0, seconds=r.get("seconds", 0), circumstances="", score="") for p in parts for r in p.per_case]
            if joined:
                write_per_case(config, joined)
    return summary, rows
