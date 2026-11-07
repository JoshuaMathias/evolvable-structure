"""The leaderboard's verdict on each solution's selected arm, as the evidence ``esoi lock`` records beside the arm it locks.

Standard library and ``esoi`` only.
"""
from __future__ import annotations

from typing import Any, Dict, List

from esoi.optimization.leaderboard import arm_selection, results_log, rival_decisions, switching_policy, verdict_labels
from esoi.structure.intent_registry import registry as registry_module


def attach_evidence(config: Any, snapshot: Dict[str, Any]) -> None:
    """Add to each solution of a snapshot the ``evidence`` (``verdict``, ``detail``, ``p``) the results log gives it, which ``esoi lock`` records beside the arm it locks."""
    for sid, found in records_evidence(config).items():
        if sid in snapshot:
            snapshot[sid]["evidence"] = found


def incumbent_p_values(config: Any, loaded: Any, row: Dict[str, str], results: Dict[str, Any], history: Dict[str, Any], per_case: Any) -> List[float]:
    """The p-values that the solution's selected arm beats each rival, from the rival decisions."""
    component, impl = arm_selection.selected_arm(config, row, "", loaded)
    rows = results.get(component, {})
    if impl not in rows:
        return []
    decided = rival_decisions.decisions(rows, impl, config.evaluation, history.get(component), per_case,
                                        switching_policy.policy_for(config, row.get("solution_id", ""), component, per_case))
    return [d.p_incumbent for d in decided if d.p_incumbent is not None]


def records_evidence(config: Any, loaded: Any = None) -> Dict[str, Dict[str, Any]]:
    """``{solution_id: {"verdict", "detail", "p"}}`` from the records and the results log of ``config`` (an ``esoi.structure.intent_registry.config.Config``):
    the leaderboard's verdict on each evaluated solution's selected arm, and the smallest Holm-adjusted p-value that the selected
    arm is better than a rival (``None`` when no test was possible). Solutions with no results are left out."""
    loaded = loaded or registry_module.load(config)
    if not config.results_path.is_file():
        return {}
    history = results_log.all_results(config.results_path)
    results = results_log.latest_by_impl(history)
    per_case = results_log.per_case_rows(config)
    solutions = loaded.every_solution()
    verdicts = verdict_labels.solution_verdicts(config, solutions, results, history, loaded, per_case)
    out: Dict[str, Dict[str, Any]] = {}
    for row in solutions:
        sid = row.get("solution_id", "")
        found = verdicts.get(sid)
        if not found or not found["component"]:
            continue
        ps = incumbent_p_values(config, loaded, row, results, history, per_case)
        out[sid] = {"verdict": found["verdict"], "detail": found["detail"], "p": round(min(ps), 6) if ps else None}
    return out
