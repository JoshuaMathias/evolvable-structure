"""The interface of LibraryAdopting: a Protocol declared with ``@solution``, and the arm this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.library_adoption.resolve import Libraries, Library, Reference, references, unresolved

__all__ = ["Libraries", "Library", "LibraryAdopting", "Reference", "references", "unresolved"]


@solution("library-adoption", kind="evaluate", entry="unresolved", example=".")
@runtime_checkable
class LibraryAdopting(Protocol):
    """The references to a library's solutions that do not resolve, one line each (empty when every adoption and specialization resolves)."""

    def unresolved(self, project: str) -> List[str]: ...


@implementation("library-adoption", "reference-column")
class ReferenceColumn:
    """The `adopts` and `specializes` cells of `solutions.csv`, resolved through `[adopts.<library>]` in the configuration."""

    def unresolved(self, project: str) -> List[str]:
        from esoi.structure.library_adoption import resolve
        config, found = load_project(project)
        return resolve.unresolved(config, found)
