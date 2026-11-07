"""The interface of TemplateSyncing: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.structure.intent_registry.template_sync.templates import sync
from esoi.structure.intent_registry.template_sync.versioning import VersionError, record, report as versioning_report

__all__ = ["VersionError", "record", "sync", "versioning_report"]


@solution("template-sync", kind="evaluate", entry="fields", example=".")
@runtime_checkable
class TemplateSyncing(Protocol):
    """The fields of each kind of record that the project's intent template asks for."""

    def fields(self, project: str) -> Dict[str, int]: ...


@implementation("template-sync", "template-parser")
class TemplateParser:
    """Reads the template from the parsed copy the repository keeps beside its records."""

    def fields(self, project: str) -> Dict[str, int]:
        from esoi.structure.intent_registry.template_sync import template
        cfg, found = load_project(project)
        return {entity: len(rows) for entity, rows in template.load_for(cfg).items()}
