"""The cascade's choice for a component whose metric declares a lead requirement, so the check (S10), ``esoi leaderboard`` and ``esoi select`` read one decision.

A metric's stage may say what lead a challenger needs and how arms without it are told apart (``lead_requirement``). Where it does, a plain
"a higher pass rate replaces the selected arm" comparison would contradict the metric, so the places that compare an arm with its rivals ask this module first:
``declared_decision`` returns the decision of the first metric of the component whose deciding stage declares a requirement, or ``None``
(the plain comparison then applies, exactly as before)."""
from __future__ import annotations

import datetime
from typing import Callable, Dict, List, Optional

from esoi.optimization.leaderboard import cascade_stages, stage_standings
from esoi.optimization.leaderboard.results_log import Row


def declared_decision(config, registry, component: str, history: Dict[str, List[Row]], incumbent: str,
                      stale: Optional[Callable[[Row], str]] = None, today: Optional[datetime.date] = None) -> Optional[stage_standings.Decision]:
    """The decision of the cascade of the first metric whose command runs ``component`` first and whose stages declare a lead requirement, with
    ``incumbent`` the selected arm; ``None`` when there is no such metric or no arm has a counting result. ``stale`` says why a row no longer counts
    (default: the staleness test of the measured code and cases)."""
    if registry is None:
        return None
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reason
    from esoi.structure.intent_registry.registry import harness_arms
    check = stale or (lambda row: stale_reason(config, component, row, False))
    for metric in registry.metrics:
        arms = harness_arms(config, metric.get("command", ""))
        if not arms or arms[0][0] != component:
            continue
        stages, errors = cascade_stages.load_stages(config, metric)
        if errors or not any(s.requirement.declared for s in stages):
            continue
        decision = stage_standings.decision_for(config, component, stages, history, check, today, incumbent,
                                                lambda c: (lambda row: stale_reason(config, c, row, False)))[1]
        if decision.winner and decision.required:
            return decision
    return None
