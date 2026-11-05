"""Print a Structure Quality report: the number, each dimension, and the worst offenders. Advisory text; nothing here sets an exit code."""
from __future__ import annotations

from typing import Any, Dict, List

from esoi.structure.structure_quality.balance import SOUND_FLOOR, WEIGHTS

OFFENDERS_SHOWN = 5


def lines(report: Dict[str, Any], shown: int = OFFENDERS_SHOWN) -> List[str]:
    number = "not measured" if report["score"] is None else f"{report['score']:.3f}"
    out = [f"structure quality {number} ({report['verdict']}; sound is {SOUND_FLOOR:.2f} or more) at stage {report['stage']}: "
           f"{report['files']} files in {report['units']} units, {report['measured_weight']:.2f} of the weight measured"]
    for name, weight in WEIGHTS.items():
        dim = report["dimensions"][name]
        value = "not measured" if dim["score"] is None else f"{dim['score']:.3f}"
        parts = ", ".join(f"{k} {v}" for k, v in dim["parts"].items())
        out.append(f"  {name:<9}{value:>12}  weight {weight:.2f}  {parts}" + (f"  ({dim['note']})" if dim["note"] else ""))
        for text in dim["offenders"][:shown]:
            out.append(f"      - {text}")
        if len(dim["offenders"]) > shown:
            out.append(f"      ... and {len(dim['offenders']) - shown} more")
    if report["weak"]:
        out.append("weak dimensions: " + ", ".join(report["weak"]) + "; next: fix the worst offenders of each at its source (docs/how-to/measure-structure-quality.md)")
    return out
