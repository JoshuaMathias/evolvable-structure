"""The balanced score of a metric run: accuracy, cost and time folded into one number, with the weights and budgets written
down where a person can change them (``[balance.<component>]`` in the configuration) instead of hidden in a scorer.

Why: an implementation that is two points more accurate but ten times as slow and expensive is not necessarily better, so a
metric that ranks by accuracy alone picks it anyway. Each of the three parts is turned into a score between 0 and 1:

  accuracy score = cases passed / cases run
  cost score     = 1 - (dollars per case / cost budget per case), never below 0 (a run that spends the whole budget scores 0)
  time score     = 1 - (seconds per case / time budget per case), never below 0

and the balanced score is the weighted sum (weights sum to 1). Free and instant arms score full marks on cost and time, so a
paid stage has to buy its price in accuracy, and the metric says by how much. Standard library only.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

DEFAULT_WEIGHTS = {"accuracy": 0.7, "cost": 0.15, "time": 0.15}


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def settings(table: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """The validated ``[balance.<component>]`` table (weights default to 0.7/0.15/0.15), or None when there is none.
    Raises ValueError for weights that do not sum to 1 or a budget that is not positive."""
    if not table:
        return None
    weights = {**DEFAULT_WEIGHTS, **{k: float(v) for k, v in (table.get("weights") or {}).items()}}
    if set(weights) != set(DEFAULT_WEIGHTS) or abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError(f"balance weights need accuracy, cost and time summing to 1, got {weights}")
    cost_budget = float(table.get("cost_per_case_usd", 0))
    seconds_budget = float(table.get("seconds_per_case", 0))
    if cost_budget <= 0 or seconds_budget <= 0:
        raise ValueError("balance needs cost_per_case_usd and seconds_per_case budgets above zero")
    return {"weights": weights, "cost_per_case_usd": cost_budget, "seconds_per_case": seconds_budget}


def balanced(passed: int, cases: int, cost_usd: Any, seconds: float, table: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """``{accuracy, cost_per_case, seconds_per_case, balanced}`` for one run, or ``{}`` when the component sets no balance
    or the cost is unknown (a score never treats an unknown price as free)."""
    cfg = settings(table)
    if cfg is None or cases <= 0 or cost_usd == "" or cost_usd is None:
        return {}
    accuracy = passed / cases
    per_cost, per_time = float(cost_usd) / cases, float(seconds) / cases
    w = cfg["weights"]
    score = (w["accuracy"] * accuracy + w["cost"] * clamp(1 - per_cost / cfg["cost_per_case_usd"])
             + w["time"] * clamp(1 - per_time / cfg["seconds_per_case"]))
    return {"accuracy": round(accuracy, 4), "cost_per_case": round(per_cost, 6), "seconds_per_case": round(per_time, 2),
            "balanced": round(score, 4)}
