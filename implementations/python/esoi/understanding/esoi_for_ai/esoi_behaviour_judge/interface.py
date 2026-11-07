"""The interface of EsoiBehaviourJudging: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.optimization.measurement_harness.interface import count_cases
from esoi.understanding.esoi_for_ai.esoi_behaviour_judge import behaviour_judge  # noqa: F401  (re-exported: other units call this unit through its interface)

__all__ = ["EsoiBehaviourJudging", "behaviour_judge"]


@solution("esoi-behaviour-judge", kind="event", entry="describe", example=".")
@runtime_checkable
class EsoiBehaviourJudging(Protocol):
    """How many labelled replies show how far the judge's grading can be trusted."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("esoi-behaviour-judge", "model-judge-on-the-rubric")
class ModelJudgeOnTheRubric:
    """The model judge, graded against the labelled replies of its component."""

    def describe(self, project: str) -> Dict[str, int]:
        return count_cases(project, "judge_esoi_behaviour")
