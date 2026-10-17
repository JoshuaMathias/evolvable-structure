"""Run one implementation of a solution over that solution's cases, and record the result with its provenance.

A component is a folder under the evaluation directory with a ``score.py`` (``score_case(fn, case)``, optionally
``aggregate(rows)`` for a headline and ``load_cases()`` when the cases live elsewhere), ``cases.json`` (or
``cases.csv``) and ``impls/<name>.py`` exposing ``build(meter) -> fn``. The harness never imports a solution by
name, so a new implementation is one new function; ``--impl module:build`` also accepts one that lives outside
the repository. ``esoi run <component> --impl <name>`` drives it:

  * ``CallMeter`` counts every model call a run makes, so cost is checked against the harness, not guessed;
    ``--max-calls`` aborts a run that exceeds its budget (``BudgetExceeded``).
  * ``--only`` runs named cases, ``--sample N`` runs N cases spread over the strata (the same cases every time;
    a smaller N is a prefix of a larger one, so a cheap first run is part of the bigger run).
  * ``--record`` appends the summary to the results log with ``git_sha`` (suffixed ``-dirty`` when the measured
    code has uncommitted changes) and ``cases_sha`` (a hash of the case files), the provenance the leaderboard
    and the check (rules S16, S20) rely on.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import functools
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import Config
from .leaderboard import cases_digest

RESULT_COLUMNS = ["date", "component", "impl", "cases", "passed", "dev", "heldout", "model_calls",
                  "tokens_in", "tokens_out", "cost_usd", "seconds", "git_sha", "cases_sha", "model", "details"]


class BudgetExceeded(RuntimeError):
    """The run made more model calls than its budget allows."""


class CallMeter:
    """Counts model calls. ``wrap(provider)`` instruments the named methods in place."""

    def __init__(self, max_calls: Optional[int] = None):
        self.calls = 0
        self.max_calls = max_calls
        self.tokens_in = self.tokens_out = 0
        self.cost_usd = 0.0   # what a provider reports per call (informational on a subscription login)
        self.model: Optional[str] = None   # set by an implementation that pins a model, for the record

    def record(self, n: int = 1) -> None:
        self.calls += n
        if self.max_calls is not None and self.calls > self.max_calls:
            raise BudgetExceeded(f"model-call budget {self.max_calls} exceeded")

    def wrap(self, provider: Any, methods: Tuple[str, ...] = ("plan", "answer")) -> Any:
        """Count calls to ``methods`` of ``provider``; token and cost counters, when the provider keeps them as
        ``tokens_in``, ``tokens_out`` and ``cost_usd`` attributes, are added up from their per-call change."""
        if getattr(provider, "meter_wrapped", False):
            return provider
        for name in methods:
            original = getattr(provider, name, None)
            if original is None:
                continue

            def make(fn: Callable) -> Callable:
                @functools.wraps(fn)   # keeps the signature: callers may inspect it for optional kwargs
                def counted(*args, **kwargs):
                    self.record()
                    t_in, t_out, cost = (getattr(provider, n, 0) or 0 for n in ("tokens_in", "tokens_out", "cost_usd"))
                    try:
                        return fn(*args, **kwargs)
                    finally:
                        self.tokens_in += (getattr(provider, "tokens_in", 0) or 0) - t_in
                        self.tokens_out += (getattr(provider, "tokens_out", 0) or 0) - t_out
                        self.cost_usd += (getattr(provider, "cost_usd", 0) or 0) - cost
                return counted
            setattr(provider, name, make(original))
        provider.meter_wrapped = True
        return provider


def prepare_path(config: Config) -> None:
    """Make the repository and the evaluation folder importable (score and impl modules import each other)."""
    for entry in (str(config.evaluation), str(config.root), *(str(config.root / p) for p in config.python_path)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def discover_components(config: Config) -> List[str]:
    """A component is any folder under the evaluation directory with a ``score.py``: adding one needs no edit here."""
    if not config.evaluation.is_dir():
        return []
    return sorted(p.name for p in config.evaluation.iterdir() if (p / "score.py").is_file())


def load_impl(spec: str, component: str) -> Callable:
    """``--impl name`` -> ``<component>/impls/name.py``'s ``build``; ``module:function`` is also accepted."""
    if ":" in spec:
        module, _, attr = spec.partition(":")
        return getattr(importlib.import_module(module), attr)
    return importlib.import_module(f"{component}.impls.{spec}").build


