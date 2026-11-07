"""Re-run the arms whose recorded result no longer counts and are worth their cost, and list the rest."""
from __future__ import annotations

import importlib
from typing import Callable, Dict, List, Optional, Tuple

from esoi.optimization.measurement_harness import stale_reasons
from esoi.optimization.measurement_harness.case_loading import sample_args
from esoi.optimization.measurement_harness.component_folder import prepare_path
from esoi.optimization.measurement_harness.run_component import run_component
from esoi.optimization.measurement_harness.run_errors import PendingNetwork, RunError
from esoi.optimization.measurement_harness.stale_reasons import expired_reason
from esoi.optimization.when_metrics_are_run import run_guards
from esoi.optimization.when_metrics_are_run.paid_gating import paid_reason
from esoi.structure.intent_registry.config import Config


def stale_arms(config: Config) -> List[Tuple[str, str]]:
    """Each selected arm of the registry, then every other recorded arm of its component that competes with it (an
    ablation or validity arm is no rival). A rival recorded on other cases or another sample is included: it is not compared until it is
    re-run on the selected arm's cases and sample."""
    from esoi.optimization.leaderboard import arm_kinds, arm_selection, results_log
    from esoi.structure.intent_registry.registry import load
    latest = results_log.latest_results(config.results_path)   # every arm, even one recorded only on named cases
    arms: List[Tuple[str, str]] = []
    registry = load(config)
    for row in registry.solutions:
        comp, impl = arm_selection.selected_arm(config, row, "", registry)
        if not comp:
            continue
        for arm in [(comp, impl)] + [(comp, name) for name, r in sorted(latest.get(comp, {}).items())
                                 if not arm_kinds.is_ablation(r, config.evaluation)]:
            if arm not in arms:
                arms.append(arm)
    return arms


def not_rerun_reason(config: Config, component: str, impl: str, row: Optional[Dict[str, str]], selected: bool, for_decision: bool,
                     named: bool, run_all: bool) -> str:
    """Empty when running a stale arm is worth its cost now, else why ``--stale`` leaves it alone. A changed file, or changed cases,
    only informs: a row is re-run automatically when it has never been measured (a selected arm), when its metric's expiration has
    passed, when a pending decision or release depends on it (``for_decision``, the selected arm only), when a person names it
    (``--include``), or with ``--all`` (the old run-everything behaviour). A rival, and any row nothing depends on, is never re-run."""
    if run_all or named:
        return ""
    if row is None and selected:
        return ""
    if selected and expired_reason(config, component, row):
        return ""
    if not selected:
        return "nothing depends on it (a rival is measured when a decision needs the comparison: name it with --include)"
    if for_decision:
        return ""
    return "no pending decision or release depends on it (run `esoi run --stale --for-decision` when one does, or name the arm with --include)"


def why_stale(config: Config, comp: str, impl: str, row: Optional[Dict[str, str]], is_selected: bool, flags: List[str], full: bool) -> str:
    """Why an arm's recorded result no longer counts (empty when it is current): a changed file or case, a different sample than the
    selected arm's, a sample when ``--full`` asks for the whole set, or an expiration that has passed."""
    why = stale_reasons.stale_reason(config, comp, row)
    if not why and row and not is_selected:
        wanted = sample_args(config, comp, row)
        if wanted != flags:
            why = f"it was scored on a different sample ({' '.join(wanted) or 'full set'}) than the selected arm ({' '.join(flags) or 'full set'}), so it is not comparable"
    if not why and full and row and sample_args(config, comp, row):
        why = "it was scored on a sample and --full asks for the whole set"
    if not why and is_selected:
        why = expired_reason(config, comp, row)   # an expiration the metric or project declares and that has passed
    return why


def rerun_one(config: Config, comp: str, impl: str, row: Optional[Dict[str, str]], why: str, flags: List[str], named: bool,
              options: Tuple[bool, bool, bool], say: Callable[[str], None]) -> str:
    """Run (or plan) one stale arm worth running. Returns ``paid`` or ``capped`` when it was skipped, ``failed`` when it could not
    start, else ``ran``."""
    record, include_paid, plan = options
    paid = paid_reason(config, comp, impl, row)
    if paid and not (include_paid or named):
        say(f"{comp}/{impl}: stale, {why}; SKIPPED because it may spend money ({paid})")
        return "paid"
    capped = "" if named else run_guards.ceiling_reason(config, comp, impl, run_guards.sample_of(flags), paid, stale_reasons.stale_reason)
    if capped:
        say(f"{comp}/{impl}: stale, {why}; SKIPPED, not worth running: {capped}")
        return "capped"
    say(f"{comp}/{impl}: stale, {why}")
    if plan:
        say(f"{comp}/{impl}: would run" + (f" ({' '.join(flags)})" if flags else ""))
        return "planned"
    score = importlib.import_module(f"{comp}.score")
    try:
        run_component(comp, score.score_case, ["--impl", impl] + flags + (["--record"] if record else ["--keep-going"]), config,
                      lambda text: None, guards=False)
    except PendingNetwork as exc:   # offline: informs, records nothing, is not a failure
        say(f"{comp}/{impl}: {exc}")
        return "offline"
    except RunError as exc:   # an arm that cannot start (an unknown variant key, a bad circumstance) fails once, loudly
        say(f"{comp}/{impl}: ERROR, {exc}")
        return "failed"
    say(f"{comp}/{impl}: run" + (f" ({' '.join(flags)})" if flags else "") + (" and recorded" if record else ""))
    return "ran"


