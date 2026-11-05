"""The interface of ReviewTracking: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project


@solution("review-tracker", kind="evaluate", entry="stale", example=".")
@runtime_checkable
class ReviewTracking(Protocol):
    """The tracker tabs that are out of date with the records (empty when none is)."""

    def stale(self, project: str) -> List[str]: ...


@implementation("review-tracker", "tracker-and-sheet")
class TrackerAndSheet:
    """Tracker tabs written beside the records, and synced with a sheet on request."""

    def stale(self, project: str) -> List[str]:
        from esoi.understanding.review_tracker import tracker
        cfg, found = load_project(project)
        return [str(tab) for tab in tracker.stale(cfg, found)]