def stratified_sample(cases: List[dict], n: int, seed: int = 0) -> List[dict]:
    """``n`` cases spread over the strata (``stratum``, else ``dataset``, else ``area``), the same cases every
    time for one seed. A smaller ``n`` is a prefix of a larger one."""
    import random
    rng = random.Random(seed)
    groups: Dict[str, List[dict]] = {}
    for case in sorted(cases, key=lambda c: str(c["id"])):
        groups.setdefault(case.get("stratum") or case.get("dataset") or case.get("area") or "", []).append(case)
    for group in groups.values():
        rng.shuffle(group)
    picked: List[dict] = []
    while len(picked) < n and any(groups.values()):
        for name in sorted(groups):
            if groups[name] and len(picked) < n:
                picked.append(groups[name].pop(0))
    return sorted(picked, key=lambda c: str(c["id"]))


def load_cases(component: str, config: Config) -> List[dict]:
    """The component's cases: the ``load_cases()`` of its score module when it has one (a dataset folder another
    harness also reads), else ``cases.json``, or ``cases.csv`` when the dataset is reviewed as a sheet (a
    ``heldout`` cell of ``yes`` marks a held-out case)."""
    prepare_path(config)
    score = importlib.import_module(f"{component}.score")
    if hasattr(score, "load_cases"):
        return score.load_cases()
    folder = config.evaluation / component
    if (folder / "cases.json").exists():
        return json.loads((folder / "cases.json").read_text(encoding="utf-8"))
    with (folder / "cases.csv").open(newline="", encoding="utf-8") as fh:
        cases = list(csv.DictReader(fh))
    for case in cases:
        case["heldout"] = (case.get("heldout") or "").strip().lower() == "yes"
    return cases


