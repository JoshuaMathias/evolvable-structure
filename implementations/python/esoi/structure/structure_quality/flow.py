"""Dimension 5, flow fidelity: the written flow of each intent against the code, from the coherence gate that Structure Check already runs.

For each intent the gate reports the share of recorded ``uses`` edges the code shows strongly (precision) and the share of edges it could
check (coverage). The part is the mean of the two across intents. A project with no records has no flow to compare, so the dimension is
not measured; the caller passes the gate's report in so that Structure Quality never imports the check that calls it.
"""
from __future__ import annotations

from typing import Dict, Optional

from esoi.structure.structure_quality.balance import Dimension, mean


def measure(report: Optional[Dict[str, object]]) -> Dimension:
    intents = (report or {}).get("intents") or []
    values = []
    offenders = []
    for row in intents:
        pair = [row.get("code_precision"), row.get("code_coverage")]
        pair = [v for v in pair if v is not None]
        if pair:
            values.append(sum(pair) / len(pair))
            if row.get("code_precision") is not None and row["code_precision"] < 1.0:
                offenders.append(f"{row['intent']}: {row['code_edges_strong']} of {row['code_edges_checkable']} checkable edges strongly shown in code "
                                 f"(precision {row['code_precision']}, coverage {row.get('code_coverage')})")
    value = mean([round(v, 4) for v in values])
    return Dimension("flow", value, {"precision_and_coverage": value} if value is not None else {}, offenders)
