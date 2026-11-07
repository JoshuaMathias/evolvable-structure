"""The interface of StructureChecking: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from pathlib import Path
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.structure_check import check, hygiene  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.structure.structure_check.rules import structure_quality_rules  # noqa: F401  (re-exported: the command line calls this unit through its interface)


@solution("structure-check", kind="evaluate", entry="check", example=".")
@runtime_checkable
class StructureChecking(Protocol):
    """The problems of a project's records and code against the rules, one line each (empty when it passes)."""

    def check(self, project: str) -> List[str]: ...


@implementation("structure-check", "rule-script")
class RuleScript:
    """Every built-in and plugin rule over the project's records and files (``esoi check``)."""

    def check(self, project: str) -> List[str]:
        from esoi.structure.structure_check import check as check_module
        from esoi.structure.intent_registry import config as config_module
        return check_module.check(config_module.load(Path(project)))
