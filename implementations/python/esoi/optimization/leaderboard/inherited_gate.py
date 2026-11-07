"""The stage gate a consumer inherits: a consumer stage written ``name [inherits=stage]`` is passed only when the foundation's stage of that name passed for the
foundation arm this arm names, by the foundation's own stage definition (gate, floor, expiry and staleness all the foundation's)."""
from __future__ import annotations

from typing import Callable, List, Tuple

from esoi.optimization.leaderboard import cascade_stages, results_log, stage_standings
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import builds_on
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_reasons import stale_reason
from esoi.structure.intent_registry import registry as registry_module
from esoi.structure.intent_registry.config import Config


def inherited_gate(config: Config, component: str, impl: str) -> Callable[[cascade_stages.Stage], Tuple[bool, str]]:
    """``gate(stage) -> (met, why)``: whether the foundation stage a consumer stage ``inherits`` has passed for the foundation arm this arm names,
    by the foundation's own stage definition (gate, floor, expiry and staleness all the foundation's)."""
    named, foundations = builds_on.declared_arms(config, component, impl), builds_on.declared(config, component)

    def gate(stage: cascade_stages.Stage) -> Tuple[bool, str]:
        checked: List[Tuple[bool, str]] = []
        for f in foundations:
            if named.get(f.name):
                checked += foundation_stage_checks(f, named[f.name], stage)
        if not checked:
            return False, f"no foundation has a stage {stage.inherits!r} for this arm"
        failed = [why for met, why in checked if not met]
        return (not failed), "; ".join(failed)
    return gate


def foundation_stage_checks(f: builds_on.Foundation, arm: str, stage: cascade_stages.Stage) -> List[Tuple[bool, str]]:
    """``(met, why)`` for the stage ``stage`` inherits, in each of the foundation's metrics that runs its component."""
    fconf = builds_on.load_config(f)
    loaded = registry_module.load(fconf)
    checked: List[Tuple[bool, str]] = []
    for metric in loaded.metrics:
        if f.target not in [c for c, _ in registry_module.harness_arms(fconf, metric.get("command", ""))]:
            continue
        stages, errors = cascade_stages.load_stages(fconf, metric)
        theirs = next((i for i, s in enumerate(stages) if s.name == stage.inherits), None)
        if theirs is not None and not errors:
            checked.append(stage_check(f, arm, stage, fconf, stages, theirs))
    return checked


def stage_check(f: builds_on.Foundation, arm: str, stage: cascade_stages.Stage, fconf: Config, stages: List[cascade_stages.Stage], theirs: int) -> Tuple[bool, str]:
    """Whether the foundation's own stage ``theirs`` passed for ``arm``, by the foundation's gate, floor, expiry and staleness."""
    history = results_log.all_results(fconf.results_path).get(f.target, {}).get(arm, [])
    standing = stage_standings.standings(stages, {arm: history}, None, lambda row, c=fconf: stale_reason(c, f.target, row, True),
                                         fconf.evaluation).get(arm)
    row = standing.rows.get(theirs) if standing else None
    if row is None:
        why = "expired or stale" if standing and theirs in standing.expired else "not run"
        return False, f"{f.name}: {arm} at {stage.inherits} is {why}"
    met, why = stage_standings.gate_met(stages[theirs], row, None, fconf.evaluation)
    return met, f"{f.name}: {arm} at {stage.inherits}: {why or 'passed'}"
