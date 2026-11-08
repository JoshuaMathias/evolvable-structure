"""The records a repository keeps beside its intent records that speak about a solution: findings, candidates, notes. A repository
declares each file once in ``esoi.toml``, and every row is attached to the solution it is about, by a column that names the solution or
by a candidate that matches one of the solution's implementations. Nothing is guessed beyond those two.

    [[consider.records]]
    file = "registry/findings.csv"   # relative to the repository root
    kind = "finding"                 # a free label; "finding" and "candidate" rows are checked by rule S60
    id = "finding_id"                # default: the first column
    solution = "solution_id"         # default: solution_id, solution_ids or solution when the file has one
    candidate = "candidate"          # default: candidate when the file has one
    results = "results_ref"          # optional: a column that cites recorded results (else the row's text must name the results log)

A file named on the command line (``--with FILE``) is read the same way with the defaults, its kind taken from its name.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi.structure.intent_registry.tables import SEP
from esoi.understanding.spec_search.spec_index import tokens

SOLUTION_COLUMNS = ("solution_id", "solution_ids", "solution")
CANDIDATE_COLUMNS = ("candidate",)
CHECKED_KINDS = ("finding", "candidate")


@dataclass
class RecordFile:
    """One declared file of extra records and the columns that tie its rows to solutions."""
    path: Path
    kind: str
    id_column: str = ""
    solution_column: str = ""
    candidate_column: str = ""
    results_column: str = ""
    rows: List[Dict[str, str]] = field(default_factory=list)

    @property
    def checked(self) -> bool:
        return self.kind in CHECKED_KINDS


def kind_from_name(path: Path) -> str:
    """``finding`` or ``candidate`` when the file's name says so, else ``record``."""
    name = path.stem.lower()
    return next((kind for kind in CHECKED_KINDS if kind in name), "record")


def read_file(root: Path, spec: Mapping[str, Any]) -> Optional[RecordFile]:
    """The file a ``[[consider.records]]`` entry names, with its columns resolved; ``None`` when the file is missing."""
    path = Path(spec.get("file", ""))
    path = path if path.is_absolute() else Path(root) / path
    if not path.is_file():
        return None
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(r) for r in reader]
        header = list(reader.fieldnames or [])
    return RecordFile(
        path=path, kind=str(spec.get("kind") or kind_from_name(path)),
        id_column=str(spec.get("id") or (header[0] if header else "")),
        solution_column=str(spec.get("solution") or next((c for c in SOLUTION_COLUMNS if c in header), "")),
        candidate_column=str(spec.get("candidate") or next((c for c in CANDIDATE_COLUMNS if c in header), "")),
        results_column=str(spec.get("results") or ""), rows=rows)


def declared(config, extra: Sequence[str] = ()) -> List[RecordFile]:
    """Every file ``[[consider.records]]`` declares, and the files named on the command line, read."""
    table = getattr(config, "consider", {}) or {}
    specs = list(table.get("records", [])) + [{"file": name} for name in extra]
    return [found for found in (read_file(config.root, spec) for spec in specs) if found is not None]


def words(text: str) -> set:
    return set(tokens(text))


def implementation_words(row: Mapping[str, str]) -> set:
    """The words of an implementation's short id and name."""
    short = (row.get("implementation_id") or "").split(":", 1)[-1].replace("_", " ").replace("-", " ")
    return words(short) | words(row.get("name", ""))


def candidate_words(candidate: str) -> set:
    """The words a candidate is matched by, or none when a word of its name is too short or too common to match on ("any-llm"):
    such a candidate is matched by an alias only."""
    wanted = words(candidate)
    return wanted if wanted and len(wanted) == len(set(re.findall(r"[a-z0-9]+", candidate.lower()))) else set()


def candidate_implementations(candidate: str, implementations: Sequence[Mapping[str, str]],
                              aliases: Mapping[str, str]) -> List[Mapping[str, str]]:
    """The implementation records a candidate names: by an alias in ``[evidence.aliases]``, or because every word of the candidate is a
    word of the implementation's short id or name ("Graphify" names ``graphify_files``, "Graphify file groups")."""
    from esoi.optimization.when_metrics_are_run.public_evidence.evidence_records import norm
    wanted = candidate_words(candidate)
    aliased = aliases.get(norm(candidate), "")
    found = []
    for row in implementations:
        impl_id = row.get("implementation_id") or ""
        if (aliased and aliased in (norm(impl_id.split(":", 1)[-1]), norm(impl_id))) or (wanted and wanted <= implementation_words(row)):
            found.append(row)
    return found


def row_solutions(record: RecordFile, row: Mapping[str, str], implementations: Sequence[Mapping[str, str]],
                  aliases: Mapping[str, str], known: set) -> Dict[str, str]:
    """``{solution id: how the row reaches it}`` for one row: the ids its solution column names, else the solutions of the
    implementations its candidate names."""
    if record.solution_column:
        named = [part.strip() for part in (row.get(record.solution_column) or "").split(SEP) if part.strip()]
        if named:
            return {sid: f"names it in {record.solution_column}" for sid in named if sid in known} or {sid: "names it" for sid in named}
    if record.candidate_column and (candidate := (row.get(record.candidate_column) or "").strip()):
        out: Dict[str, str] = {}
        for impl in candidate_implementations(candidate, implementations, aliases):
            out.setdefault(impl.get("solution_id", ""), f"candidate {candidate} is implementation {impl.get('implementation_id', '')}")
        return out
    return {}


def row_id(record: RecordFile, row: Mapping[str, str], position: int) -> str:
    return (row.get(record.id_column) or "").strip() or f"row {position}"


def row_text(row: Mapping[str, str], skip: Sequence[str] = ()) -> str:
    """The row's non-empty cells, ``column: value``, on one line."""
    return "; ".join(f"{k}: {' '.join(v.split())}" for k, v in row.items() if k and k not in skip and (v or "").strip())


def cites_results(record: RecordFile, row: Mapping[str, str], results_name: str) -> bool:
    """Whether a row cites the recorded results: its results column is filled, or its text names the results log."""
    if record.results_column and (row.get(record.results_column) or "").strip():
        return True
    return results_name.lower() in " ".join(v or "" for v in row.values()).lower()


def about(config, registry, solution_id: str, files: Sequence[RecordFile]) -> List[Dict[str, str]]:
    """The rows of the declared files that are about one solution, each as ``{file, kind, id, via, text}``."""
    from esoi.optimization.when_metrics_are_run.public_evidence.evidence_records import aliases as evidence_aliases
    alias = evidence_aliases(config)
    known = {r.get("solution_id", "") for r in registry.every_solution()}
    out = []
    for record in files:
        for position, row in enumerate(record.rows, 2):
            reached = row_solutions(record, row, registry.implementations, alias, known)
            if solution_id in reached:
                out.append({"file": str(record.path.relative_to(config.root)) if record.path.is_relative_to(config.root) else str(record.path),
                            "kind": record.kind, "id": row_id(record, row, position), "via": reached[solution_id],
                            "text": row_text(row, (record.id_column,))})
    return out
