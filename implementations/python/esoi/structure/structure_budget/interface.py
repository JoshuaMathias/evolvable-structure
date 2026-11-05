"""The interface of StructureBudgeting: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.intent_registry.interface import counted


@solution("structure-budget", kind="event", entry="describe", example=".")
@runtime_checkable
class StructureBudgeting(Protocol):
    """What the structure costs the project now: its rules and its waivers."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("structure-budget", "written-weighing-rule")
class WrittenWeighingRule:
    """The rules and waivers counted, so each can be weighed against what it catches."""

    def describe(self, project: str) -> Dict[str, int]:
        from esoi.structure.structure_check import rules as rule_modules
        cfg, found = load_project(project)
        return {"rules": len(rule_modules.summaries(cfg)), "waivers": len(found.waivers)}
