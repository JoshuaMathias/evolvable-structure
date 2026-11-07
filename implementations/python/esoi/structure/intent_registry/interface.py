"""The interface of IntentRegistering: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.intent_registry import admit, besidecode, migrate  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.structure.intent_registry import implementedby  # noqa: F401  (re-exported: other units call this unit through its interface)

__all__ = ["IntentRegistering", "admit", "besidecode", "counted", "implementedby", "load_project", "migrate"]


@solution("intent-registry", kind="event", entry="count", example=".")
@runtime_checkable
class IntentRegistering(Protocol):
    """The project's records as the code reads them: how many rows each kind of record holds."""

    def count(self, project: str) -> Dict[str, int]: ...


def counted(found) -> Dict[str, int]:
    return {"problems": len(found.problems), "ideals": len(found.ideals), "solutions": len(found.every_solution()),
            "implementations": len(found.implementations), "metrics": len(found.metrics)}


@implementation("intent-registry", "esoi_folder")
class CsvRecords:
    """Records kept in the structure folder, one folder per intent (the layout before records beside the code)."""

    def count(self, project: str) -> Dict[str, int]:
        cfg, found = load_project(project)
        return counted(found)


@implementation("intent-registry", "beside_code")
class BesideCodeRecords:
    """Records kept beside the code they describe (`[records] beside_code` in esoi.toml), read as one tree with the structure folder."""

    def count(self, project: str) -> Dict[str, int]:
        cfg, found = load_project(project)
        return counted(found)
