"""Read and write the per-case log, the outcome of each case of each recorded run."""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Dict, List

from esoi.optimization.leaderboard import results_log
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.structure.intent_registry.config import Config


PER_CASE_COLUMNS = ["component", "impl", "cases_sha", "circumstances_sha", "sample", "case_id", "heldout", "ok", "calls",
                    "tokens_in", "tokens_out", "seconds", "circumstances", "score"]


PER_CASE_KEY = results_log.PER_CASE_KEY


def read_per_case(config: Config, every: bool = False) -> List[Dict[str, str]]:
    """The per-case log, the newest row of each (arm, cases, sample, case) or, with ``every``, every row in file order
    (``results_log.per_case_rows``, which the leaderboard's paired test also reads)."""
    return results_log.per_case_rows(config, every)


def upgrade_per_case_header(path: Path) -> None:
    """Rewrite a per-case log written by an older version (a header without a column added since, such as ``score``) under the
    current header, in one move, so a new row never lands under a header that lacks its column. Existing values are kept and a
    column the old file lacked is left empty. A file already on the current header is not touched."""
    if not path.is_file() or path.stat().st_size == 0:
        return
    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh), [])
        if header == PER_CASE_COLUMNS:
            return
        fh.seek(0)
        rows = [r for r in csv.DictReader(fh) if r.get("component") != "component"]
    unknown = [name for name in header if name not in PER_CASE_COLUMNS]
    if unknown:
        raise RunError(f"{path} has column(s) this version does not know ({', '.join(unknown)}); remedy: update esoi")
    temporary = path.with_suffix(path.suffix + ".upgrade")
    with open(temporary, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, PER_CASE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({name: row.get(name, "") or "" for name in PER_CASE_COLUMNS} for row in rows)
    os.replace(temporary, path)


def write_per_case(config: Config, new: List[Dict[str, str]]) -> None:
    """Add rows to the per-case log without losing another recorder's: one append of the whole batch (``O_APPEND``), then,
    when the arm had rows of its own from older cases or an earlier run of the same sample, a compaction written to a
    temporary file and moved over the log in one step. A row lost to a compaction that overlapped an append is re-derived:
    the arm is stale (``circumstances_stale``) until its rows are back."""
    path = config.root / config.per_case
    path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_per_case_header(path)
    out = io.StringIO()
    writer = csv.DictWriter(out, PER_CASE_COLUMNS, lineterminator="\n")
    if not path.is_file() or path.stat().st_size == 0:
        writer.writeheader()
    writer.writerows(new)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, out.getvalue().encode("utf-8"))
    finally:
        os.close(fd)
    arm = {(r["component"], r["impl"]) for r in new}
    keep = [r for r in read_per_case(config) if (r["component"], r["impl"]) not in arm or r["cases_sha"] == new[0]["cases_sha"]]
    if len(keep) != len(read_per_case(config, every=True)):   # superseded rows, rows of older cases or a repeated header
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        with open(temporary, "w", newline="", encoding="utf-8") as fh:
            compacted = csv.DictWriter(fh, PER_CASE_COLUMNS, lineterminator="\n")
            compacted.writeheader()
            compacted.writerows(keep)
        os.replace(temporary, path)
