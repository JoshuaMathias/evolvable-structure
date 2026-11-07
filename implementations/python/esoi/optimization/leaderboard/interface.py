"""The interface of Leaderboarding: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.optimization.leaderboard import board_report, cascade_report, evidence_table  # noqa: F401  (re-exported: the command line calls this unit through its interface)


@solution("leaderboard", kind="evaluate", entry="standings", example=".")
@runtime_checkable
class Leaderboarding(Protocol):
    """How many recorded rows each measured component has in the project's results log."""

    def standings(self, project: str) -> Dict[str, int]: ...


@implementation("leaderboard", "margin-leaderboard")
class MarginLeaderboard:
    """The latest rows per component, ranked by pass rate with a margin."""

    def standings(self, project: str) -> Dict[str, int]:
        from esoi.optimization.leaderboard import results_log
        cfg, found = load_project(project)
        return {component: len(rows) for component, rows in results_log.latest_results(cfg.results_path).items()}
