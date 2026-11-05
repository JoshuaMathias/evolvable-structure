"""The interface of SpecifyingFromCode: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project


@solution("specify-from-code", kind="evaluate", entry="drift", example=".")
@runtime_checkable
class SpecifyingFromCode(Protocol):
    """The places where what the code declares and what the records say disagree."""

    def drift(self, project: str) -> List[str]: ...


@implementation("specify-from-code", "declarations-and-sync")
class DeclarationsAndSync:
    """@solution and @implementation declarations read from the code and compared with the records."""

    def drift(self, project: str) -> List[str]:
        from esoi.structure.intent_registry.specify_from_code import declarations
        cfg, found = load_project(project)
        return declarations.drift(cfg, found, declarations.scan(cfg))
