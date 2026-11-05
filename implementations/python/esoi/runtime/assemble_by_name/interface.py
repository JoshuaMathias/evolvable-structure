"""The interface of AssemblingByName: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution


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
