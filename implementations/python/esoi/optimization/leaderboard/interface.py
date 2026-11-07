"""The interface of Leaderboarding: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.optimization.leaderboard import held_out_parts, rival_pairing, stage_standings
from esoi.optimization.leaderboard.board_report import board as board_report_board
from esoi.optimization.leaderboard.verdict_labels import solution_verdicts, verdict as verdict_labels_verdict
from esoi.optimization.leaderboard.cascade_report import run_cli as cascade_report_run_cli
from esoi.optimization.leaderboard.evidence_table import BEGIN, END, run_cli as evidence_table_run_cli
from esoi.optimization.leaderboard.rival_pairing import incomparable_rivals, rival_pairs, stale_rivals
from esoi.optimization.leaderboard.lock_evidence import attach_evidence as lock_evidence_attach_evidence, records_evidence as lock_evidence_records_evidence
from esoi.optimization.leaderboard.stage_standings import decide, standings
from esoi.optimization.leaderboard.held_out_parts import selection_view

__all__ = ["BEGIN", "END", "Leaderboarding", "board_report_board", "cascade_report_run_cli", "decide", "evidence_table_run_cli", "held_out_parts", "incomparable_rivals", "lock_evidence_attach_evidence", "lock_evidence_records_evidence", "rival_pairing", "rival_pairs", "selection_view", "solution_verdicts", "stage_standings", "stale_rivals", "standings", "verdict_labels_verdict"]


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
