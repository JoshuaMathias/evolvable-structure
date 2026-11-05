"""Read the committed results log and the per-case log: rows by component and implementation, with whole-run rows kept apart from partial and slice rows."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from esoi.structure.intent_registry.config import Config


Row = Dict[str, str]
Rows = Dict[str, Row]

SLICE_MARK = "slice:"


def slice_id(row: Row) -> str:
    """The circumstance a derived row describes (``slice:small-file`` or ``sample:12/slice:small-file``), else ``""``."""
    last = (row.get("sample") or "").strip().rsplit("/", 1)[-1]
    return last[len(SLICE_MARK):] if last.startswith(SLICE_MARK) else ""


def is_partial(row: Row) -> bool:
    """A row that scored named cases (``only:``) or one circumstance's cases (``slice:``): never the default verdict's evidence."""
    return bool(slice_id(row)) or (row.get("sample") or "").strip().startswith("only:")


def all_results(path: Path, slices: bool = False) -> Dict[str, Dict[str, List[Row]]]:
    """{component: {impl: [rows, oldest first]}}: every row of the results log, in date order (file order within a date).
    Derived slice rows are left out unless ``slices`` is true (``slice_results`` reads those)."""
    out: Dict[str, Dict[str, List[Row]]] = {}
    if not Path(path).exists():
        return out
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if not (row.get("component") and row.get("impl")):
                continue   # a blank or half-written line is no result
            if bool(slice_id(row)) != slices:
                continue
            out.setdefault(row["component"], {}).setdefault(row["impl"], []).append(row)
    for impls in out.values():
        for history in impls.values():
            history.sort(key=lambda r: r.get("date") or "")   # stable: a later line of the same date stays later
    return out


def slice_results(path: Path) -> Dict[str, Dict[str, Dict[str, List[Row]]]]:
    """{component: {circumstance id: {impl: [rows, oldest first]}}}: the derived slice rows of the results log."""
    out: Dict[str, Dict[str, Dict[str, List[Row]]]] = {}
    for comp, impls in all_results(path, slices=True).items():
        for impl, history in impls.items():
            for found in history:
                out.setdefault(comp, {}).setdefault(slice_id(found), {}).setdefault(impl, []).append(found)
    return out


def as_whole(row: Row) -> Row:
    """A slice row read as the run of its slice's cases: the ``slice:`` part of its ``sample`` label dropped, so ``verdict``
    judges the arms of one circumstance exactly as it judges the arms of one case set."""
    head, _, last = (row.get("sample") or "").strip().rpartition("/")
    return {**row, "sample": head if last.startswith(SLICE_MARK) else (row.get("sample") or "")}


def latest_results(path: Path, whole: bool = False) -> Dict[str, Rows]:
    """{component: {impl: row}} keeping the newest row per implementation. With ``whole``, the newest row that scored a whole
    run (not ``only:`` or ``slice:``), the row staleness is judged on; an arm with none is left out."""
    return {comp: {impl: found[-1] for impl, history in impls.items() if (found := [r for r in history if not (whole and is_partial(r))])}
            for comp, impls in all_results(path).items()}


PER_CASE_KEY = ("component", "impl", "cases_sha", "sample", "case_id")


def per_case_rows(config: Config, every: bool = False) -> List[Row]:
    """The per-case log (``esoi run --record`` writes it; empty when the project has none yet): the newest row of each (arm,
    cases, sample, case) or, with ``every``, every row in file order. A repeated header line (two recorders creating the
    file together) is not a row."""
    path = config.root / config.per_case
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("component") != "component"]
    return rows if every else list({tuple(r.get(k) or "" for k in PER_CASE_KEY): r for r in rows}.values())
