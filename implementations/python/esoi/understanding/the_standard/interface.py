"""The interface of TheStandard: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.intent_registry.tables import read_lines


@solution("the-standard", kind="event", entry="describe", example=".")
@runtime_checkable
class TheStandard(Protocol):
    """The standard document that teaches how a solution is shaped: its length."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("the-standard", "standard-document")
class StandardDocument:
    """The standard document the template sync keeps in step with the skill."""

    def describe(self, project: str) -> Dict[str, int]:
        from esoi.structure.intent_registry.template_sync import template
        cfg, found = load_project(project)
        return {"standard_lines": len(read_lines(template.standard_doc_path(cfg)))}


@implementation("the-standard", "documentation-folder")
class DocumentationFolder:
    """The documentation folder and its index page."""

    def describe(self, project: str) -> Dict[str, int]:
        cfg, found = load_project(project)
        return {"how_to_guides": "\n".join(read_lines(cfg.root / "docs" / "README.md")).count("](how-to/")}
