"""Rules about cascading conditionals: S32 and S33.

S32 a metric's cascading conditionals can be read, S33 the selected implementation is the one the cascade chooses.
"""
from __future__ import annotations

import datetime

from esoi.optimization.leaderboard import arm_selection, cascade_stages, stage_standings
from esoi.optimization.measurement_harness.stale_reasons import defect_reason, stale_reason
from esoi.structure.intent_registry.tables import ids
from esoi.structure.structure_check.rules.base import Context, RuleGroup

SUMMARIES = {
    "S32": "A metric's `cascading_conditionals` is an ordered list of stages (`name [key=value | key=value]` joined by ` > `): "
           "known keys and values, unique stage names, a gate or floor on every stage but the last (not on a `public` or `kind=idea` stage, which needs a `scale`), "
           "and a metric `expiration` (and the project's `[expiration] default`) that is `never` or a number of days.",
    "S33": "Where a metric's cascade has counting results, the solution's selected implementation is the one the cascade "
           "chooses (the highest result at the latest stage run, unless another scored higher at an earlier shared stage "
           "and has not been run there yet), or a waiver names the pending decision (waive as `<solution>`).",
}


def run(ctx: Context) -> list:
    bad: list = []
    for metric in ctx.registry.metrics:
        stages, errors = cascade_stages.load_stages(ctx.config, metric)
        mid = metric.get("metric_id", "")
        bad.extend(f"S32 metrics.csv {mid}: {why}" for why in errors)
        component, selected = next(iter(ctx.harness_arms(metric.get("command", ""))), ("", ""))   # the command names the selected arm
        if errors or not stages or component not in ctx.history:
            continue
        current = stage_standings.decide(stages, stage_standings.standings(stages, ctx.history[component], datetime.date.today(),
                                 lambda row, c=component: stale_reason(ctx.config, c, row, False),
                                 ctx.config.evaluation), ctx.config.evaluation)   # rows on the current cases only
        recorded = stage_standings.decide(stages, stage_standings.standings(stages, ctx.history[component], datetime.date.today(),
                                  lambda row, c=component: defect_reason(ctx.config, c, row),
                                  ctx.config.evaluation), ctx.config.evaluation)   # every well-formed row, whatever changed since
        for sid in ids(metric.get("solution_ids", "")):
            owner = next((s for s in ctx.registry.solutions if s["solution_id"] == sid), None)
            if owner is not None:
                selected = arm_selection.selected_arm(ctx.config, owner, component, ctx.registry)[1] or selected   # the records' `selected`
            if not (current.winner and selected and selected != current.winner) and not (recorded.winner and selected and selected != recorded.winner):
                continue
            decision = current if current.winner and selected != current.winner else recorded
            line = (f"S33 {sid}: selected is {selected} but the cascade of {mid} chooses {decision.winner} "
                    f"({'; '.join(decision.notes) or 'the highest result at ' + stages[decision.stage].name})")
            if current.winner == recorded.winner and current.winner != selected:   # current and recorded results agree: a real disagreement
                if not ctx.waived("S33", sid):
                    bad.append(line + "; switch `selected` (esoi select --promote) or waive naming the pending decision")
            elif not ctx.waived("S33", sid):   # the choice differs only because some results were recorded on other cases, so it informs
                ctx.advisory.append(line + f"; some results were recorded on other cases or changed code, so re-run `esoi run {component} --impl {selected} --record` when the decision depends on it")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
