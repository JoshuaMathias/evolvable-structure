"""The interface of OwnershipMapping: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project

__all__ = ["OwnershipMapping"]


@solution("ownership-map", kind="evaluate", entry="unowned", example=".")
@runtime_checkable
class OwnershipMapping(Protocol):
    """The files of the project that no component owns."""

    def unowned(self, project: str) -> List[str]: ...


@implementation("ownership-map", "component-rows")
class ComponentRows:
    """The path patterns of the components table."""

    def unowned(self, project: str) -> List[str]:
        from esoi.structure.structure_check.interface import check
        cfg, found = load_project(project)
        return sorted(name for name, owners in check.build_context(cfg).owners.items() if not owners)
