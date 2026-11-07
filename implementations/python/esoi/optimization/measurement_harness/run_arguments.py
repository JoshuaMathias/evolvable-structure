"""The command line of ``esoi run <component>`` and the choice of which cases it runs."""
from __future__ import annotations

import argparse
from typing import Any, Callable, Dict, List

from esoi.optimization.when_metrics_are_run import run_log
from esoi.optimization.measurement_harness.case_loading import stratified_sample
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.optimization.when_metrics_are_run import run_guards
from esoi.structure.intent_registry.config import Config


def build_parser(component: str) -> argparse.ArgumentParser:
    """The argument parser of one component's run."""
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
    return ap


def failed_case_names(args: argparse.Namespace, config: Config, component: str, impl: str, cases_sha: str) -> str:
    """The cases that failed last time, comma-joined, for ``--failed``; raises ``RunError`` when none are logged or other cases were named."""
    if args.only or args.sample is not None:
        raise RunError("--failed already names the cases to run (the ones that failed last); drop --only or --sample")
    failing = run_log.failed_cases(config.root / config.runs_log, component, impl, cases_sha)
    if not failing:
        raise RunError(f"no failing case is logged for {impl} on these cases, so there is nothing to rerun "
                       f"(the log is {config.runs_log}); run it without --failed")
    return ",".join(failing)


def name_cases_to_run(args: argparse.Namespace, config: Config, component: str, impl: str, cases_sha: str,
                      say: Callable[[str], None], guards: bool) -> None:
    """Set ``args.only`` to the failing cases (``--failed``) or to the unsolved ones (a plain unguarded-by-flags run)."""
    if args.failed:
        args.only = failed_case_names(args, config, component, impl, cases_sha)
    elif guards and not (args.only or args.sample is not None or args.record or args.force is not None):
        unsolved = run_guards.unsolved_cases(config, component, impl)
        if unsolved:   # the failing cases are rerun by themselves; the whole set waits until they pass
            say(f"{len(unsolved)} case(s) failed in the latest run and have not passed since, so only those run ({', '.join(unsolved[:8])}"
                f"{' ...' if len(unsolved) > 8 else ''}); pass --force \"reason\" to run the whole set")
            args.only = ",".join(unsolved)


def narrow_cases(args: argparse.Namespace, component: str, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The cases ``--only`` names, then the ``--sample`` spread over them."""
    if args.only:
        keep = {c.strip() for c in args.only.split(",")}
        cases = [c for c in cases if c["id"] in keep]
        if not cases:
            raise RunError(f"--only {args.only!r} matches no case of {component}")
    if args.sample is not None:
        if args.sample < 1:
            raise RunError("--sample needs a number of cases of at least 1")
        cases = stratified_sample(cases, args.sample)
    return cases
