"""The public evidence record: its columns and allowed values, reading and checking the CSV, and where a repository keeps it and which implementation each candidate means."""
from __future__ import annotations

import csv
import datetime
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


COLUMNS = ("evidence_id", "candidate", "dimension", "measure", "value", "unit", "better", "comparator", "source_url",
           "source_kind", "run_by_independent", "method_disclosed", "n", "benchmark_status", "date_published",
           "date_checked", "confounds", "note")
REQUIRED = ("evidence_id", "candidate", "dimension", "measure", "value", "unit", "better", "source_url", "source_kind",
            "run_by_independent", "method_disclosed", "benchmark_status", "date_checked")
DIMENSIONS = ("quality", "token_efficiency", "speed", "cost", "reliability", "safety", "maintenance")
BETTER = ("higher", "lower")
SOURCE_KINDS = ("independent_benchmark", "replication", "peer_reviewed", "vendor_reported", "maintainer_reported",
                "community_report", "own_run")
INDEPENDENT_KINDS = ("independent_benchmark", "replication", "peer_reviewed", "own_run")
VENDOR_KINDS = ("vendor_reported", "maintainer_reported")
RUN_BY = ("yes", "no", "unknown")
METHOD = ("yes", "partial", "no")
STATUS = ("live", "saturated", "archived", "contamination_risk", "unknown")
LETTERS = "ABCD"
FLAGS = ("single_source", "vendor_only", "stale", "saturated", "confounded", "contradicts", "no_method", "unit_mismatch",
         "contamination_risk", "not_comparable")
LIST_SEPARATOR = ";"


class EvidenceError(ValueError):
    """The evidence records are not valid; ``problems`` lists every one."""

    def __init__(self, problems: List[str]):
        self.problems = problems
        super().__init__("; ".join(problems[:5]) + (f"; and {len(problems) - 5} more" if len(problems) > 5 else ""))


@dataclass(frozen=True)
class Evidence:
    """One reported number, read and checked."""
    evidence_id: str
    candidate: str
    dimension: str
    measure: str
    value: float
    unit: str
    better: str
    comparator: str
    source_url: str
    source_kind: str
    run_by_independent: str
    method_disclosed: str
    n: Optional[int]
    benchmark_status: str
    date_published: Optional[datetime.date]
    date_checked: datetime.date
    confounds: Tuple[str, ...]
    note: str
    line: int = 0

    @property
    def independent(self) -> bool:
        return self.source_kind in INDEPENDENT_KINDS and self.run_by_independent != "no"

    @property
    def vendor_side(self) -> bool:
        return self.source_kind in VENDOR_KINDS or self.run_by_independent == "no"

    @property
    def basis(self) -> Tuple[str, str]:
        return (self.measure.strip().lower(), self.comparator.strip().lower())

    def source_key(self) -> str:
        return self.source_url.strip().lower().rstrip("/")


def norm(name: str) -> str:
    """A name compared without case, underscores or spaces (``Lexical_Only`` and ``lexical-only`` are one candidate)."""
    return re.sub(r"[\s_]+", "-", (name or "").strip().lower())


def header_problems(header: Sequence[str]) -> List[str]:
    """Columns the header lacks, and columns that are not part of the evidence record."""
    return ([f"header: column {c} is missing" for c in COLUMNS if c not in header]
            + [f"header: column {c} is not part of the evidence record" for c in header if c not in COLUMNS])


def finite_number(text: str) -> Optional[float]:
    """The number a cell holds, or None when it is not a finite number."""
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value == value and value not in (float("inf"), float("-inf")) else None


def cell_problems(cell: Dict[str, str]) -> Dict[str, str]:
    """``{column: what is wrong}`` for one row's cells, in column-check order (a column appears once)."""
    found: Dict[str, str] = {}
    for column in REQUIRED:
        if not cell[column]:
            found[column] = "is empty; write a value (use `unknown` where a column allows it)"
    for column, allowed in (("dimension", DIMENSIONS), ("better", BETTER), ("source_kind", SOURCE_KINDS),
                            ("run_by_independent", RUN_BY), ("method_disclosed", METHOD), ("benchmark_status", STATUS)):
        if cell[column] and cell[column] not in allowed:
            found[column] = f"is {cell[column]!r}, not one of {', '.join(allowed)}"
    found.update(shape_problems(cell))
    return found


def shape_problems(cell: Dict[str, str]) -> Dict[str, str]:
    """``{column: what is wrong}`` for the value, count, link and dates of one row."""
    found: Dict[str, str] = {}
    if cell["value"] and finite_number(cell["value"]) is None:
        found["value"] = f"is {cell['value']!r}, not a finite number"
    if cell["n"] and not (cell["n"].isdigit() and int(cell["n"]) > 0):
        found["n"] = f"is {cell['n']!r}, not a positive whole number (leave it empty when unstated)"
    if cell["source_url"] and not re.match(r"^https?://\S+$", cell["source_url"]):
        found["source_url"] = "is not an http(s) link"
    found.update(date_problems(cell))
    return found


def date_problems(cell: Dict[str, str]) -> Dict[str, str]:
    """``{column: what is wrong}`` for the two date columns."""
    return {column: f"is {cell[column]!r}, not a date like 2026-10-31"
            for column in ("date_published", "date_checked") if cell[column] and as_date(cell[column]) is None}


