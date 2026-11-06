"""The interface of WhenMetricsAreRun: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.optimization.when_metrics_are_run.paid_gating import BudgetExceeded, declared_live, declares_simulated, impl_path, paid_reason
from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.understanding.the_standard.skill_distribution.skill import read_lines


# What the harness and the consumer checks need to refuse a paid run: the budget error and the questions of whether an arm is paid and where it lives.
__all__ = ["WhenMetricsAreRun", "OnADecision", "BudgetExceeded", "declared_live", "declares_simulated", "impl_path", "paid_reason"]


@solution("when-metrics-are-run", kind="event", entry="describe", example=".")
@runtime_checkable
class WhenMetricsAreRun(Protocol):
    """The length of the written policy that says when each metric is run and what it may spend."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("when-metrics-are-run", "on-a-decision")
class OnADecision:
    """The policy page beside the records: a changed file informs, and a metric runs when a decision needs its result."""

    def describe(self, project: str) -> Dict[str, int]:
        cfg, found = load_project(project)
        return {"policy_lines": len(read_lines(cfg.structure / "metric-run-policy.md"))}
