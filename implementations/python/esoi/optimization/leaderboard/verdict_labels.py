"""The verdict of a selected implementation (WIN, TIE, LOSS or UNMEASURED) for a component, a solution and each circumstance slice."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import Registry
from esoi.optimization.leaderboard.arm_selection import selected_arm
from esoi.optimization.leaderboard.results_log import Row, Rows, all_results, as_whole, per_case_rows
from esoi.optimization.leaderboard.rival_decisions import best_guess, decisions
from esoi.optimization.leaderboard.rival_pairing import rival_pairs
from esoi.optimization.leaderboard.switching_policy import Policy, policy_for


def slice_verdicts(component: str, incumbent: str, slices: Dict[str, Dict[str, Dict[str, List[Row]]]],
                   eval_dir: Optional[Path] = None) -> List[Tuple[str, str, str]]:
    """``(circumstance id, verdict label, detail)`` of ``incumbent`` in each circumstance the component has slice rows for
    (``slice_results``). A slice verdict is a PROPOSAL read by a person: nothing is selected by it. Name the incumbent the
    marginal-value rule names (the no-add-on baseline arm, to which a tie goes), not the arm that is selected. An add-on must show
    its marginal value, so a slice is judged with ``require_significance``."""
    out = []
    for cid, group in sorted(slices.get(component, {}).items()):
        history = {impl: [as_whole(r) for r in found] for impl, found in group.items()}
        out.append((cid, *verdict({impl: found[-1] for impl, found in history.items()}, incumbent, eval_dir, history,
                                  policy=Policy(require_significance=True))))
    return out


def no_rival_detail(unmatched: List[Tuple[str, str]]) -> str:
    """Why no rival could be compared with the selected implementation."""
    if unmatched:
        return ("no rival was measured on the same cases and sample as the selected "
                f"implementation: {'; '.join(f'{i} {why}' for i, why in unmatched)}")
    return "no rival implementation was measured on the same cases"


def verdict(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
            history: Optional[Dict[str, List[Row]]] = None, per_case: Optional[List[Row]] = None,
            policy: Optional[Policy] = None) -> Tuple[str, str]:
    """How the selected implementation stands against the other measured ones, as ``(label, detail)``. LOSS: a rival should replace
    it. WIN: it is shown, or guessed, better than every rival. TIE: no rival is shown better, so it stays. The detail says which
    basis decided each rival: a significance test or a best guess."""
    if rows.get(selected) is None:
        guess, why = best_guess(rows, eval_dir)
        return "UNMEASURED", "the selected implementation has no recorded row" + (f"; {why}" if len(rows) else "")
    pairs, unmatched = rival_pairs(rows, selected, eval_dir, history)
    if not pairs:
        return "UNMEASURED", no_rival_detail(unmatched)
    return outcome_label(decisions(rows, selected, eval_dir, history, per_case, policy))


def outcome_label(found: list) -> Tuple[str, str]:
    """``(label, detail)`` from the decisions against each rival: LOSS if one should replace the selected arm, WIN if it beat all, else TIE."""
    text = "; ".join(d.text for d in sorted(found, key=lambda d: d.rival))
    beaten = sorted(d.rival for d in found if d.outcome == "rival" and d.switch)
    if beaten:
        return "LOSS", "beaten by " + ", ".join(beaten) + ": " + text
    return ("WIN" if all(d.outcome == "incumbent" for d in found) else "TIE"), text


def solution_verdicts(config: Config, solutions: List[Row], results: Optional[Dict[str, Rows]] = None,
                      history: Optional[Dict[str, Dict[str, List[Row]]]] = None, registry: Optional[Registry] = None,
                      per_case: Optional[List[Row]] = None) -> Dict[str, Dict[str, str]]:
    """{solution_id: {"verdict", "detail", "component", "selected_by"}} for every solution, judged on the
    first harness arm of its ``metric_command`` (the primary metric; later arms are listed on the board)."""
    if results is None:
        history = all_results(config.results_path)
        results = {comp: {impl: rows[-1] for impl, rows in impls.items()} for comp, impls in history.items()}
    per_case = per_case_rows(config) if per_case is None else per_case
    return {row["solution_id"]: solution_verdict(config, row, results, history, registry, per_case) for row in solutions}


def solution_verdict(config: Config, row: Row, results: Dict[str, Rows], history: Optional[Dict[str, Dict[str, List[Row]]]],
                     registry: Optional[Registry], per_case: List[Row]) -> Dict[str, str]:
    """The verdict of one solution on the first harness arm of its metric command."""
    comp, impl = selected_arm(config, row, "", registry)
    if not comp:
        return dict(verdict="UNMEASURED", detail="no harness metric", component="", selected_by=row.get("selected_by", ""))
    label, detail = verdict(results.get(comp, {}), impl, config.evaluation, (history or {}).get(comp), per_case,
                            policy_for(config, row["solution_id"], comp, per_case))
    return dict(verdict=label, detail=detail, component=comp, selected_by=row.get("selected_by", ""))
