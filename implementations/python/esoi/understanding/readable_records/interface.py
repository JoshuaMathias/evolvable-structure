"""The interface of ReadableRecording: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project


@solution("readable-records", kind="evaluate", entry="page", example=".")
@runtime_checkable
class ReadableRecording(Protocol):
    """The README page of the project's top intent, generated from its records."""

    def page(self, project: str) -> str: ...


@implementation("readable-records", "full_page")
class FullPageReadme:
    """The record tables only, written from the records, so the page cannot disagree with them."""

    def page(self, project: str) -> str:
        from esoi.understanding.readable_records import readme
        cfg, found = load_project(project)
        return readme.pages(cfg, found, layout="full")[0][1]


@implementation("readable-records", "at_a_glance")
class AtAGlanceReadme:
    """The summary a reader needs first (vision, coherence, diagram, entry calls, links), then the full record below a divider."""

    def page(self, project: str) -> str:
        from esoi.understanding.readable_records import readme
        cfg, found = load_project(project)
        return readme.pages(cfg, found, layout="glance")[0][1]


@implementation("readable-records", "links_page")
class LinksPageReadme:
    """A compact page of the vision statement and links to everything else."""

    def page(self, project: str) -> str:
        from esoi.understanding.readable_records import readme
        cfg, found = load_project(project)
        return readme.pages(cfg, found, layout="links")[0][1]
