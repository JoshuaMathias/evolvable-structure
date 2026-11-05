"""Decide whether running an arm may spend money: its PAID and SIMULATED declarations, its price, and the call budget that stops a run."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, Optional

from esoi.runtime.implementation_selection import variants
from esoi.structure.intent_registry.config import Config


class BudgetExceeded(RuntimeError):
    """The run made more model calls than its budget allows."""


SIMULATED_MODEL = "simulated"   # the model recorded for an arm that declares SIMULATED = True


def declares_constant(path: Path, name: str) -> bool:
    """Whether a module sets ``<name> = True`` at module level (the markers ``PAID`` and ``SIMULATED``)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    return any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
               and isinstance(n.value, ast.Constant) and n.value.value is True for n in tree.body)


def declares_paid(path: Path) -> bool:
    """Whether an implementation module sets ``PAID = True`` at module level (it calls a model that costs money)."""
    return declares_constant(path, "PAID")


def declares_simulated(path: Path) -> bool:
    """Whether an implementation module sets ``SIMULATED = True``: it meters a deterministic stand-in for a model."""
    return declares_constant(path, "SIMULATED")


def impl_path(config: Config, component: str, impl: str) -> Path:
    return config.evaluation / component / "impls" / f"{impl}.py"


def declared_live(config: Config, component: str, impl: str, max_calls: Optional[int]) -> bool:
    """Whether a run may call a model: the arm declares ``PAID = True``, is listed in ``paid_arms``, or the run was given a call budget."""
    base = variants.base_of(impl)
    return max_calls is not None or f"{component}/{base}" in config.paid_arms or declares_paid(impl_path(config, component, base))


def paid_reason(config: Config, component: str, impl: str, row: Optional[Dict[str, str]]) -> str:
    """Why running an arm may spend money, or an empty string for an offline arm: it is listed in ``paid_arms``, its
    module declares ``PAID = True``, or its last recorded run called a model. An arm that declares ``SIMULATED = True``
    (or whose last row records model ``simulated``) meters a stand-in and spends nothing, whatever its model calls: its
    cost is known (0.0), never inferred from a missing price."""
    if f"{component}/{impl}" in config.paid_arms:
        return "listed in paid_arms"
    if declares_paid(impl_path(config, component, impl)):
        return "declares PAID = True"
    if declares_simulated(impl_path(config, component, impl)) or (row or {}).get("model") == SIMULATED_MODEL:
        return ""
    if row and int(float(row.get("model_calls") or 0)) > 0:
        return "its last recorded run called a model"
    return ""


def price_for(config: Config, model: Optional[str]) -> Optional[Dict[str, float]]:
    """The ``prices`` entry for a model: the exact name, else the longest listed name that is a prefix of it (so a
    dated model id finds its family's price)."""
    if not model or not config.prices:
        return None
    if model in config.prices:
        return config.prices[model]
    listed = [name for name in config.prices if model.startswith(name)]
    return config.prices[max(listed, key=len)] if listed else None
