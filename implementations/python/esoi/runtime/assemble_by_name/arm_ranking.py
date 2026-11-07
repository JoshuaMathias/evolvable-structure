"""Rank the arms of one solution best first from the scope's own leaderboard, and say whether the selected arm's lead is significant."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from esoi.runtime.implementation_selection import selection_registry
from esoi.structure.intent_registry import config as config_module
from esoi.structure.intent_registry import registry as registry_module


def read_leaderboard(assembler: Any, solution_id: str):
    """``(configuration, latest result row per implementation)`` of the solution's component, from the scope's own records."""
    from esoi.optimization.leaderboard import results_log
    cfg = config_module.load(Path(assembler.records) / "esoi.toml")
    loaded = registry_module.load(cfg)
    row = next((r for r in loaded.every_solution() if r.get("solution_id") == solution_id), {})
    component, _ = registry_module.first_arm(cfg, row.get("metric_command", ""))
    results = results_log.latest_results(cfg.results_path).get(component, {}) if component and cfg.results_path.is_file() else {}
    return cfg, results


def selected_lead(cfg: Any, results: Dict[str, Any], by_key: Dict[str, str], known: List[str], selected: str) -> float:
    """1.0 when the selected arm's lead over its runner-up is significant by the selection's own decisions, else 0.0."""
    from esoi.optimization.leaderboard import results_log, rival_decisions
    rivals = {by_key[n]: results[by_key[n]] for n in known if n != selected}
    found = rival_decisions.decisions({by_key[selected]: results[by_key[selected]], **rivals}, by_key[selected], cfg.evaluation,
                                      None, results_log.per_case_rows(cfg))
    runner_up = next((d for d in found if selection_registry.key(d.rival) == known[0 if known[0] != selected else 1]), None)
    return 1.0 if runner_up is not None and runner_up.outcome == "incumbent" and runner_up.significant else 0.0


def metric_order(assembler: Any, solution_id: str, selected: str = "") -> Tuple[List[str], Optional[float], str]:
    """``(arm names best first, lead, note)`` for a seat, from the scope's own leaderboard when it has records and results:
    the latest rows of the solution's component ranked as the leaderboard ranks them, and ``lead`` 1.0 when the selected
    arm's lead over its runner-up is significant by the same ``decisions`` the selection uses, else 0.0. Without records or
    a results file (a packaged snapshot) the order is the snapshot's names and ``lead`` is None; ``note`` says which."""
    names = assembler.names(solution_id)
    order = [selected] + [n for n in names if n != selected] if selected else list(names)
    if assembler.records is None:
        return order, None, f"{solution_id}: no records packaged, so arms are tried in the snapshot's order"
    try:
        cfg, results = read_leaderboard(assembler, solution_id)
    except Exception as error:
        return order, None, f"{solution_id}: the leaderboard could not be read ({type(error).__name__}: {error}); using record order"
    from esoi.optimization.leaderboard import ranking
    by_key = {selection_registry.key(impl): impl for impl in results}
    ranked = [selection_registry.key(r["impl"]) for r in ranking.rank(results)] if results else []
    known = [n for n in ranked if n in names]
    if not known:
        return order, None, f"{solution_id}: no results file rows for its arms, so arms are tried in record order"
    best_first = known + [n for n in names if n not in known]
    if selected:
        best_first = [selected] + [n for n in best_first if n != selected]
    lead = selected_lead(cfg, results, by_key, known, selected) if selected and by_key.get(selected) and len(known) > 1 else 0.0
    return best_first, lead, f"{solution_id}: arms ranked by the leaderboard in {cfg.results}"
