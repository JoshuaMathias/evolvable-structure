"""The interface of ReadableRecording: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.understanding.readable_records.diagram import FILE as diagram_FILE, block as diagram_block, render as diagram_render, run_cli as diagram_run_cli, stale, write as diagram_write
from esoi.understanding.readable_records.readme_view import DIAGRAM_LINES, FILE as readme_view_FILE, FIRST_SCREEN_LINES, SUMMARY_LINES, WRAP, link, one_line, recorded_call, screen_lines, view_of
from esoi.understanding.readable_records.readme import pages as readme_pages, render as readme_render, run_cli as readme_run_cli, write as readme_write

__all__ = ["DIAGRAM_LINES", "FIRST_SCREEN_LINES", "ReadableRecording", "SUMMARY_LINES", "WRAP", "diagram_FILE", "diagram_block", "diagram_render", "diagram_run_cli", "diagram_write", "link", "one_line", "readme_pages", "readme_render", "readme_run_cli", "readme_view_FILE", "readme_write", "recorded_call", "screen_lines", "stale", "view_of"]


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
        return readme.top_page(cfg, found, layout="full")


@implementation("readable-records", "at_a_glance")
class AtAGlanceReadme:
    """The summary a reader needs first (vision, coherence, diagram, entry calls, links), then the full record below a divider."""

    def page(self, project: str) -> str:
        from esoi.understanding.readable_records import readme
        cfg, found = load_project(project)
        return readme.top_page(cfg, found, layout="glance")


@implementation("readable-records", "links_page")
class LinksPageReadme:
    """A compact page of the vision statement and links to everything else."""

    def page(self, project: str) -> str:
        from esoi.understanding.readable_records import readme
        cfg, found = load_project(project)
        return readme.top_page(cfg, found, layout="links")
