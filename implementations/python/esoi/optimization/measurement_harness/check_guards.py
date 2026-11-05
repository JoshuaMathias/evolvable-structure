"""Refuse a run that cannot inform a decision (an unsolved failure, a capped arm, a public result) unless it says why it runs anyway."""
from __future__ import annotations

import argparse
from typing import Callable, List

from esoi.optimization.leaderboard import results_log
from esoi.optimization.measurement_harness import stale_reasons
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.optimization.when_metrics_are_run import run_guards
from esoi.optimization.when_metrics_are_run.paid_gating import paid_reason
from esoi.runtime.implementation_selection import variants
from esoi.structure.intent_registry.config import Config


def check_guards(config: Config, component: str, impl: str, sample: str, args: argparse.Namespace,
                 say: Callable[[str], None]) -> List[str]:
    """Refuse (``RunError``) a run that cannot inform a decision, unless it says why it runs anyway; the notes to record in
    ``details`` are returned. The ceiling guard and the public-first guard are in ``esoi.optimization.when_metrics_are_run.run_guards``."""
    try:
        forced = run_guards.force_reason(args.force)
        differs = run_guards.check_differs(args.differs) if args.differs is not None else ""
        latest = results_log.latest_results(config.results_path).get(component, {}).get(impl)
        paid = paid_reason(config, component, variants.base_of(impl), latest)
        capped = run_guards.ceiling_reason(config, component, impl, sample, paid, stale_reasons.stale_reason)
        public, lines = run_guards.public_reason(config, component, impl)
    except ValueError as exc:
        raise RunError(str(exc)) from exc
    notes: List[str] = []
    unsolved = "" if getattr(args, "failed", False) or sample else run_guards.unsolved_reason(config, component, impl)
    if unsolved and not forced:
        raise RunError(f"{impl} is not run on the whole set: {unsolved}")
    if unsolved:
        notes.append(f"forced past unsolved failures: {forced}")
    for line in lines:
        say(f"public result: {line}")
    if capped and not forced:
        raise RunError(f"{impl} is not run: {capped}")
    if capped:
        notes.append(f"forced past ceiling: {forced}")
    if public and not (differs or forced):
        raise RunError(f"{impl} is not run: {public}")
    if public and differs:
        notes.append(f"differs from public: {differs}")
    elif public:
        notes.append(f"forced past public result: {forced}")
    return notes
