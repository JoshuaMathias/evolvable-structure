"""Rules about cascading conditionals: S32 and S33.

S32 a metric's cascading conditionals can be read, S33 the selected implementation is the one the cascade chooses.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple

from esoi.optimization.leaderboard import arm_selection, cascade_stages
from esoi.optimization.leaderboard.stage_standings import decision_for
from esoi.structure.intent_registry import circumstances
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import defect_reason, stale_reason
from esoi.structure.intent_registry.tables import ids
from esoi.structure.structure_check.rules.base import Context, RuleGroup

SUMMARIES = {
    "S32": "A metric's `cascading_conditionals` is an ordered list of stages (`name [key=value | key=value]` joined by ` > `): "
           "known keys and values, unique stage names, a gate or floor on every stage but the last (not on a `public` or `kind=idea` stage, which needs a `scale`), "
           "and a metric `expiration` (and the project's `[expiration] default`) that is `never` or a number of days.",
    "S33": "Where a metric's cascade has counting results, the solution's selected implementation is the one the cascade "
           "chooses (the highest result at the latest stage run, or the arm the stage's `lead`, `lead-on` and `tie-break` requirement lets stand, unless another scored higher at an earlier shared stage "
           "and has not been run there yet), or a waiver names the pending decision (waive as `<solution>`). A metric whose "
           "parent is another metric of the same solution ranks one kind of its work and is not compared with `selected`.",
}


def differs(selected: str, decision) -> bool:
    """Whether a standing names a winner other than the selected arm."""
    return bool(decision.winner and selected and selected != decision.winner)


@dataclass(frozen=True)
class Cascade:
    """A metric's stages and what they choose: on the current cases only (``current``) and on every well-formed row (``recorded``)."""
    stages: list
    current: object
    recorded: object


def disagreement_lines(ctx: Context, metric: Dict[str, str], component: str, selected: str, cascade: Cascade) -> Tuple[List[str], List[str]]:
    """(problems, advice) for each solution of a metric whose selected arm is not the one its cascade chooses."""
    stages, current, recorded = cascade.stages, cascade.current, cascade.recorded
    bad: List[str] = []
    advice: List[str] = []
    mid = metric.get("metric_id", "")
    for sid in ids(metric.get("solution_ids", "")):
        if refines_own_metric(metric, sid, ctx.registry.metrics):
            continue
        selected = recorded_selection(ctx, sid, component, selected)
        if not (differs(selected, current) or differs(selected, recorded)) or ctx.waived("S33", sid):
            continue
        line = disagreement_line(sid, mid, selected, current if differs(selected, current) else recorded, stages)
        if current.winner == recorded.winner and current.winner != selected:   # current and recorded results agree: a real disagreement
            bad.append(line + "; switch `selected` (esoi select --promote) or waive naming the pending decision")
        else:   # the choice differs only because some results were recorded on other cases, so it informs
            advice.append(line + advice_tail(component, selected))
    return bad, advice


def refines_own_metric(metric: Dict[str, str], sid: str, metrics: list) -> bool:
    """Whether ``metric`` measures one kind of the solution's work under another metric of the same solution (its
    ``parent_metric_ids`` names a metric that also lists ``sid``). A solution has one authoritative metric and `selected`
    is that metric's choice; a metric beneath it ranks the arms for its own kind of work (hard work, say, with its own
    budget), which a consumer asks for by kind, so its winner is not a disagreement with `selected`."""
    parents = set(ids(metric.get("parent_metric_ids", "")))
    return any(m.get("metric_id") in parents and sid in ids(m.get("solution_ids", "")) for m in metrics)


def recorded_selection(ctx: Context, sid: str, component: str, selected: str) -> str:
    """The arm the records' `selected` names for the solution, else the one given."""
    owner = next((s for s in ctx.registry.solutions if s["solution_id"] == sid), None)
    if owner is None:
        return selected
    return arm_selection.selected_arm(ctx.config, owner, component, ctx.registry)[1] or selected


def disagreement_line(sid: str, mid: str, selected: str, decision, stages) -> str:
    """The S33 line saying the selected arm is not the one the cascade chooses, with the cascade's reasons."""
    return (f"S33 {sid}: selected is {selected} but the cascade of {mid} chooses {decision.winner} "
            f"({'; '.join(decision.notes + ([decision.why] if decision.why else [])) or 'the highest result at ' + stages[decision.stage].name})")


def advice_tail(component: str, selected: str) -> str:
    """The advice appended to a disagreement that only informs."""
    return f"; some results were recorded on other cases or changed code, so re-run `esoi run {component} --impl {selected} --record` when the decision depends on it"


def unknown_parts(ctx: Context, stages: list, component: str) -> List[str]:
    """The parts a stage's ``lead-on`` names that are not circumstances of the component's solutions (a part is a circumstance id)."""
    named = sorted({n for s in stages for n in s.requirement.part_names})
    if not named:
        return []
    known = {c.circumstance_id for c in circumstances.for_component(ctx.config, component)}
    return [f"lead-on names part {n}, which is not a circumstance of {component} (circumstances.csv)" for n in named if n not in known]


def run(ctx: Context) -> list:
    bad: list = []
    for metric in ctx.registry.metrics:
        stages, errors = cascade_stages.load_stages(ctx.config, metric)
        mid = metric.get("metric_id", "")
        bad.extend(f"S32 metrics.csv {mid}: {why}" for why in errors)
        component, selected = next(iter(ctx.harness_arms(metric.get("command", ""))), ("", ""))   # the command names the selected arm
        if errors or not stages or component not in ctx.history:
            continue
        bad.extend(f"S32 metrics.csv {mid}: {why}" for why in unknown_parts(ctx, stages, component))
        owner = next(iter(ids(metric.get("solution_ids", ""))), "")
        incumbent = recorded_selection(ctx, owner, component, selected) if owner else selected   # the selected arm of the metric's solution
        today = datetime.date.today()
        current = decision_for(ctx.config, component, stages, ctx.history[component], lambda row, c=component: stale_reason(ctx.config, c, row, False),
                               today, incumbent, lambda c: (lambda row: stale_reason(ctx.config, c, row, False)))[1]   # rows on the current cases only
        recorded = decision_for(ctx.config, component, stages, ctx.history[component], lambda row, c=component: defect_reason(ctx.config, c, row),
                                today, incumbent, lambda c: (lambda row: defect_reason(ctx.config, c, row)))[1]   # every well-formed row, whatever changed since
        found, advice = disagreement_lines(ctx, metric, component, selected, Cascade(stages, current, recorded))
        bad += found
        ctx.advisory.extend(advice)
    return bad


GROUP = RuleGroup(SUMMARIES, run)
