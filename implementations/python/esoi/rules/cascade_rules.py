"""Rules about cascading conditionals: S32 and S33.

S32 a metric's cascading conditionals can be read, S33 the selected implementation is the one the cascade chooses.
"""
from __future__ import annotations

import datetime

from .. import cascade, leaderboard
from ..harness import defect_reason, stale_reason
from ..tables import ids
from .base import Context, RuleGroup

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
        stages, errors = cascade.load_stages(ctx.config, metric)
        mid = metric.get("metric_id", "")
        bad.extend(f"S32 metrics.csv {mid}: {why}" for why in errors)
        component, selected = next(iter(ctx.harness_arms(metric.get("command", ""))), ("", ""))   # the command names the selected arm
        if errors or not stages or component not in ctx.history:
            continue
        standing = cascade.standings(stages, ctx.history[component], datetime.date.today(),
                                     lambda row, c=component: defect_reason(ctx.config, c, row),   # a changed case file or code only informs
                                     ctx.config.evaluation)
        decision = cascade.decide(stages, standing, ctx.config.evaluation)
        for sid in ids(metric.get("solution_ids", "")):
            owner = next((s for s in ctx.registry.solutions if s["solution_id"] == sid), None)
            if owner is not None:
                selected = leaderboard.selected_arm(ctx.config, owner, component, ctx.registry)[1] or selected   # the records' `selected`
            if decision.winner and selected and selected != decision.winner and not ctx.waived("S33", sid):
                bad.append(f"S33 {sid}: selected is {selected} but the cascade of {mid} chooses {decision.winner} "
                           f"({'; '.join(decision.notes) or 'the highest result at ' + stages[decision.stage].name}); "
                           "switch `selected` (esoi select --promote) or waive naming the pending decision")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