def as_date(text: str) -> Optional[datetime.date]:
    """An ISO date, or None when the text is not one (or is empty)."""
    try:
        return datetime.date.fromisoformat(text) if text else None
    except ValueError:
        return None


def repeat_problems(cell: Dict[str, str], seen: Dict[str, int], position: int, found: Dict[str, str]) -> Dict[str, str]:
    """``found`` plus a problem when the row repeats an earlier ``evidence_id``; records the line the id first appears on."""
    if cell["evidence_id"]:
        if cell["evidence_id"] in seen:
            found.setdefault("evidence_id", f"repeats line {seen[cell['evidence_id']]}")
        seen.setdefault(cell["evidence_id"], position)
    return found


def parse_rows(rows: Iterable[Mapping[str, str]], header: Optional[Sequence[str]] = None) -> Tuple[List[Evidence], List[str]]:
    """``(evidence, problems)`` from row dicts. Every problem names its line (header is line 1) and the column."""
    problems: List[str] = header_problems(header) if header is not None else []
    if problems:
        return [], problems
    out: List[Evidence] = []
    seen: Dict[str, int] = {}
    for position, row in enumerate(rows, 2):
        cell = {c: (row.get(c) or "").strip() for c in COLUMNS}
        found = repeat_problems(cell, seen, position, cell_problems(cell))
        problems.extend(f"line {position} ({cell['evidence_id'] or 'no id'}): {column} {message}" for column, message in found.items())
        if not found:
            out.append(evidence_of(cell, position))
    return out, problems + direction_problems(out)


def evidence_of(cell: Dict[str, str], position: int) -> Evidence:
    """The ``Evidence`` of one valid row's cells."""
    return Evidence(
        cell["evidence_id"], cell["candidate"], cell["dimension"], cell["measure"], finite_number(cell["value"]) if cell["value"] else None,
        cell["unit"], cell["better"], cell["comparator"], cell["source_url"], cell["source_kind"], cell["run_by_independent"],
        cell["method_disclosed"], int(cell["n"]) if cell["n"] else None, cell["benchmark_status"], as_date(cell["date_published"]),
        as_date(cell["date_checked"]), tuple(c.strip() for c in cell["confounds"].split(LIST_SEPARATOR) if c.strip()), cell["note"], position)


def direction_problems(out: List[Evidence]) -> List[str]:
    """A problem for each row that says the opposite direction of better from the first row for the same measure."""
    problems: List[str] = []
    direction: Dict[Tuple[str, str], Evidence] = {}
    for e in out:
        first = direction.setdefault((e.dimension, e.measure.lower()), e)
        if first.better != e.better:
            problems.append(f"line {e.line} ({e.evidence_id}): better is {e.better} but {first.evidence_id} (line {first.line}) "
                            f"says {first.better} for the same measure {e.measure!r}")
    return problems


def parse_text(text: str) -> List[Evidence]:
    """The evidence in CSV text, or ``EvidenceError`` naming every problem."""
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    rows = list(reader)
    extra = [r for r in rows if None in r]
    problems: List[str] = []
    if extra:
        problems.append("a row has more cells than the header; quote any cell that contains a comma")
    found, more = parse_rows(rows, header)
    if problems or more:
        raise EvidenceError(problems + more)
    return found


def load(path: Path) -> List[Evidence]:
    return parse_text(Path(path).read_text(encoding="utf-8"))


def header_line() -> str:
    return ",".join(COLUMNS)


def evidence_path(config) -> Path:
    """Where this repository keeps its evidence: ``[evidence] file`` in the configuration, else ``evidence.csv`` in the structure folder."""
    table = getattr(config, "evidence", {}) or {}
    return config.root / table.get("file", f"{config.structure_dir}/evidence.csv")


def load_for(config) -> List[Evidence]:
    """The repository's evidence, or an empty list when it keeps none. A malformed file raises ``EvidenceError``."""
    path = evidence_path(config)
    return load(path) if path.is_file() else []


def aliases(config) -> Dict[str, str]:
    """``{candidate: implementation}`` from ``[evidence.aliases]`` in the configuration (both normalised)."""
    table = (getattr(config, "evidence", {}) or {}).get("aliases", {})
    return {norm(k): norm(v) for k, v in table.items()}


def implementation_candidates(config, registry, solution_id: str) -> Dict[str, str]:
    """``{implementation name: candidate key}`` for a solution. The smallest honest mapping: an implementation is matched by the
    part of its id after the colon, or its ``name``, equal to the evidence's candidate (case, ``_``, ``-`` and spaces ignored);
    ``[evidence.aliases]`` maps a candidate that is spelled differently. Nothing is guessed beyond that."""
    alias = aliases(config)
    out: Dict[str, str] = {}
    for row in registry.implementations:
        if row.get("solution_id") != solution_id:
            continue
        impl_id = row.get("implementation_id", "")
        short = impl_id.split(":", 1)[-1]
        keys = {norm(short), norm(row.get("name", ""))} | {c for c, target in alias.items() if target in (norm(short), norm(impl_id))}
        out[short] = ",".join(sorted(keys))
    return out
