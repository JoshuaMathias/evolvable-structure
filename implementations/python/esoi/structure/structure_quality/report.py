"""Print a Structure Quality report: the number, each dimension, and the worst offenders. Advisory text; nothing here sets an exit code."""
from __future__ import annotations

from typing import Any, Dict, List

from esoi.structure.structure_quality.balance import REFERENCE_LINE, REFERENCE_STATES, WEIGHTS

OFFENDERS_SHOWN = 5


def dimension_lines(name: str, weight: float, dim: Dict[str, Any], shown: int) -> List[str]:
    """The report lines of one dimension: its score and parts, then its first offenders."""
    value = "not measured" if dim["score"] is None else f"{dim['score']:.3f}"
    parts = ", ".join(f"{k} {v}" for k, v in dim["parts"].items())
    out = [f"  {name:<9}{value:>12}  weight {weight:.2f}  {parts}" + (f"  ({dim['note']})" if dim["note"] else "")]
    out += [f"      - {text}" for text in dim["offenders"][:shown]]
    if len(dim["offenders"]) > shown:
        out.append(f"      ... and {len(dim['offenders']) - shown} more")
    return out


def lines(report: Dict[str, Any], shown: int = OFFENDERS_SHOWN) -> List[str]:
    number = "not measured" if report["score"] is None else f"{report['score']:.3f}"
    out = [f"structure quality {number} ({report['verdict'].replace('_', ' ')}; reference line {REFERENCE_LINE:.2f}, from {len(REFERENCE_STATES)} measured kept structures "
           f"scoring {min(REFERENCE_STATES.values()):.2f} to {max(REFERENCE_STATES.values()):.2f}) at stage {report['stage']}: "
           f"{report['files']} files in {report['units']} units",
           f"  measured: {', '.join(report['measured']) or 'nothing'} ({report['measured_weight']:.2f} of the weight)"
           + (f"; not measured: {', '.join(report['not_measured'])}, their weight shared out over the measured ones in proportion" if report["not_measured"] else "")]
    for name, weight in WEIGHTS.items():
        out += dimension_lines(name, weight, report["dimensions"][name], shown)
    if report["weak"]:
        out.append("weak dimensions: " + ", ".join(report["weak"]) + "; next: fix the worst offenders of each at its source (docs/how-to/measure-structure-quality.md)")
    return out
