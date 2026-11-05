"""The interface of WhenMetricsAreRun: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.understanding.the_standard.skill_distribution.skill import read_lines


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
