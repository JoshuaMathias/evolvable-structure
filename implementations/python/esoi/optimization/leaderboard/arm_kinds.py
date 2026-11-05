"""What kind of arm an implementation is (ablation, validity check, alternative or live code) and why a component with complementary arms is never ranked."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from esoi.runtime.implementation_selection.variants import base_of
from esoi.optimization.leaderboard.results_log import Row


def invariant_reason(component: str, eval_dir: Optional[Path] = None) -> str:
    """Why the component is not ranked: the reason in ``<component>/invariant.txt`` when its implementations are
    complementary (not alternatives)."""
    if eval_dir is not None:
        note = Path(eval_dir) / component / "invariant.txt"
        if note.is_file():
            return note.read_text(encoding="utf-8").strip()
    return ""


ARM_MARKER = re.compile(r'\s*"""\s*(ABLATION|ALTERNATIVE|VALIDITY)')
NOT_RIVALS = ("ablation", "validity")   # shown and tagged, never offered as the thing to adopt


def arm_kind(row: Row, eval_dir: Optional[Path] = None) -> str:
    """What an implementation is for, from the first word of its module docstring: ``ablation`` (a part of a
    candidate measured alone), ``validity``
    (the metric's own offline check that it can tell good from bad, which no implementation can lose to),
    ``alternative``, or ``""`` for live code. Shown beside every row so a reader can tell a rival from a reference."""
    if eval_dir is None:
        return ""
    path = Path(eval_dir) / row.get("component", "") / "impls" / (base_of(row["impl"]) + ".py")
    if not path.is_file():
        return ""
    found = ARM_MARKER.match(path.read_text(encoding="utf-8"))
    if not found:
        return ""
    return found.group(1).lower()


def is_ablation(row: Row, eval_dir: Optional[Path] = None) -> bool:
    """True when the implementation is no rival: an ABLATION returns less than the whole job, and a VALIDITY arm
    checks the metric rather than competing on it, so both are ranked and never offered as the thing to adopt."""
    return arm_kind(row, eval_dir) in NOT_RIVALS
