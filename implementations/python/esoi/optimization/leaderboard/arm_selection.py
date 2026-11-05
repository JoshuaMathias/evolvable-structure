"""Which arm of a component a solution's selection means, from its records and the results log."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import Registry, harness_arms
from esoi.optimization.leaderboard.results_log import Row, all_results


def selected_arm(config: Config, row: Row, component: str = "", registry: Optional[Registry] = None) -> Tuple[str, str]:
    """``(component, arm)`` the solution's selection means on ``component`` (default: the first component of its metric command).
    The command lists the arms to measure; the choice is the solution's ``selected`` in the records: a name, ``solution:name`` or
    the path of the implementation's file, read as an arm when the command lists it or the results log holds a run of it on the component. The
    registry maps a file path to its arm name. With no such ``selected`` it is the first arm the command lists for the component. Promotion therefore changes
    ``selected`` and never the command."""
    arms = harness_arms(config, row.get("metric_command", ""))
    if not arms:
        return "", ""
    component = component or arms[0][0]
    listed = [impl for comp, impl in arms if comp == component]
    cell = (row.get("selected") or "").strip()
    sid = row.get("solution_id", "")
    records = {r.get("implementation_id", ""): r for r in (registry.implementations if registry is not None else [])}
    chosen = ""
    if cell:
        by_path = next((i.split(":", 1)[-1] for i, r in records.items() if i.startswith(f"{sid}:") and (r.get("filepath") or "").strip() == cell), "")
        chosen = by_path or cell.split(":", 1)[-1]
    known = chosen in listed or chosen in all_results(config.results_path).get(component, {})
    return component, chosen if chosen and known else (listed[0] if listed else "")


def selected_impls(config: Config, solutions: List[Row], registry: Optional[Registry] = None) -> Dict[str, str]:
    """{component: selected impl name} for solutions whose metric is one or more harness commands (see ``selected_arm``)."""
    out: Dict[str, str] = {}
    for row in solutions:
        for comp, _ in harness_arms(config, row.get("metric_command", "")):
            out.setdefault(comp, selected_arm(config, row, comp, registry)[1])
    return out
