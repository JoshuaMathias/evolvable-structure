"""The log of every run, finished or not: what an iteration on an implementation reads to know what to run next.

The skill says "all runs are recorded and saved even if stopped midrun" and that, while improving an implementation, the
failing cases are rerun by themselves before the whole set is. The results log (``results.csv``) holds only the runs someone
chose to record, one summary row each, and it is what the leaderboard and the cascade read. This log (``runs.csv``, beside it)
holds every run, one row per case written the moment the case finishes, so a run stopped by Ctrl-C, a model-call budget or a
crash keeps what it scored. The leaderboard and the cascade never read it; a run counts for them only when ``--record`` also
put its summary in the results log (the ``recorded`` column says which runs did).

Rows (``kind``): ``start`` when a run begins, ``case`` as each case finishes (with the scorer's row in ``row`` as JSON), and
``end`` when the run stops, with ``status`` ``done`` or ``stopped: <why>``. A run killed without a chance to write ``end`` shows as
a ``start`` and cases with no ``end``, which also means stopped.

Three readers use it, all with no model call:

  * ``failed_cases``: the cases whose latest outcome for the arm (on these cases) is a failure, for ``esoi run --failed``;
  * ``unsolved_failures``: those failures that stand in the way of a whole run: the case's latest outcome failed and was not part of
    a recorded whole run (a baseline that fails by design and was recorded by a run that finished is a finished measurement, not an iteration in progress);
  * ``reusable``: the latest outcome of each case for the same arm, cases and code version, so a later cascade stage does not
    rerun a case the earlier stage already ran (a changed implementation has another version, so nothing is reused then).
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

COLUMNS = ["run_id", "kind", "date", "component", "impl", "cases_sha", "git_sha", "sample", "recorded", "case_id", "ok",
           "calls", "tokens_in", "tokens_out", "cost_usd", "seconds", "status", "row"]
Entry = Dict[str, str]


def new_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + f"-{os.getpid()}"


def read(path: Path) -> List[Entry]:
    """Every entry in file order; a repeated header line or a half-written line is not an entry."""
    if not Path(path).is_file():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("run_id") and r.get("run_id") != "run_id"]


def append(path: Path, entry: Dict[str, Any]) -> None:
    """Add one entry with a single ``O_APPEND`` write, so two runs logging together do not interleave inside a line."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.is_file() or path.stat().st_size == 0
    out = io.StringIO()
    writer = csv.DictWriter(out, COLUMNS, lineterminator="\n")
    if fresh:
        writer.writeheader()
    writer.writerow({name: "" if entry.get(name) is None else entry.get(name) for name in COLUMNS})
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, out.getvalue().encode("utf-8"))
    finally:
        os.close(fd)


class RunLog:
    """One run's rows. ``key`` holds what is the same on every row: component, impl, cases_sha, git_sha, sample, recorded."""

    def __init__(self, path: Path, key: Dict[str, Any], run_id: Optional[str] = None):
        self.path, self.key, self.run_id = Path(path), dict(key), run_id or new_run_id()
        self.ended = False

    def put(self, kind: str, **values: Any) -> None:
        append(self.path, dict(self.key, run_id=self.run_id, kind=kind, date=datetime.date.today().isoformat(), **values))

    def begin(self) -> None:
        self.put("start")

    def case(self, row: Dict[str, Any], cost: float = 0.0, reused: bool = False) -> None:
        self.put("case", case_id=row["id"], ok="1" if row.get("ok") else "0", calls=row.get("calls", 0),
                 tokens_in=row.get("tokens_in", 0), tokens_out=row.get("tokens_out", 0), cost_usd=round(cost, 6),
                 seconds=row.get("seconds", 0), row=json.dumps(row, default=str), status="reused" if reused else "")

    def end(self, status: str) -> None:
        if not self.ended:
            self.ended = True
            self.put("end", status=status)


def latest_by_case(entries: List[Entry], component: str, impl: str, cases_sha: str) -> Dict[str, Entry]:
    """{case id: its newest ``case`` entry} for the arm on these cases. A reused entry only repeats an earlier outcome and is skipped."""
    out: Dict[str, Entry] = {}
    for e in entries:
        if (e["kind"] == "case" and e["component"] == component and e["impl"] == impl and e["cases_sha"] == cases_sha
                and e.get("status") != "reused"):
            out[e["case_id"]] = e
    return out


def failed_cases(path: Path, component: str, impl: str, cases_sha: str) -> List[str]:
    return [cid for cid, e in latest_by_case(read(path), component, impl, cases_sha).items() if e["ok"] != "1"]


def unsolved_failures(path: Path, component: str, impl: str, cases_sha: str) -> List[str]:
    """The failed cases that were not part of a recorded whole run (see the module docstring)."""
    entries = read(path)
    done = {e["run_id"] for e in entries if e["kind"] == "end" and e["status"] == "done"}
    return [cid for cid, e in latest_by_case(entries, component, impl, cases_sha).items()
            if e["ok"] != "1" and not (e["recorded"] == "yes" and not e["sample"] and e["run_id"] in done)]


def reusable(path: Path, component: str, impl: str, cases_sha: str, git_sha: str) -> Dict[str, Dict[str, Any]]:
    """{case id: scorer row, with ``cost`` added} of cases already run for this arm, these cases and exactly this code. Nothing is
    reused for code of no known version (``git_sha`` blank) or with uncommitted changes (``-dirty``): it may differ from the run."""
    if not git_sha or git_sha.endswith("-dirty"):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for cid, e in latest_by_case(read(path), component, impl, cases_sha).items():
        if e["git_sha"] != git_sha:
            continue
        try:
            row = json.loads(e["row"])
        except ValueError:
            continue
        row["cost"] = float(e.get("cost_usd") or 0)
        out[cid] = row
    return out
