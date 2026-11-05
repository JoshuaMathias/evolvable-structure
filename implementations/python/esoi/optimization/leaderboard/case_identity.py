"""What a results row was scored on (the case files, their digest and the comparison key), so that only rows scored on the same cases are ever compared."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Tuple

from esoi.optimization.leaderboard.results_log import Row


def cases_files(component: str, eval_dir: Path) -> List[Path]:
    """The case files a component is scored on: ``cases.json`` (or ``cases.csv`` when the dataset is reviewed as a
    sheet), plus every ``datasets/*.json`` of a component whose cases live in a dataset folder."""
    folder = Path(eval_dir) / component
    main = next((folder / n for n in ("cases.json", "cases.csv") if (folder / n).is_file()), None)
    return ([main] if main else []) + sorted((folder / "datasets").glob("*.json"))


def cases_digest(component: str, eval_dir: Path) -> str:
    """Short hash of everything ``cases_files`` names: the ``cases_sha`` a recorded run is pinned to. Line endings
    are normalised first, because a dataset reviewed as a sheet comes back from the sheet with either kind."""
    files = cases_files(component, eval_dir)
    if not files:
        return ""
    return hashlib.sha256(b"".join(f.read_bytes().replace(b"\r\n", b"\n") for f in files)).hexdigest()[:8]


def unverified(row: Row) -> bool:
    """A row recorded without provenance (no ``cases_sha``): shown, flagged, never trusted as evidence."""
    return not (row.get("cases_sha") or "").strip()


def cases_key(row: Row) -> Tuple[str, str, int]:
    """What a row was scored on: ``(cases_sha, sample, case count)``. ``sample`` is blank for the full set (and for rows
    recorded before the column existed, which the case count then tells apart)."""
    try:
        count = int(float(row.get("cases") or 0))
    except ValueError:
        count = 0
    return (row.get("cases_sha") or "", (row.get("sample") or "").strip(), count)


def comparable(a: Row, b: Row) -> bool:
    """Two rows are comparable only when scored on the same cases: the same case file, the same sample and the same
    number of cases (blank == blank: legacy rows)."""
    return cases_key(a) == cases_key(b)


def describe_cases(row: Row) -> str:
    """``1137 cases`` or ``40 cases (sample:40)``, with the case file when it is recorded."""
    sha, sample, count = cases_key(row)
    return f"{count} cases" + (f" ({sample})" if sample else "") + (f" on cases_sha {sha}" if sha else "")
