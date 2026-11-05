"""Reading the solution, implementation and component records the coherence check scores: id lists, csv rows and each solution's selected implementation."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


def ids(text: str) -> List[str]:
    return [x.strip() for x in (text or "").replace(",", ";").split(";") if x.strip()]


def read(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def selected_record(sid: str, row: Dict[str, str], every_impl: List[Dict[str, str]]) -> Dict[str, str]:
    from esoi.structure.intent_registry.records import match_implementations
    mine = {r["implementation_id"]: r for r in every_impl if r.get("solution_id") == sid}
    chosen = (row.get("selected") or "").strip()
    if not chosen:
        return {}
    hit = match_implementations(sid, [chosen], mine)[0].get(chosen, "")
    return mine.get(hit, {})
