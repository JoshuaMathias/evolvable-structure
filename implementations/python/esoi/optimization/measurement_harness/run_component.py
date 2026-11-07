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
from esoi.optimization.measurement_harness import balance
from esoi.optimization.measurement_harness import cassette as cassettes
from esoi.optimization.measurement_harness import code_provenance
from esoi.optimization.measurement_harness import run_log
from esoi.optimization.measurement_harness.arm_loading import load_impl
from esoi.optimization.measurement_harness.call_meter import CallMeter
from esoi.optimization.measurement_harness.case_loading import load_cases, sample_label
from esoi.optimization.measurement_harness.check_guards import check_guards
from esoi.optimization.measurement_harness.offline_guard import OfflineGuard, refuse_offline_network
from esoi.optimization.measurement_harness.per_case_log import write_per_case
from esoi.optimization.measurement_harness.record_result import record_result
from esoi.optimization.measurement_harness.record_slices import record_slices
from esoi.optimization.measurement_harness.run_arguments import build_parser, name_cases_to_run, narrow_cases
from esoi.optimization.measurement_harness.run_cases import run_cases
from esoi.optimization.measurement_harness.run_cost import run_cost
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.optimization.when_metrics_are_run import run_guards
from esoi.optimization.when_metrics_are_run.paid_gating import SIMULATED_MODEL, declared_live, declares_simulated, impl_path
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


def make_meter(config: Config, component: str, impl: str, args: argparse.Namespace) -> Tuple[CallMeter, Optional[OfflineGuard]]:
    """The call meter of a run, with its offline guard (None when the arm is declared live) and its cassette, if any."""
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
    return meter, guard


def build_summary(component: str, impl: str, config: Config, rows: List[Dict[str, Any]], cases: List[Dict[str, Any]], reused: Dict[str, Any],
                  own_at: Tuple, started: float, meter: CallMeter, sample: str) -> Dict[str, Any]:
    """The run's summary row: counts, spend (own plus reused) and the model."""
    held = [r for r, c in zip(rows, cases) if c.get("heldout")]
    return dict(component=component, impl=impl, cases=len(rows), passed=sum(bool(r["ok"]) for r in rows),
                dev=f"{sum(bool(r['ok']) for r in rows if r not in held)}/{len(rows) - len(held)}",
                heldout=f"{sum(bool(r['ok']) for r in held)}/{len(held)}",
                model_calls=own_at[0] + reused["calls"], tokens_in=own_at[1] + reused["tokens_in"],
                tokens_out=own_at[2] + reused["tokens_out"],
                cli_reported_cost_usd=round(own_at[3] + reused["cost"], 4),
                seconds=round(own_at[4] - started + reused["seconds"], 1),
                model=SIMULATED_MODEL if declares_simulated(impl_path(config, component, variants.base_of(impl))) else meter.model,
                sample=sample)


def score_summary(summary: Dict[str, Any], config: Config, component: str, parts: list, builds: list, rows: list) -> Tuple[int, int, Any]:
    """Add the balanced score (blended with the foundation's parts when there are any); returns (passed, total, cost)."""
    cost = run_cost(config, summary, summary["model"])
    if parts:
        summary.update(foundation.blend(summary, cost, parts, builds, config.balance.get(component)))
        return summary["passed"], summary["cases"], run_cost(config, summary, summary["model"])
    summary.update(balance.balanced(summary["passed"], len(rows), cost, summary["seconds"], config.balance.get(component)))
    return summary["passed"], len(rows), cost


def say_totals(summary: Dict[str, Any], component: str, arm: str, passed: int, total: int, cost: Any, parts: list,
               say: Callable[[str], None]) -> None:
    """Print the run's headline line and the notes that explain how to read it."""
    say(f"\n{component} / {arm}: {passed}/{total} passed (dev {summary['dev']}, held-out "
        f"{summary['heldout']}), {summary['model_calls']} model calls, {summary['tokens_in']} in / {summary['tokens_out']} out tokens, "
        f"cost {'$' + str(cost) if cost != '' else 'unknown (no price for the model in `prices`)'}, {summary['seconds']}s")
    if parts:   # the composed headline weights each part by its share, so its counts are not the raw ones that dev and held-out add up
        raw = foundation.sum_ratio([summary["dev"], summary["heldout"]])
        say(f"note: {passed}/{total} is the share-weighted equivalent (accuracy times cases); the raw counts are {raw} cases passed, "
            f"dev {summary['dev']} and held-out {summary['heldout']}")
    if not summary["model_calls"] and cost not in ("", 0, 0.0):
        say(f"note: no model was called, so the ${cost} is not money spent: it is the charge the arm's meter priced from the configuration "
            f"(store size, selected context size, source reads), which the balanced score weighs as cost")
    if "balanced" in summary:
        say(f"balanced score {summary['balanced']} = accuracy {summary['accuracy']}, ${summary['cost_per_case']}/case, "
            f"{summary['seconds_per_case']}s/case (weights and budgets: [balance.{component}] in the configuration)")


