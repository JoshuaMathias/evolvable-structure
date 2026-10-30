"""The metric record of one piece of work: the slice before, the readings before and after, and the rows reconciled.

A scaffolded repository stands in for a real one and fixed meters stand in for the metric, so the moments a reading is taken,
what is announced, and what is written to the ledger are the whole subject. Offline: no model, no network.
"""
import threading
import time

import pytest

from esoi import scaffold
from esoi.iteration import Finished, MetricIteration
from esoi.metric_meter import AFTER, BEFORE
from esoi.metric_results import SOURCE_MEASURED, SOURCE_NOT_APPLICABLE, SOURCE_RECORDED, FileMetricLedger, MetricResult
from esoi.spec_slice import RepoSliceSource

GREETING = "make the greeting function greet a person by name in the standard form"


class FixedMeter:
    """A meter that answers from a list, one value per reading. ``cheap`` says whether a reading takes no time, ``serves``
    which moments (before the work, after it) it can answer."""
    name = "fixed"

    def __init__(self, *values, cheap=False, serves=(BEFORE, AFTER)):
        self.values, self.reads, self.cheap, self.serves = list(values), 0, cheap, serves

    def measure(self, spec_slice, working_dir=None):
        self.reads += 1
        return self.values.pop(0) if self.values else None


class StuckMeter:
    """Never answers until the test lets it go; it takes time, so it is announced."""
    name, cheap = "stuck", False

    def __init__(self):
        self.release, self.reads = threading.Event(), 0

    def measure(self, spec_slice, working_dir=None):
        self.reads += 1
        self.release.wait(30)
        return None


@pytest.fixture
def greet_repo(tmp_path):
    root = tmp_path / "repo"
    scaffold.init(root, "demo_pkg", say=lambda *_: None)
    return root


@pytest.fixture
def ledger(tmp_path):
    return FileMetricLedger(str(tmp_path / "ledger"))


def iteration(ledger, repo, *meters, source=True, **kw):
    kw.setdefault("measures", bool(meters))
    return MetricIteration(ledger, "run-1", source=RepoSliceSource() if source else None, meters=meters, task_id="task-1",
                           request=GREETING, working_dir=str(repo), **kw)


def test_with_no_source_the_standing_instructions_are_the_whole_method(ledger, greet_repo):
    meter = FixedMeter(0.5, 0.6)
    run = iteration(ledger, greet_repo, meter, source=False)
    assert run.begin() == "" and run.finish() == Finished([], True) and meter.reads == 0


def test_a_source_without_measuring_puts_the_next_priority_in_the_brief_and_reads_nothing(ledger, greet_repo):
    meter = FixedMeter(0.5, 0.6)
    run = iteration(ledger, greet_repo, meter, measures=False, closing="Record it.")
    block = run.begin()
    assert block.startswith("\n\nNEXT PRIORITY") and "greeting-pass-rate" in block and block.endswith("Record it.")
    assert meter.reads == 0 and run.finish().results == []


def test_measuring_reads_before_and_after_and_keeps_the_workers_row_beside_it(ledger, greet_repo):
    told = []
    meter = FixedMeter(0.5, 0.75)
    run = iteration(ledger, greet_repo, meter, status=told.append)
    run.begin()
    ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="run-1", metric_id="greeting-pass-rate", before=0.5, after=0.9))
    done = run.finish()
    assert meter.reads == 2 and done.did_work
    by_source = {r.source: r for r in done.results}
    measured = by_source[SOURCE_MEASURED]
    assert (measured.before, measured.after, measured.delta) == (0.5, 0.75, 0.25)
    assert measured.solution_id == "greet-a-person" and measured.milestone.startswith("Share")
    assert measured.name == "Greeting pass rate" and measured.task_id == "task-1"
    assert (by_source[SOURCE_RECORDED].before, by_source[SOURCE_RECORDED].after) == (0.5, 0.9)
    assert measured.disagrees and by_source[SOURCE_RECORDED].disagrees   # both kept, both flagged
    assert told == ["Checking the starting value before any change.", "Checking the result after the change."]


def test_a_cheap_reading_says_nothing(ledger, greet_repo):
    told = []
    run = iteration(ledger, greet_repo, FixedMeter(0.5, cheap=True), status=told.append)
    run.begin()
    assert told == []


def test_a_recorded_row_serves_the_reading_before_and_the_arm_the_reading_after(ledger, greet_repo):
    row, arm = FixedMeter(1.0, serves=(BEFORE,), cheap=True), FixedMeter(0.9977)
    run = iteration(ledger, greet_repo, row, arm)
    run.begin()
    (only,) = run.finish().results
    assert (row.reads, arm.reads) == (1, 1) and (only.before, only.after) == (1.0, 0.9977)