def rerun_stale(config: Config, say: Callable[[str], None] = print, record: bool = True, include_paid: bool = False,
                include: Optional[List[str]] = None, full: bool = False, plan: bool = False, run_all: bool = False,
                for_decision: bool = False) -> int:
    """Report every selected implementation, and every rival recorded beside it, whose recorded result no longer counts, and run
    and record only those worth running (``not_rerun_reason``): a changed file or changed cases is information, not an order.

    By default a stale row is re-run when it has never been measured (a selected arm), when its metric's expiration has passed
    (never unless a metric or the project declares one), or when a pending decision or release depends on it (``for_decision``, the
    selected arm only) or a person names it (``include``). A rival, and any row nothing depends on, is listed as not re-run.
    ``run_all`` is the old behaviour: re-run every stale arm. Each plan line says which file changed and which component owns it,
    and why the row is or is not re-run.

    Each run uses the sample of the selected arm's newest whole-run row (an ``only:`` or ``slice:`` row is never the row
    staleness is judged on), so a re-record stays comparable with its rivals; ``full`` runs the whole set instead.

    An arm that may spend money (``paid_reason``) is never run by default: it is listed as skipped with the command that
    runs it. ``include_paid`` runs them all, ``include`` (``component/impl`` names) only those.
    The recorded rows are the only progress: every run appends its row when it finishes, so a killed re-record loses just the
    arm in flight and the next ``--stale`` starts at it, skipping what is already current. ``plan`` lists each arm with its
    decision (current, would run, not re-run, skipped as paid or capped) and runs nothing."""
    from esoi.optimization.leaderboard import arm_selection, results_log
    from esoi.structure.intent_registry.registry import load
    prepare_path(config)
    latest = results_log.latest_results(config.results_path, whole=True)   # staleness is judged on the newest whole run, not an only: row
    registry = load(config)
    selected_arms = {arm_selection.selected_arm(config, r, "", registry) for r in registry.solutions}
    skipped: List[str] = []
    skipped_ceiling: List[str] = []
    left: List[str] = []
    failed = 0
    target: Dict[str, List[str]] = {}   # component -> run flags of its selected arm's sample
    for comp, impl in stale_arms(config):
        row = latest.get(comp, {}).get(impl)
        if comp not in target:   # stale_arms lists the selected arm of a component first
            target[comp] = [] if full else sample_args(config, comp, row)
        flags = target[comp]
        why = why_stale(config, comp, impl, row, (comp, impl) in selected_arms, flags, full)
        if not why:
            say(f"{comp}/{impl}: current")
            continue
        named = f"{comp}/{impl}" in (include or [])   # a person named this arm: that is the decision the guard asks for
        waiting = not_rerun_reason(config, comp, impl, row, (comp, impl) in selected_arms, for_decision, named, run_all)
        if waiting:
            label = "measured code changed since " + why.split(" changed since ", 1)[-1] if why.startswith("the measured code changed since") else f"stale, {why}"
            say(f"{comp}/{impl}: {label}; not re-run: {waiting}")
            left.append(f"{comp}/{impl}")
            continue
        outcome = rerun_one(config, comp, impl, row, why, flags, named, (record, include_paid, plan), say)
        if outcome == "paid":
            skipped.append(f"{comp}/{impl}")
        elif outcome == "capped":
            skipped_ceiling.append(f"{comp}/{impl}")
        failed += outcome == "failed"
    if left:
        say(f"{len(left)} row(s) not re-run: a changed file only informs; improve the implementation first, and measure when a decision "
            "depends on the result (`esoi run --stale --for-decision`, `--include COMPONENT/IMPL`, or `--all` for every stale arm)")
    if skipped:
        say(f"skipped {len(skipped)} paid arm(s); stage and budget them first (see the metric run policy), then run each with "
            "`esoi run <component> --impl <name> --max-calls N --record`, or "
            f"`esoi run --stale --include {' --include '.join(skipped)}`")
    return 1 if failed else 0
