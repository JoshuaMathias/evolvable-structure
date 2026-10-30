"""Rules about cascading conditionals: S32 and S33.

S32 a metric's cascading conditionals can be read, S33 the selected implementation is the one the cascade chooses.
"""
from __future__ import annotations

import datetime

from .. import cascade, leaderboard
from ..harness import stale_reason
from ..tables import ids
from .base import Context, RuleGroup

SUMMARIES = {
    "S32": "A metric's `cascading_conditionals` is an ordered list of stages (`name [key=value | key=value]` joined by ` > `): "
           "known keys and values, unique stage names, and a gate or floor on every stage but the last.",
    "S33": "Where a metric's cascade has counting results, the solution's selected implementation is the one the cascade "
           "chooses (the highest result at the latest stage run, unless another scored higher at an earlier shared stage "
           "and has not been run there yet), or a waiver names the pending decision (waive as `<solution>`).",
}


def run(ctx: Context) -> list:
    bad: list = []
    for metric in ctx.registry.metrics:
        stages, errors = cascade.parse(metric.get("cascading_conditionals", ""))
        mid = metric.get("metric_id", "")
        bad.extend(f"S32 metrics.csv {mid}: {why}" for why in errors)
        component, selected = next(iter(ctx.harness_arms(metric.get("command", ""))), ("", ""))   # the command names the selected arm
        if errors or not stages or component not in ctx.history:
            continue
        standing = cascade.standings(stages, ctx.history[component], datetime.date.today(),
                                     lambda row, c=component: stale_reason(ctx.config, c, row, ctx.strict),
                                     ctx.config.evaluation)
        decision = cascade.decide(stages, standing, ctx.config.evaluation)
        for sid in ids(metric.get("solution_ids", "")):
            if decision.winner and selected and selected != decision.winner and not ctx.waived("S33", sid):
                bad.append(f"S33 {sid}: selected is {selected} but the cascade of {mid} chooses {decision.winner} "
                           f"({'; '.join(decision.notes) or 'the highest result at ' + stages[decision.stage].name}); "
                           "switch `selected` (esoi select --promote) or waive naming the pending decision")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
