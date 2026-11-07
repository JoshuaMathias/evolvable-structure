"""Re-run the arms whose recorded result no longer counts and are worth their cost, and list the rest."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reasons
from esoi.optimization.measurement_harness.case_loading import sample_args
from esoi.optimization.measurement_harness.component_folder import prepare_path
from esoi.optimization.measurement_harness.run_component import run_component
from esoi.optimization.measurement_harness.run_errors import PendingNetwork, RunError
from esoi.optimization.when_metrics_are_run.interface import paid_reason, run_guards
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


@dataclass(frozen=True)
class StaleArm:
    """One arm under review: its latest whole-run row (None when never measured), whether it is the selected arm, and the run flags of the selected arm's sample."""
    config: Config
    comp: str
    impl: str
    row: Optional[Dict[str, str]]
    is_selected: bool
    flags: List[str]


@dataclass(frozen=True)
class RerunPolicy:
    """What a ``--stale`` run does with an arm worth running: record the row, include paid arms, or only plan."""
    record: bool
    include_paid: bool
    plan: bool


def not_rerun_reason(arm: StaleArm, for_decision: bool, named: bool, run_all: bool) -> str:
    """Empty when running a stale arm is worth its cost now, else why ``--stale`` leaves it alone. A changed file, or changed cases,
    only informs: a row is re-run automatically when it has never been measured (a selected arm), when its metric's expiration has
    passed, when a pending decision or release depends on it (``for_decision``, the selected arm only), when a person names it
    (``--include``), or with ``--all`` (the old run-everything behaviour). A rival, and any row nothing depends on, is never re-run."""
    config, component, row, selected = arm.config, arm.comp, arm.row, arm.is_selected
    if run_all or named:
        return ""
    if row is None and selected:
        return ""
    if selected and stale_reasons.expired_reason(config, component, row):
        return ""
    if not selected:
        return "nothing depends on it (a rival is measured when a decision needs the comparison: name it with --include)"
    if for_decision:
        return ""
    return "no pending decision or release depends on it (run `esoi run --stale --for-decision` when one does, or name the arm with --include)"


def why_stale(arm: StaleArm, full: bool) -> str:
    """Why an arm's recorded result no longer counts (empty when it is current): a changed file or case, a different sample than the
    selected arm's, a sample when ``--full`` asks for the whole set, or an expiration that has passed."""
    config, comp, row = arm.config, arm.comp, arm.row
    return (stale_reasons.stale_reason(config, comp, row) or other_sample(arm)
            or (full_reason(config, comp, row) if full else "")
            or (stale_reasons.expired_reason(config, comp, row) if arm.is_selected else ""))   # an expiration the metric or project declares and that has passed


def full_reason(config: Config, comp: str, row: Optional[Dict[str, str]]) -> str:
    """Why a sampled row no longer counts when ``--full`` asks for the whole set."""
    return "it was scored on a sample and --full asks for the whole set" if row and sample_args(config, comp, row) else ""


def other_sample(arm: StaleArm) -> str:
    """Why a rival's row is not comparable: it was scored on another sample than the selected arm's."""
    flags = arm.flags
    if not arm.row or arm.is_selected:
        return ""
    wanted = sample_args(arm.config, arm.comp, arm.row)
    if wanted == flags:
        return ""
    return f"it was scored on a different sample ({' '.join(wanted) or 'full set'}) than the selected arm ({' '.join(flags) or 'full set'}), so it is not comparable"


def rerun_one(arm: StaleArm, why: str, named: bool, policy: RerunPolicy, say: Callable[[str], None]) -> str:
    """Run (or plan) one stale arm worth running. Returns ``paid`` or ``capped`` when it was skipped, ``failed`` when it could not
    start, else ``ran``."""
    config, comp, impl = arm.config, arm.comp, arm.impl
    paid = paid_reason(config, comp, impl, arm.row)
    if paid and not (policy.include_paid or named):
        say(f"{comp}/{impl}: stale, {why}; SKIPPED because it may spend money ({paid})")
        return "paid"
    capped = "" if named else run_guards.ceiling_reason(config, comp, impl, run_guards.sample_of(arm.flags), paid, stale_reasons.stale_reason)
    if capped:
        say(f"{comp}/{impl}: stale, {why}; SKIPPED, not worth running: {capped}")
        return "capped"
    return run_arm(arm, why, policy, say)


def run_arm(arm: StaleArm, why: str, policy: RerunPolicy, say: Callable[[str], None]) -> str:
    """Report and run (or plan) one stale arm that passed the guards: ``planned``, ``offline``, ``failed`` or ``ran``."""
    config, comp, impl, flags, record, plan = arm.config, arm.comp, arm.impl, arm.flags, policy.record, policy.plan
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


def say_left_over(left: List[str], skipped: List[str], say: Callable[[str], None]) -> None:
    """The closing lines: how many rows were not re-run and why, and how to run the paid arms that were skipped."""
    if left:
        say(f"{len(left)} row(s) not re-run: a changed file only informs; improve the implementation first, and measure when a decision "
            "depends on the result (`esoi run --stale --for-decision`, `--include COMPONENT/IMPL`, or `--all` for every stale arm)")
    if skipped:
        say(f"skipped {len(skipped)} paid arm(s); stage and budget them first (see the metric run policy), then run each with "
            "`esoi run <component> --impl <name> --max-calls N --record`, or "
            f"`esoi run --stale --include {' --include '.join(skipped)}`")


def waiting_label(why: str) -> str:
    """How a stale row that is not re-run is described: the changed code, or the stale reason."""
    prefix = "the measured code changed since"
    return "measured code changed since " + why.split(" changed since ", 1)[-1] if why.startswith(prefix) else f"stale, {why}"


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
    left: List[str] = []
    failed = 0
    target: Dict[str, List[str]] = {}   # component -> run flags of its selected arm's sample
    for comp, impl in stale_arms(config):
        row = latest.get(comp, {}).get(impl)
        if comp not in target:   # stale_arms lists the selected arm of a component first
            target[comp] = [] if full else sample_args(config, comp, row)
        flags = target[comp]
        arm = StaleArm(config, comp, impl, row, (comp, impl) in selected_arms, flags)
        why = why_stale(arm, full)
        if not why:
            say(f"{comp}/{impl}: current")
            continue
        named = f"{comp}/{impl}" in (include or ())   # a person named this arm: that is the decision the guard asks for
        waiting = not_rerun_reason(arm, for_decision, named, run_all)
        if waiting:
            say(f"{comp}/{impl}: {waiting_label(why)}; not re-run: {waiting}")
            left.append(f"{comp}/{impl}")
            continue
        outcome = rerun_one(arm, why, named, RerunPolicy(record, include_paid, plan), say)
        skipped += [f"{comp}/{impl}"] * (outcome == "paid")
        failed += outcome == "failed"
    say_left_over(left, skipped, say)
    return 1 if failed else 0
