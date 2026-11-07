"""The interface of WhenMetricsAreRun: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.optimization.when_metrics_are_run.paid_gating import BudgetExceeded, SIMULATED_MODEL, declared_live, declares_simulated, impl_path, paid_reason, price_for
from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.intent_registry.tables import read_lines
from esoi.optimization.when_metrics_are_run import run_guards, run_log
from esoi.optimization.when_metrics_are_run.run_guards import ceiling_reason, check_differs, force_reason, public_reason, unsolved_cases, unsolved_reason
from esoi.optimization.when_metrics_are_run.run_log import failed_cases


# What the harness and the consumer checks need to refuse a paid run: the budget error and the questions of whether an arm is paid and where it lives.
__all__ = ["BudgetExceeded", "SIMULATED_MODEL", "WhenMetricsAreRun", "ceiling_reason", "check_differs", "declared_live", "declares_simulated", "failed_cases", "force_reason", "impl_path", "paid_reason", "price_for", "public_reason", "run_guards", "run_log", "unsolved_cases", "unsolved_reason"]


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
