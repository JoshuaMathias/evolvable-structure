"""The metric result of a piece of work, kept by the program: what the relevant metric was before and after the change.

ESOI asks every piece of work to report "what the relevant metric result was before and after your change". Left to the
worker's closing words that is only a claim, so the program keeps the record itself: the numbers are written to a ledger by
code, the flow reads the ledger (never the wording of anything a model wrote) and every consumer gets the same structured
entries.

A ``MetricResult`` is one row. Its ``source`` says who vouches for the numbers, and is exactly one of:

  ``measured``        the program's own meter read the value (``esoi.metric_meter``), in code, before and after the work
  ``recorded``        the worker called for the values to be recorded; nobody has checked them
  ``not_applicable``  the worker declared that no metric applies, and gave a reason (shown only when no row holds a number)

A measured and a recorded row for the same metric are both kept; when their numbers differ (``differs``: the measured one
rounded to the decimals the recorded one is written with, else exactly) both carry ``disagrees``. A number is a finite int or
float and nothing else: a string a model produced is rejected at the door, never coerced.

The consumer's view is ``to_dict()``, and a run's list of them is the ``metrics`` payload:

    {"solution_id", "metric_id", "name", "milestone", "before", "after", "delta", "source", "reason", "disagrees"}

An empty list means nothing to show. ``to_row()`` adds the run, task and time, for the ledger file only.

The ledger is a JSON-lines file per run in a directory the writers share (``FileMetricLedger``); the directory is an argument.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

try:  # POSIX only; elsewhere the single O_APPEND write is the guarantee
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

log = logging.getLogger("esoi.metric_results")

SOURCE_MEASURED = "measured"
SOURCE_RECORDED = "recorded"
SOURCE_NOT_APPLICABLE = "not_applicable"
SOURCES = (SOURCE_MEASURED, SOURCE_RECORDED, SOURCE_NOT_APPLICABLE)

# The most metric entries a payload carries by default (``reconcile(rows, limit=...)`` changes it).
MAX_METRICS = 12
# A line in the ledger stays far below the size at which an append could be split: free text is cut to these.
ID_CHARS, NAME_CHARS, TEXT_CHARS = 120, 160, 300
# A ledger file untouched for this long belongs to a finished run and is removed.
LEDGER_MAX_AGE_SECONDS = 2 * 24 * 3600
# One metric on the result line, so a long list stays one line.
LINE_ENTRIES = 3
NOT_RECORDED_LINE = "No metric was recorded for this change."


def number_or_none(value: Any, field_name: str) -> Optional[float]:
    """``value`` as a float, ``None`` for ``None``; ValueError for anything that is not a finite number.

    A bool is not a number here, and neither is a string (``"0.8"``, ``"80%"``, ``"nan"``): a value a model typed is not
    parsed into a metric."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number, not {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be a finite number")
    return number


def clip(text: Any, limit: int) -> str:
    return " ".join(str(text or "").split())[:limit]


@dataclass(frozen=True)
class MetricResult:
    """One row of a run's metric record. Immutable; ``reconcile`` builds new ones."""
    source: str
    run_id: str = ""
    task_id: str = ""
    solution_id: str = ""
    metric_id: str = ""
    name: str = ""
    milestone: str = ""
    before: Optional[float] = None
    after: Optional[float] = None
    reason: str = ""
    ts: float = 0.0
    disagrees: bool = False

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"source must be one of {', '.join(SOURCES)}, not {self.source!r}")
        for field_name, limit in (("run_id", ID_CHARS), ("task_id", ID_CHARS), ("solution_id", ID_CHARS),
                                  ("metric_id", ID_CHARS), ("name", NAME_CHARS), ("milestone", TEXT_CHARS),
                                  ("reason", TEXT_CHARS)):
            object.__setattr__(self, field_name, clip(getattr(self, field_name), limit))
        before, after = number_or_none(self.before, "before"), number_or_none(self.after, "after")
        object.__setattr__(self, "before", before)
        object.__setattr__(self, "after", after)
        if not self.ts:
            object.__setattr__(self, "ts", time.time())
        if self.source == SOURCE_NOT_APPLICABLE:
            if not self.reason:
                raise ValueError("a result marked not applicable needs a reason")
            if before is not None or after is not None:
                raise ValueError("a result marked not applicable cannot carry values")
        elif before is None and after is None:
            raise ValueError("a result needs a before value, an after value, or both")

    @property
    def delta(self) -> Optional[float]:
        return round(self.after - self.before, 10) if self.before is not None and self.after is not None else None

    def to_dict(self) -> Dict[str, Any]:
        """The consumer's entry: the ten keys of the ``metrics`` payload."""
        return {"solution_id": self.solution_id, "metric_id": self.metric_id, "name": self.name,
                "milestone": self.milestone, "before": self.before, "after": self.after, "delta": self.delta,
                "source": self.source, "reason": self.reason, "disagrees": self.disagrees}

    def to_row(self) -> Dict[str, Any]:
        """What the ledger file stores: the entry plus the run, the task and the time."""
        return {**self.to_dict(), "run_id": self.run_id, "task_id": self.task_id, "ts": self.ts}

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "MetricResult":
        """A ledger row back into a result; ValueError for a row that is not one."""
        try:
            return cls(source=str(row.get("source") or ""), run_id=row.get("run_id") or "",
                       task_id=row.get("task_id") or "", solution_id=row.get("solution_id") or "",
                       metric_id=row.get("metric_id") or "", name=row.get("name") or "",
                       milestone=row.get("milestone") or "", before=row.get("before"), after=row.get("after"),
                       reason=row.get("reason") or "", ts=float(row.get("ts") or 0.0),
                       disagrees=bool(row.get("disagrees")))
        except (TypeError, AttributeError) as e:
            raise ValueError(f"not a metric row: {e}") from e


