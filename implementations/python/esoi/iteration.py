"""The metric record of ONE piece of work: before the work, after it, and what every consumer is handed.

ESOI's rule for work is "what the relevant metric result was before and after your change". ``MetricIteration`` is how a program
meets it without trusting anyone's closing words. For each piece of work (a goal, a task, one run) the program creates one and
calls it at two points, in code, with no model:

  ``begin``   before the first attempt: the slice of the specification the work serves (``esoi.spec_slice``) becomes a short
              NEXT PRIORITY block for the brief, and when the iteration ``measures`` it reads the metric (``esoi.metric_meter``)
              and writes the ``measured`` ``before`` row. That reading is bounded and announced: it never holds the work back
              for longer than its budget, and with no slice (no records, no folder) nothing is read and nothing waits.
  ``finish``  after the last attempt: it reads the metric again (``after``, by the meters that read the tree as it is now,
              never a recorded row), reconciles the ledger's rows (``esoi.metric_results.reconcile``) and returns them.

Between the two, anything may add rows to the same ledger under the same run id (a worker that records its own values, for
instance); ``rows`` reads them all. What counts as "changed something", whether to ask a worker to record a missing result,
and where the returned rows are put are the caller's: this class keeps the record and nothing else.

The three ways a program can run it are three settings, not three classes: no ``source`` (the standing instructions are the
whole method), a ``source`` without ``measures`` (the brief gets the slice), and a ``source`` with ``measures`` (the program
also reads the metric before and after and writes the readings itself). It never raises into the work it records.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, List, Mapping, Optional, Sequence, Tuple

from .metric_meter import AFTER, BEFORE, DEFAULT_BUDGET_SECONDS, MetricMeter, read_value
from .metric_results import SOURCE_MEASURED, MetricLedger, MetricResult, reconcile
from .spec_slice import SliceSource, SpecSlice, next_priority_block

log = logging.getLogger("esoi.iteration")

# The moment a reading is taken, as the ledger's reason names it.
READING_PHASES = {BEFORE: "before the change", AFTER: "after the change"}
# What the status line says while a reading runs, and what it says when none could be taken in time. Plain words for a
# person: never the metric's name (a long one is cut mid-word on a narrow screen).
READING_STATUS: Mapping[str, Tuple[str, str]] = {
    BEFORE: ("Checking the starting value before any change.", "No starting value in time. Going on without it."),
    AFTER: ("Checking the result after the change.", "No result check in time. Going on without it.")}


@dataclass(frozen=True)
class Finished:
    """The end of an iteration: the reconciled rows, and whether the work did anything for them to describe."""
    results: List[MetricResult]
    did_work: bool


class MetricIteration:
    """The metric record of one piece of work. Create one per piece of work."""

    def __init__(self, ledger: MetricLedger, run_id: str, *, source: Optional[SliceSource] = None,
                 meters: Sequence[MetricMeter] = (), measures: bool = True, task_id: str = "", request: str = "",
                 working_dir: Optional[str] = None, status: Optional[Callable[[str], None]] = None,
                 budget_seconds: float = DEFAULT_BUDGET_SECONDS, closing: str = "",
                 statuses: Mapping[str, Tuple[str, str]] = READING_STATUS):
        self.ledger, self.run_id = ledger, run_id
        self.source = source
        self.meters = list(meters)
        self.measures = bool(measures and self.meters)
        self.task_id, self.request, self.working_dir = task_id, request, working_dir
        self.status = status
        self.budget_seconds = budget_seconds
        self.closing = closing   # what the brief asks of the worker after the NEXT PRIORITY block (its own words)
        self.statuses = statuses
        self.started = time.time()
        self.spec_slice: Optional[SpecSlice] = None
        self.gaps: List[str] = []   # readings that could not be taken, said on the rows written after them

    def say(self, text: str) -> None:
        if self.status is not None:
            self.status(text)

    # -- before the first attempt ------------------------------------------------------------------

    def begin(self) -> str:
        """The block for the brief ("" for none), after reading the metric when the iteration measures. Never raises."""
        try:
            if self.source is None:
                return ""
            self.spec_slice = self.source.slice_for(self.request, self.working_dir)
            found = self.spec_slice
            if found is None:
                return ""
            if self.measures and found.metric_id:
                self.read(BEFORE)
            return "\n\n" + next_priority_block(found, self.closing)
        except Exception:  # noqa: BLE001  the record must never stop the work it records
            log.debug("iteration not begun", exc_info=True)
            return ""

    def read(self, when: str) -> None:
        """Take one reading of the slice's metric, ``BEFORE`` or ``AFTER`` the change, and keep it as a measured row.

        The reading is bounded, and announced only if a meter that takes time is about to run. One that gives nothing writes no
        row (a row without a number would count as a record); when it ran out of time that is said on the status line and,
        for a reading before the change, on the row written after the work."""
        found = self.spec_slice
        if found is None:
            return
        checking, missed = self.statuses[when]
        reading = read_value(self.meters, found, self.working_dir, when=when, budget_seconds=self.budget_seconds,
                             announce=lambda: self.say(checking))
        if reading.value is not None:
            self.keep(reading.meter, **{when: reading.value})
        elif reading.note:
            self.gaps.append(f"no reading {READING_PHASES[when]}: {reading.note}")
            self.say(missed)

    def keep(self, meter: str, before: Optional[float] = None, after: Optional[float] = None) -> None:
        found = self.spec_slice
        if found is None:
            return
        reason = f"measured by {meter}" + (f"; {'; '.join(self.gaps)}" if self.gaps and after is not None else "")
        self.ledger.record(MetricResult(
            source=SOURCE_MEASURED, run_id=self.run_id, task_id=self.task_id, solution_id=found.solution_id,
            metric_id=found.metric_id, name=found.metric_name, milestone=found.milestone, before=before, after=after,
            reason=reason))

    # -- around the attempts -----------------------------------------------------------------------

    def rows(self) -> List[MetricResult]:
        """Every row kept for this piece of work: under its run id, and what a call with only the task id kept since it began."""
        rows = list(self.ledger.for_run(self.run_id))
        if self.task_id and self.task_id != self.run_id:
            rows += [r for r in self.ledger.for_run(self.task_id) if r.ts >= self.started]
        return rows

    # -- after the last attempt --------------------------------------------------------------------

    def finish(self, did_work: bool = True) -> Finished:
        """Read the metric once more when the work was done, and reconcile the rows. Never raises.

        ``did_work`` is the caller's: False for work that was cancelled, never started or handed on, which has no after to
        read."""
        try:
            found = self.spec_slice
            if did_work and found is not None and self.measures and found.metric_id:
                self.read(AFTER)
            return Finished(reconcile(self.rows()), did_work)
        except Exception:  # noqa: BLE001
            log.debug("iteration not finished", exc_info=True)
            return Finished([], did_work)
