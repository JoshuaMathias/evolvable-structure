"""The one balanced number of Structure Quality: seven dimensions, weights and budgets fixed here before any alternative is scored.

Why these weights: scope, coupling and preserved behavior are the failures that cost the most when they happen (an arm off its interface,
a library that names its consumer, a refactor that deletes behavior production uses), so each carries 0.20 or 0.15 of the number; size and
reuse carry 0.15 each because they are the cheapest to see and the easiest to game; flow fidelity carries 0.10 and the public surface 0.05
because they are measured on fewer repositories. No weight is above a quarter, so no single dimension can win (rule S45 reads a winner that
does: a scorer that looks at size alone is the bound this metric must beat). A dimension that cannot be measured on a project (no interface to
check, no records to read) is reported as not measured and the number is the weighted mean of the others, with the weight measured stated.

Changing a weight afterwards ranks earlier rows on another criterion, so a change means re-recording every arm
(``docs/explanation/a-cascade-runs-one-criterion.md``). A consumer tightens the budgets (``Budgets``), never the weights.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

WEIGHTS: Dict[str, float] = {"scope": 0.20, "size": 0.15, "coupling": 0.20, "reuse": 0.15, "flow": 0.10, "surface": 0.05, "behavior": 0.15}
SOUND_FLOOR = 0.80   # the balanced number at or above which a structure is called sound
LOW_DIMENSION = 0.60   # a dimension below this is named as a weak one in the report


@dataclass(frozen=True)
class Budgets:
    function_lines: int = 100
    module_lines: int = 600
    files_per_folder: int = 30
    children_per_intent: int = 8
    depth: int = 7
    protocols_per_unit: int = 2
    clone_window: int = 30   # tokens in a window that counts as copied code
    duplication_budget: float = 0.15   # share of code copied between files at which the reuse dimension reaches zero
    min_cochange_support: int = 5
    min_cochange_confidence: float = 0.8
    history_commits: int = 400
    consumers: tuple = ()   # names a library must not mention (its own consumers), declared by the project

    def tightened(self, **overrides) -> "Budgets":
        for key, value in overrides.items():
            current = getattr(self, key)
            if isinstance(current, (int, float)) and key != "consumers" and value > current and not key.startswith("min_"):
                raise ValueError(f"a consumer may tighten the budget {key} (at most {current}), not loosen it to {value}")
        return replace(self, **overrides)


@dataclass
class Dimension:
    name: str
    score: Optional[float]   # 0 to 1, or None when the project gives nothing to measure
    parts: Dict[str, float] = field(default_factory=dict)
    offenders: List[str] = field(default_factory=list)   # worst first
    note: str = ""


def share(good: int, total: int) -> Optional[float]:
    return None if total <= 0 else round(good / total, 4)


def mean(values: List[Optional[float]]) -> Optional[float]:
    kept = [v for v in values if v is not None]
    return round(sum(kept) / len(kept), 4) if kept else None


def combine(values: List[Optional[float]]) -> Optional[float]:
    """The geometric mean of the parts of one dimension that were measured, none counted below 0.01: a part that fails outright pulls the whole
    dimension down instead of being averaged away by parts that are fine (a thousand files in one folder is not offset by short functions)."""
    kept = [max(v, 0.01) for v in values if v is not None]
    if not kept:
        return None
    product = 1.0
    for v in kept:
        product *= v
    return round(product ** (1 / len(kept)), 4)


def balanced(dimensions: List[Dimension]) -> Dict[str, object]:
    """``{score, measured_weight, weak, verdict}`` from the dimensions: the weighted mean over those measured."""
    measured = [d for d in dimensions if d.score is not None]
    weight = sum(WEIGHTS[d.name] for d in measured)
    score = round(sum(WEIGHTS[d.name] * d.score for d in measured) / weight, 4) if weight else None
    weak = [d.name for d in measured if d.score < LOW_DIMENSION]
    verdict = "unmeasured" if score is None else ("sound" if score >= SOUND_FLOOR else "unsound")
    flagged = [d.name for d in dimensions if d.offenders]
    return {"score": score, "measured_weight": round(weight, 4), "weak": weak, "flagged": flagged, "verdict": verdict}
