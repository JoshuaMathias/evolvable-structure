"""The interface of AssemblingByName: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.runtime.assemble_by_name import intent_map  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.runtime.assemble_by_name.entry import own_runner  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.runtime.assemble_by_name.environment_needs import checking, closure, declarations, generated_files, report  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.runtime.assemble_by_name.installation import assembly_plan, execution, plan_report, resolution_ladder, resolvers  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.runtime.assemble_by_name import assemble, hierarchy  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.runtime.assemble_by_name.assemble import Assembler  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.runtime.assemble_by_name import lock_file  # noqa: F401  (re-exported: other units call this unit through its interface)

__all__ = ["Assembler", "AssemblingByName", "AssemblyConfig", "assemble", "assembly_plan", "checking", "closure", "declarations", "execution", "generated_files", "hierarchy", "intent_map", "lock_file", "own_runner", "plan_report", "report", "resolution_ladder", "resolvers"]


@solution("assemble-by-name", kind="event", entry="names", example="structure-check")
@runtime_checkable
class AssemblingByName(Protocol):
    """The implementation names a solution of esoi can be built from."""

    def names(self, solution_id: str) -> List[str]: ...


@implementation("assemble-by-name", "assembler")
class AssemblerByName:
    """An Assembler over esoi's own solutions."""

    def names(self, solution_id: str) -> List[str]:
        from esoi.runtime.assemble_by_name.entry import own_runner
        return own_runner().assembler.names(solution_id)
