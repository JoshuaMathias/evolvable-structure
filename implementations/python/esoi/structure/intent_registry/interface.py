"""The interface of IntentRegistering: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.intent_registry import circumstances
from esoi.structure.intent_registry.assembly_errors import AssemblyError, LockError  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.structure.intent_registry.name_check import check_name  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.structure.intent_registry.migrate import run_cli as migrate_run_cli
from esoi.structure.intent_registry.admit import run_cli as admit_run_cli
from esoi.structure.intent_registry.besidecode import run_cli as besidecode_run_cli
from esoi.structure.intent_registry.circumstances import Circumstance, case_circumstances, digest, for_component, holds, run_context, slices
from esoi.structure.intent_registry.implementedby import CAP, implemented_by, problems

__all__ = ["AssemblyError", "CAP", "Circumstance", "IntentRegistering", "LockError", "admit_run_cli", "besidecode_run_cli", "case_circumstances", "check_name", "circumstances", "counted", "digest", "for_component", "holds", "implemented_by", "load_project", "migrate_run_cli", "problems", "run_context", "slices"]


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
