"""The interface of ImplementationSelecting: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.runtime.implementation_selection.lock_command import run_lock  # noqa: F401  (re-exported: the command line calls this unit through its interface)


@solution("implementation-selection", kind="event", entry="choose", example="structure-check")
@runtime_checkable
class ImplementationSelecting(Protocol):
    """The implementation that serves a solution of the calling project now, and the layer of the cascade that chose it."""

    def choose(self, solution_id: str) -> Any: ...


@implementation("implementation-selection", "declarations")
class Declarations:
    """The runtime cascade of ``esoi.runtime.implementation_selection.declare``: call, context, environment, deployment, then the records' default."""

    def choose(self, solution_id: str) -> Any:
        from esoi.runtime.implementation_selection import selection_cascade
        return selection_cascade.choose(solution_id)


def attach_evidence(config: Any, snapshot: Dict[str, Any]) -> None:
    """Add the results log's verdict on each solution's selected arm to a selection snapshot (the evidence ``esoi lock`` records)."""
    from esoi.runtime.implementation_selection import lock
    lock.attach_evidence(config, snapshot)