def test_with_no_meter_for_the_reading_after_no_measured_after_is_invented(ledger, greet_repo):
    row = FixedMeter(1.0, serves=(BEFORE,), cheap=True)
    run = iteration(ledger, greet_repo, row)
    run.begin()
    (only,) = run.finish().results
    assert row.reads == 1 and (only.before, only.after) == (1.0, None)


def test_a_declared_not_applicable_is_not_shown_beside_a_reading_but_stays_in_the_ledger(ledger, greet_repo):
    run = iteration(ledger, greet_repo, FixedMeter(0.5, 0.6))
    run.begin()
    ledger.record(MetricResult(source=SOURCE_NOT_APPLICABLE, run_id="run-1", reason="Prose only."))
    assert [r.source for r in run.finish().results] == [SOURCE_MEASURED]
    assert [r.source for r in ledger.for_run("run-1")].count(SOURCE_NOT_APPLICABLE) == 1


def test_a_meter_with_no_reading_writes_no_row(ledger, greet_repo):
    run = iteration(ledger, greet_repo, FixedMeter())
    run.begin()
    assert run.finish().results == [] and ledger.for_run("run-1") == []


def test_an_unclear_request_gets_no_slice_no_block_and_no_reading(ledger, greet_repo):
    meter = FixedMeter(0.1, 0.2)
    run = MetricIteration(ledger, "run-1", source=RepoSliceSource(), meters=[meter], request="write a poem about the sea",
                          working_dir=str(greet_repo))
    assert run.begin() == "" and run.finish().results == [] and meter.reads == 0


def test_a_folder_with_no_records_pays_nothing(ledger, tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    meter = FixedMeter(0.1, 0.2)
    assert iteration(ledger, bare, meter).begin() == "" and meter.reads == 0
    run = MetricIteration(ledger, "run-1", source=RepoSliceSource(), meters=[meter], request=GREETING)   # no folder at all
    assert run.begin() == "" and meter.reads == 0


def test_work_that_did_not_happen_is_not_measured_after(ledger, greet_repo):
    meter = FixedMeter(0.5, 0.6)
    run = iteration(ledger, greet_repo, meter)
    run.begin()
    done = run.finish(did_work=False)
    assert meter.reads == 1 and done.did_work is False
    assert [(r.before, r.after) for r in done.results] == [(0.5, None)]


def test_a_row_kept_under_the_task_alone_counts_but_one_from_before_the_work_began_does_not(ledger, greet_repo):
    ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="task-1", metric_id="m", before=1, ts=1.0))   # an earlier run
    run = iteration(ledger, greet_repo, FixedMeter())
    ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="task-1", metric_id="m", after=2, ts=time.time() + 1))
    assert [r.after for r in run.rows()] == [2.0]


def test_a_meter_that_never_answers_does_not_hold_the_work_back_and_the_row_after_says_so(ledger, greet_repo):
    told, stuck = [], StuckMeter()
    run = iteration(ledger, greet_repo, stuck, status=told.append, budget_seconds=0.3)
    started = time.monotonic()
    run.begin()
    assert time.monotonic() - started < 3 and stuck.reads == 1
    assert "No starting value in time. Going on without it." in told
    stuck.release.set()
    assert run.gaps == ["no reading before the change: stuck did not finish within 0.3s"]

    class Later(StuckMeter):
        name = "later"

        def measure(self, spec_slice, working_dir=None):
            self.reads += 1
            if self.reads == 1:
                self.release.wait(30)
                return None
            return 0.8

    later = Later()
    second = iteration(ledger, greet_repo, later, budget_seconds=0.3)
    second.begin()
    later.release.set()
    (only,) = second.finish().results
    assert (only.before, only.after) == (None, 0.8)
    assert only.reason == "measured by later; no reading before the change: later did not finish within 0.3s"


def test_the_iteration_never_raises_into_the_work_it_records(ledger, greet_repo):
    class Broken:
        def slice_for(self, request, working_dir=None):
            raise RuntimeError("boom")

    run = MetricIteration(ledger, "run-1", source=Broken(), meters=[FixedMeter(1.0)], request=GREETING)
    assert run.begin() == ""

    class BrokenLedger:
        def record(self, result):
            raise RuntimeError("disk")

        def for_run(self, run_id):
            raise RuntimeError("disk")

    assert MetricIteration(BrokenLedger(), "run-1").finish() == Finished([], True)
