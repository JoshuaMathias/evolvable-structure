"""The interface of WinnerPromoting: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, Tuple, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.optimization.promote_the_winner import promote  # noqa: F401  (re-exported: the command line calls this unit through its interface)

__all__ = ["WinnerPromoting", "promote"]


@solution("promote-the-winner", kind="evaluate", entry="proposals", example=".")
@runtime_checkable
class WinnerPromoting(Protocol):
    """What would be promoted now: each solution a rival clearly beats, with the status of the proposal. Nothing is changed."""

    def proposals(self, project: str) -> List[Tuple[str, str]]: ...


@implementation("promote-the-winner", "margin-promotion")
class MarginPromotion:
    """A rival that beats the selected implementation by the margin the solution's policy asks for."""

    def proposals(self, project: str) -> List[Tuple[str, str]]:
        from esoi.optimization.promote_the_winner import promote
        cfg, found = load_project(project)
        return [(one.solution_id, one.status) for one in promote.propose(cfg, found)]