def git(config: Config, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=config.root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def current_sha(config: Config) -> str:
    """The short commit, suffixed ``-dirty`` when the measured code has uncommitted changes (the results log
    itself is not the code under test)."""
    sha = git(config, "rev-parse", "--short", "HEAD")
    if sha and git(config, "status", "--porcelain", "--untracked-files=no", "--", *config.code_paths,
                   config.evaluation_dir, f":(exclude){config.results}"):
        sha += "-dirty"
    return sha


def record_result(summary: Dict[str, Any], config: Config, date: Optional[str] = None,
                  path: Optional[Path] = None, model_env: Optional[str] = None) -> Dict[str, Any]:
    """Append one run's summary to the results log, the source of truth for metrics. Returns the row written."""
    comp = summary.get("component", "")
    model = summary.get("model") or (model_env if summary.get("model_calls") and model_env else
                                     ("unknown" if summary.get("model_calls") else "none"))
    row = dict(summary, date=date or datetime.date.today().isoformat(),
               cost_usd=summary.get("cli_reported_cost_usd", summary.get("cost_usd", 0.0)),
               git_sha=current_sha(config), model=model, cases_sha=cases_digest(comp, config.evaluation))
    target = Path(path) if path else config.results_path
    new = not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESULT_COLUMNS, extrasaction="ignore", lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow(row)
    return row


def run_component(component: str, scorer: Callable, argv: List[str], config: Config,
                  say: Callable[[str], None] = print) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Drive one implementation over a component's cases; print each case; optionally record. Returns (summary, rows)."""
    ap = argparse.ArgumentParser(prog=f"esoi run {component}", description=f"Evaluate the {component} component on its own.")
    ap.add_argument("--impl", required=True, help="implementation name (impls/<name>.py) or module:build")
    ap.add_argument("--only", default=None, help="comma-separated case ids")
    ap.add_argument("--sample", type=int, default=None, metavar="N",
                    help="run N cases spread over the strata (same cases every time; N=3 is a prefix of N=10)")
    ap.add_argument("--max-calls", type=int, default=None, help="abort when model calls exceed this")
    ap.add_argument("--out", default=None, help="results json path (default: a temporary folder)")
    ap.add_argument("--record", action="store_true", help="append the summary to the results log")
    args = ap.parse_args(argv)
    cases = load_cases(component, config)
    if args.only:
        keep = {c.strip() for c in args.only.split(",")}
        cases = [c for c in cases if c["id"] in keep]
    if args.sample:
        cases = stratified_sample(cases, args.sample)
    budget = args.max_calls if args.max_calls is not None else "none"
    say(f"{component}: {len(cases)} case(s), impl {args.impl}, model-call budget {budget}: "
        f"{', '.join(str(c['id']) for c in cases[:12])}{' ...' if len(cases) > 12 else ''}")
    meter = CallMeter(args.max_calls)
    fn = load_impl(args.impl, component)(meter)
    rows: List[Dict[str, Any]] = []
    started = time.time()
    for case in cases:
        before, t0 = meter.calls, time.time()
        try:
            row = scorer(fn, case)
        except BudgetExceeded:
            raise
        except Exception as exc:
            row = dict(ok=False, note=f"{type(exc).__name__}: {exc}")
        row.update(id=case["id"], area=case.get("area"), calls=meter.calls - before, seconds=round(time.time() - t0, 1))
        rows.append(row)
        say(f"[{row['id']:9}] {'PASS' if row['ok'] else 'FAIL'} calls={row['calls']} {row.get('got', '')} | {row.get('note', '')}")
    passed = sum(bool(r["ok"]) for r in rows)
    held = [r for r, c in zip(rows, cases) if c.get("heldout")]
    summary = dict(component=component, impl=args.impl, cases=len(rows), passed=passed,
                   dev=f"{sum(bool(r['ok']) for r in rows if r not in held)}/{len(rows) - len(held)}",
                   heldout=f"{sum(bool(r['ok']) for r in held)}/{len(held)}",
                   model_calls=meter.calls, tokens_in=meter.tokens_in, tokens_out=meter.tokens_out,
                   cli_reported_cost_usd=round(meter.cost_usd, 4), seconds=round(time.time() - started, 1),
                   model=meter.model)
    say(f"\n{component} / {args.impl}: {passed}/{len(rows)} passed (dev {summary['dev']}, held-out "
        f"{summary['heldout']}), {meter.calls} model calls, {meter.tokens_in} in / {meter.tokens_out} out tokens, "
        f"reported cost ${summary['cli_reported_cost_usd']}, {summary['seconds']}s")
    score = importlib.import_module(f"{component}.score")
    if hasattr(score, "aggregate"):
        say(f"{component}: {score.aggregate(rows)}")
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(summary=summary, rows=rows), indent=1), encoding="utf-8")
        say(f"results: {out}")
    if args.record:
        record_result(summary, config)
        say(f"recorded in {config.results}")
    return summary, rows


def run_cli(argv: List[str], config: Config, say: Callable[[str], None] = print) -> int:
    """``esoi run <component> --impl <name> [flags]``."""
    prepare_path(config)
    components = discover_components(config)
    if not argv or argv[0] not in components:
        say("usage: esoi run <component> --impl <name> [--only IDS] [--sample N] [--max-calls N] [--record]")
        say("components: " + (", ".join(components) or "none found under " + config.evaluation_dir))
        return 2
    score = importlib.import_module(f"{argv[0]}.score")
    run_component(argv[0], score.score_case, argv[1:], config, say)
    return 0
