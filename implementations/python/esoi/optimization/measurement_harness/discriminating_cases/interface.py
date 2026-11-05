"""The interface of DiscriminatingCases: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project


@solution("discriminating-cases", kind="event", entry="describe", example=".")
@runtime_checkable
class DiscriminatingCases(Protocol):
    """How many baseline implementations the components keep to prove their cases can tell a naive one from a sound one."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("discriminating-cases", "broken-baselines")
class BrokenBaselines:
    """The naive implementations kept in each component's ``broken/`` folder."""

    def describe(self, project: str) -> Dict[str, int]:
        cfg, found = load_project(project)
        files = sorted(cfg.evaluation.glob("*/broken/*.py")) if cfg.evaluation.is_dir() else []
        return {"baselines": sum(1 for file in files if file.name != "__init__.py")}
