"""The interface of TheSteps: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.understanding.the_standard.skill_distribution.skill import read_lines
from esoi.understanding.the_standard.skill_distribution.skill import skill_file


@solution("the-steps", kind="event", entry="describe", example=".")
@runtime_checkable
class TheSteps(Protocol):
    """The written order in which to define and apply ESOI: its title and how many numbered steps it has."""

    def describe(self, project: str) -> Dict[str, Any]: ...


@implementation("the-steps", "esoi-steps")
class EsoiSteps:
    """The steps file of the public skill."""

    def describe(self, project: str) -> Dict[str, Any]:
        import re
        lines = read_lines(skill_file(project, "steps.md"))
        return {"title": next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), ""),
                "numbered_steps": sum(1 for line in lines if re.match(r"\d+[.)]\s", line))}
