"""The dollar cost to record for a run: what the provider reported, else tokens times the configured price."""
from __future__ import annotations

from typing import Any, Dict, Optional

from esoi.optimization.when_metrics_are_run.interface import SIMULATED_MODEL, price_for
from esoi.structure.intent_registry.config import Config


def run_cost(config: Config, summary: Dict[str, Any], model: Optional[str]) -> Any:
    """The dollar cost to record for a run: what the provider reported when that is more than zero, else tokens times
    the configured price of the model, else 0.0 for a run that called no model, else ``""`` (unknown, never a
    zero that reads as free). Prices are USD per million tokens, ``prices = { "model" = { input = 3.0, output = 15.0 } }``."""
    reported = float(summary.get("cli_reported_cost_usd", summary.get("cost_usd", 0.0)) or 0.0)
    if model == SIMULATED_MODEL:
        return 0.0   # a deterministic stand-in: its calls are counted, but nothing is spent
    if reported > 0:
        return reported
    if not summary.get("model_calls"):
        return 0.0
    price = price_for(config, model)
    if price is None or not (summary.get("tokens_in") or summary.get("tokens_out")):
        return ""
    return round((float(summary.get("tokens_in") or 0) * float(price.get("input", 0))
                  + float(summary.get("tokens_out") or 0) * float(price.get("output", 0))) / 1_000_000, 6)
