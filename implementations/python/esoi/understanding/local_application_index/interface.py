"""The interface of LocalApplicationIndexing: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.optimization.measurement_harness.interface import count_cases
from esoi.understanding.local_application_index import projects  # noqa: F401  (re-exported: the command line calls this unit through its interface)


@solution("local-application-index", kind="event", entry="describe", example=".")
@runtime_checkable
class LocalApplicationIndexing(Protocol):
    """The cases the index of projects that apply ESOI is measured on."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("local-application-index", "live_index")
class LiveIndex:
    """The index folder in the user's home, measured on the cases of its component."""

    def describe(self, project: str) -> Dict[str, int]:
        return count_cases(project, "index_projects")
