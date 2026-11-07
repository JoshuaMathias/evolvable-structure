"""Refuse a run that cannot inform a decision (an unsolved failure, a capped arm, a public result) unless it says why it runs anyway."""
from __future__ import annotations

import argparse
from typing import Callable, List

from esoi.optimization.leaderboard import results_log
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reasons
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.optimization.when_metrics_are_run.interface import paid_reason, run_guards
from esoi.runtime.implementation_selection import variants
from esoi.structure.intent_registry.config import Config


def capped_reason(config: Config, component: str, impl: str, sample: str) -> str:
    """Why the run would pass the ceiling on what the arm may spend, or an empty string."""
    latest = results_log.latest_results(config.results_path).get(component, {}).get(impl)
    paid = paid_reason(config, component, variants.base_of(impl), latest)
    return run_guards.ceiling_reason(config, component, impl, sample, paid, stale_reasons.stale_reason)


def guard_findings(config: Config, component: str, impl: str, sample: str, args: argparse.Namespace) -> tuple:
    """``(forced, differs, ceiling reason, public reason, public lines)``; an unreadable flag is a ``RunError``."""
    try:
        forced = run_guards.force_reason(args.force)
        differs = run_guards.check_differs(args.differs) if args.differs is not None else ""
        capped = capped_reason(config, component, impl, sample)
        public, lines = run_guards.public_reason(config, component, impl)
    except ValueError as exc:
        raise RunError(str(exc)) from exc
    return forced, differs, capped, public, lines


def check_guards(config: Config, component: str, impl: str, sample: str, args: argparse.Namespace,
                 say: Callable[[str], None]) -> List[str]:
    """Refuse (``RunError``) a run that cannot inform a decision, unless it says why it runs anyway; the notes to record in
    ``details`` are returned. The ceiling guard and the public-first guard are in ``esoi.optimization.when_metrics_are_run.run_guards``."""
    forced, differs, capped, public, lines = guard_findings(config, component, impl, sample, args)
    notes: List[str] = []
    unsolved = "" if getattr(args, "failed", False) or sample else run_guards.unsolved_reason(config, component, impl)
    settle(unsolved, forced, f"{impl} is not run on the whole set: {unsolved}", f"forced past unsolved failures: {forced}", notes)
    for line in lines:
        say(f"public result: {line}")
    settle(capped, forced, f"{impl} is not run: {capped}", f"forced past ceiling: {forced}", notes)
    if public and not (differs or forced):
        raise RunError(f"{impl} is not run: {public}")
    notes += [f"differs from public: {differs}" if differs else f"forced past public result: {forced}"] if public else []
    return notes


def settle(reason: str, forced: str, refusal: str, note: str, notes: List[str]) -> None:
    """Refuse a run a guard stopped unless it was forced; a forced one leaves its note."""
    if reason and not forced:
        raise RunError(refusal)
    if reason:
        notes.append(note)
