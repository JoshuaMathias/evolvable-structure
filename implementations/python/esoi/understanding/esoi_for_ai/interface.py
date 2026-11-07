"""The interface of EsoiForAi: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.tables import read_lines
from esoi.understanding.the_standard.skill_distribution.interface import skill_file
from esoi.optimization.measurement_harness.interface import count_cases
from esoi.understanding.esoi_for_ai.esoi_behaviour_judge.interface import EsoiBehaviourJudging
from esoi.understanding.esoi_for_ai import behaviour, command_provider  # noqa: F401  (re-exported: other units call this unit through its interface)

__all__ = ["EsoiForAi", "behaviour", "command_provider"]


@solution("esoi-for-ai", kind="event", entry="describe", example=".")
@runtime_checkable
class EsoiForAi(Protocol):
    """The standing instructions an AI agent is given and what they are measured on: the length of the skill that carries them, the
    behaviour cases its replies are scored on, and the labelled replies the judge of those replies is scored on."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("esoi-for-ai", "skill-as-standing-instructions")
class SkillAsStandingInstructions:
    """The public skill, loaded as standing instructions; the replies a pattern cannot settle are graded by the behaviour judge."""

    def __init__(self, judge: EsoiBehaviourJudging):
        self.judge = judge

    def describe(self, project: str) -> Dict[str, int]:
        return {"skill_lines": len(read_lines(skill_file(project, "SKILL.md"))),
                "behaviour_cases": count_cases(project, "behave_by_esoi")["cases"],
                "judge_cases": self.judge.describe(project)["cases"]}