def add_component_headline(summary: Dict[str, Any], score: Any, rows: list, component: str, say: Callable[[str], None]) -> None:
    """The component's own headline (``aggregate``) and its hard fail (``disqualify``), when its scorer defines them."""
    if hasattr(score, "aggregate"):
        headline = score.aggregate(rows)
        say(f"{component}: {headline}")
        summary["details"] = details_text(headline)
    if hasattr(score, "disqualify") and (barred := score.disqualify(rows)):   # a hard fail: the run records a zero balanced score, so it cannot rank
        summary["balanced"] = 0.0
        summary["details"] = f"DISQUALIFIED {barred}; {summary.get('details', '')}".strip("; ")
        say(f"{component}: DISQUALIFIED, {barred}")


def run_notes(meter: CallMeter, reused: Dict[str, Any], parts: list, builds: list) -> List[str]:
    """The notes a run adds to its details: refused calls, replays, reused cases, foundation parts and source reads."""
    notes: List[str] = []
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
    return notes


def record_run(summary: Dict[str, Any], config: Config, component: str, circs: Any, cases: list, rows: list, parts: list,
               say: Callable[[str], None]) -> None:
    """Append the summary to the results log, with the derived slices and the foundation's per-case outcomes."""
    record_result(summary, config)
    say(f"recorded in {config.results}")
    if not summary["sample"].startswith("only:"):
        for part in record_slices(config, component, circs, summary, cases, rows):
            say(f"recorded {part['sample']}: {part['passed']}/{part['cases']} (derived from this run)")
    if parts:   # the foundation's per-case outcomes join the consumer's log, so the paired test sees every case the number rests on
        key = dict(component=component, impl=summary["impl"], cases_sha=cases_digest(component, config.evaluation),
                   circumstances_sha=circumstances.digest(circs) if circs else "", sample=summary["sample"])
        joined = [dict(key, case_id=f"{p.name}:{r['case_id']}", heldout="", ok=r["ok"], calls=r.get("calls", 0), tokens_in=0,
                       tokens_out=0, seconds=r.get("seconds", 0), circumstances="", score="") for p in parts for r in p.per_case]
        if joined:
            write_per_case(config, joined)


def finish_run(summary: Dict[str, Any], rows: list, notes: list, args: argparse.Namespace, config: Config, stopped: str,
               say: Callable[[str], None]) -> None:
    """Fold the notes into the details, write ``--out`` and say how a stopped run is continued."""
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


def open_run(component: str, argv: List[str], config: Config, say: Callable[[str], None], guards: bool):
    """Read the command line and choose the cases: ``(args, cases, circumstances, impl, sample label, cases digest)``."""
    args = build_parser(component).parse_args(argv)
    cases = load_cases(component, config)
    whole = len(cases)
    try:
        circs = circumstances.for_component(config, component)   # an unreadable circumstance fails here, before any model call
        circumstances.check_fields(circs, cases)
    except ValueError as exc:
        raise RunError(str(exc)) from exc
    impl = args.impl if ":" in args.impl else variants.canonical(args.impl)   # one spelling of a variant in every record
    refuse_offline_network(config, component, impl)
    cases_sha = cases_digest(component, config.evaluation)
    name_cases_to_run(args, config, component, impl, cases_sha, say, guards)
    cases = narrow_cases(args, component, cases)
    sample = sample_label(args, cases, whole)
    budget = args.max_calls if args.max_calls is not None else "none"
    say(f"{component}: {len(cases)} case(s), impl {args.impl}, model-call budget {budget}: "
        f"{', '.join(str(c['id']) for c in cases[:12])}{' ...' if len(cases) > 12 else ''}")
    return args, cases, circs, impl, sample, cases_sha


def run_component(component: str, scorer: Callable, argv: List[str], config: Config,
                  say: Callable[[str], None] = print, guards: bool = True) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Drive one implementation over a component's cases; print each case; optionally record. Returns (summary, rows)."""
    args, cases, circs, impl, sample, cases_sha = open_run(component, argv, config, say, guards)
    runs_path = config.root / config.runs_log
    notes = check_guards(config, component, impl, sample, args, say) if guards else []
    meter, guard = make_meter(config, component, impl, args)
    fn = load_impl(impl, component, config)(meter)
    score = importlib.import_module(f"{component}.score")
    builds = foundation.declared(config, component) if not (args.only or args.sample is not None) else []   # composition is for whole sets
    if foundation.declared(config, component) and not builds:
        say("note: a sampled or --only run scores the consumer's own cases only; the foundation parts are not composed")
    git_sha = code_provenance.current_sha(config, component, impl)
    reuse = {} if (args.fresh or args.only) else run_log.reusable(runs_path, component, impl, cases_sha, git_sha)
    log = run_log.RunLog(runs_path, dict(component=component, impl=impl, cases_sha=cases_sha, git_sha=git_sha, sample=sample,
                                         recorded="yes" if args.record else "no"))
    log.begin()
    parts: list = []
    started = time.time()
    if guard:
        guard.start()
    try:
        # a recorded run is a whole measurement; a development run is for fixing
        rows, reused, stopped = run_cases(cases, scorer, fn, meter, reuse, log, say, not (args.keep_going or args.record))
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
    summary = build_summary(component, impl, config, rows, cases, reused, own_at, started, meter, sample)
    passed, total, cost = score_summary(summary, config, component, parts, builds, rows)
    say_totals(summary, component, args.impl, passed, total, cost, parts, say)
    add_component_headline(summary, score, rows, component, say)
    finish_run(summary, rows, notes + run_notes(meter, reused, parts, builds), args, config, stopped, say)
    if args.record:
        record_run(summary, config, component, circs, cases, rows, parts, say)
    return summary, rows