class MetricLedger(Protocol):
    """Where a run's metric rows are kept, whichever process writes them."""

    def record(self, result: MetricResult) -> bool:
        """Keep one row under its ``run_id``; True when it was kept. Never raises."""
        ...

    def for_run(self, run_id: str) -> List[MetricResult]:
        """Every row kept for the run, oldest first (``[]`` for an unknown run or a failed read)."""
        ...


class RunFiles:
    """An append-only JSON-lines file per key (a run id) in one directory.

    An append is one ``os.write`` of the whole line on an ``O_APPEND`` descriptor, under an exclusive ``flock`` where the
    platform has one, so two writers (threads or processes) never produce a torn or interleaved line. The file is created
    with mode 0666 minus the umask, the permissions an ordinary ``open(path, "a")`` gives it. Appends never raise: a ledger
    that cannot be written must not break the work it records."""

    def __init__(self, directory: str, max_age_seconds: float = LEDGER_MAX_AGE_SECONDS):
        self.directory = directory
        self.max_age_seconds = max_age_seconds

    def path_for(self, key: str) -> str:
        return os.path.join(self.directory, re.sub(r"[^A-Za-z0-9_.-]", "_", str(key)) + ".jsonl")

    def append(self, key: str, record: Mapping[str, Any]) -> bool:
        """Append one record as one line; True when it was written."""
        if not key:
            return False
        try:
            data = (json.dumps(dict(record), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            os.makedirs(self.directory, exist_ok=True)
            fd = os.open(self.path_for(key), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o666)
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                os.write(fd, data)
            finally:
                os.close(fd)   # closing releases the lock
            return True
        except (OSError, TypeError, ValueError) as error:
            log.debug("ledger line not written for %s: %s", key, error)
            return False

    def read(self, key: str) -> List[Dict[str, Any]]:
        """Every well-formed record of the key, oldest first; a malformed line is skipped."""
        if not key:
            return []
        rows: List[Dict[str, Any]] = []
        try:
            with open(self.path_for(key), "r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(row, dict):
                        rows.append(row)
        except OSError:
            return []
        return rows

    def prune(self) -> None:
        """Remove the files untouched for ``max_age_seconds``."""
        cutoff = time.time() - self.max_age_seconds
        try:
            for name in os.listdir(self.directory):
                path = os.path.join(self.directory, name)
                if name.endswith(".jsonl") and os.path.getmtime(path) < cutoff:
                    os.remove(path)
        except OSError:
            pass


class FileMetricLedger:
    """The default ledger: a JSON-lines file per run in ``directory``, which every writer of the run can reach."""

    def __init__(self, directory: str):
        self.directory = directory
        self.files = RunFiles(directory)

    def record(self, result: MetricResult) -> bool:
        if result.run_id and self.files.append(result.run_id, result.to_row()):
            self.files.prune()
            return True
        return False

    def for_run(self, run_id: str) -> List[MetricResult]:
        rows: List[MetricResult] = []
        for raw in self.files.read(run_id):
            try:
                rows.append(MetricResult.from_row(raw))
            except ValueError:
                continue
        return rows


def same_metric(a: MetricResult, b: MetricResult) -> bool:
    return bool(a.metric_id) and a.metric_id == b.metric_id and (not a.solution_id or not b.solution_id
                                                                   or a.solution_id == b.solution_id)


def decimals_written(value: float) -> int:
    """How many decimals ``value`` is written with: those of its shortest exact form (``repr``), so ``0.4`` has one,
    ``0.38`` two and ``14.0`` one."""
    exponent = Decimal(repr(float(value))).as_tuple().exponent
    return max(-int(exponent), 0)


def differs(measured: Optional[float], recorded: Optional[float]) -> bool:
    """True when a measured value and a recorded one are different numbers.

    A worker writes the number it reports with the decimals it chose (``0.4``), and the meter's is more exact
    (``0.38``): they say the same thing. So the two agree when the measured value, rounded half up to the
    decimals the RECORDED value is written with, equals the recorded value. Anything else is a real difference,
    compared exactly: there is no tolerance, and a number written with more decimals than the measured one has
    cannot be rounded into agreement. A missing value never differs."""
    if measured is None or recorded is None or measured == recorded:
        return False
    try:
        places = Decimal(1).scaleb(-decimals_written(recorded))
        rounded = Decimal(repr(float(measured))).quantize(places, rounding=ROUND_HALF_UP)
    except InvalidOperation:   # a number too large to round to a decimal place: compare as written
        return True
    return rounded != Decimal(repr(float(recorded)))


def reconcile(rows: Sequence[MetricResult], limit: int = MAX_METRICS) -> List[MetricResult]:
    """The rows of a run as the payload shows them, oldest information first, capped at ``limit``.

    Rows of one source for one metric are folded into one (a later non-empty value replaces an earlier one, so the measured
    ``before`` written first and the ``after`` written when the work ends become one row, and so do a worker's two calls).
    Rows of different sources are never merged and never overwrite each other: when a measured row and a recorded row for
    the same metric give different numbers for before or for after, both stay and both carry ``disagrees``.

    A reading beats a shrug: once any row holds a number (before or after), the declared not-applicable rows are left out
    of what is shown, so a run never says a metric moved and that there was nothing to measure in one breath. They stay in
    the ledger file; a run whose only rows are not-applicable ones still shows them."""
    folded: Dict[tuple, MetricResult] = {}
    for row in rows:
        key = (row.source, row.reason) if row.source == SOURCE_NOT_APPLICABLE else (row.source, row.solution_id, row.metric_id)
        earlier = folded.get(key)
        folded[key] = row if earlier is None else replace(
            earlier, before=row.before if row.before is not None else earlier.before,
            after=row.after if row.after is not None else earlier.after, name=row.name or earlier.name,
            milestone=row.milestone or earlier.milestone, reason=row.reason or earlier.reason, ts=row.ts,
            task_id=row.task_id or earlier.task_id)
    out = list(folded.values())
    measured = [r for r in out if r.source == SOURCE_MEASURED]
    recorded = [r for r in out if r.source == SOURCE_RECORDED]
    flagged = set()
    for m in measured:
        for r in recorded:
            if same_metric(m, r) and (differs(m.before, r.before) or differs(m.after, r.after)):
                flagged.update((id(m), id(r)))
    order = {SOURCE_MEASURED: 0, SOURCE_RECORDED: 1, SOURCE_NOT_APPLICABLE: 2}
    out = [replace(r, disagrees=True) if id(r) in flagged else r for r in out]
    if any(r.before is not None or r.after is not None for r in out):
        out = [r for r in out if r.source != SOURCE_NOT_APPLICABLE]
    return sorted(out, key=lambda r: order[r.source])[:limit]


def payload_of(results: Sequence[MetricResult]) -> List[Dict[str, Any]]:
    """The ``metrics`` payload entries, ready for an event, a result object or a JSON response."""
    return [r.to_dict() for r in results]


def format_value(value: Optional[float]) -> str:
    return "unknown" if value is None else f"{value:.4g}"


def render_line(results: Sequence[Mapping[str, Any]], missing: bool = False) -> str:
    """ONE plain line for a consumer that shows text only, written from the payload entries and never by a model.

    ``Metric: <name> <before> -> <after> (measured)``; several metrics are joined with semicolons (at most
    ``LINE_ENTRIES``, then a count); a declared not-applicable reads ``Metric: not applicable (<reason>)``; a change that
    ended with nothing recorded reads ``NOT_RECORDED_LINE``. Empty when there is nothing to say."""
    parts: List[str] = []
    for entry in list(results)[:LINE_ENTRIES]:
        if entry.get("source") == SOURCE_NOT_APPLICABLE:
            parts.append(f"not applicable ({entry.get('reason') or 'no reason given'})")
            continue
        label = entry.get("name") or entry.get("metric_id") or "metric"
        flag = ", the recorded value differs" if entry.get("disagrees") else ""
        parts.append(f"{label} {format_value(entry.get('before'))} -> {format_value(entry.get('after'))} "
                     f"({entry.get('source')}{flag})")
    if len(results) > LINE_ENTRIES:
        parts.append(f"and {len(results) - LINE_ENTRIES} more")
    if parts:
        return "Metric: " + "; ".join(parts)
    return NOT_RECORDED_LINE if missing else ""


def without_line(text: str, results: Sequence[Mapping[str, Any]], missing: bool = False) -> str:
    """``text`` with the plain line ``render_line`` wrote for exactly these entries taken out.

    For a consumer that shows the entries itself and must not show them twice. Only a whole line equal to what
    ``render_line`` writes for these arguments is removed (with the blank lines just before it); nothing else in the
    text is touched, and a text that does not hold the line comes back unchanged."""
    line = render_line(results, missing)
    if not line or not text:
        return text
    kept: List[str] = []
    removed = False
    for each in text.split("\n"):
        if each.strip() == line:
            removed = True
            while kept and not kept[-1].strip():
                kept.pop()
            continue
        kept.append(each)
    return "\n".join(kept) if removed else text
