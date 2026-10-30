"""The metric record: the result type and the ledger two processes share.

ESOI asks every piece of work to say what the relevant metric was before and after the change. These tests pin the part of
that which is plain data and plain files: a number is a number and nothing a model typed is converted into one, a ledger
append from several threads and processes never tears a line, and the rows of different sources are reconciled without one
overwriting another. Offline: no model, no network.
"""
import math
import os
import threading
from concurrent.futures import ProcessPoolExecutor

import pytest

from esoi.metric_results import (
    MAX_METRICS, NOT_RECORDED_LINE, SOURCE_MEASURED, SOURCE_NOT_APPLICABLE, SOURCE_RECORDED, FileMetricLedger,
    MetricResult, decimals_written, differs, payload_of, reconcile, render_line, without_line)

PAYLOAD_KEYS = {"solution_id", "metric_id", "name", "milestone", "before", "after", "delta", "source", "reason",
                "disagrees"}


def measured(**kw):
    return MetricResult(source=SOURCE_MEASURED, run_id="r1", metric_id="metric-x", solution_id="sol-x",
                        name="Pass rate", **kw)


def recorded(**kw):
    return MetricResult(source=SOURCE_RECORDED, run_id="r1", metric_id="metric-x", **kw)


# -- the result type ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["0.8", "80%", "nan", True, False, [1], {"a": 1}, math.nan, math.inf, -math.inf])
def test_a_value_that_is_not_a_finite_number_is_rejected_not_converted(bad):
    with pytest.raises(ValueError):
        measured(before=bad)
    with pytest.raises(ValueError):
        measured(after=bad)


def test_ints_and_floats_are_kept_as_floats_and_the_delta_is_computed():
    result = measured(before=2, after=2.5)
    assert (result.before, result.after, result.delta) == (2.0, 2.5, 0.5)
    assert measured(after=1).delta is None   # a delta needs both ends


def test_a_result_needs_a_value_unless_it_is_not_applicable():
    with pytest.raises(ValueError):
        measured()
    with pytest.raises(ValueError):
        MetricResult(source="guessed", before=1)


def test_not_applicable_needs_a_reason_and_carries_no_values():
    with pytest.raises(ValueError, match="reason"):
        MetricResult(source=SOURCE_NOT_APPLICABLE, run_id="r1")
    with pytest.raises(ValueError, match="values"):
        MetricResult(source=SOURCE_NOT_APPLICABLE, run_id="r1", reason="a draft", before=1)
    assert MetricResult(source=SOURCE_NOT_APPLICABLE, run_id="r1", reason="  a draft  ").reason == "a draft"


def test_the_consumer_entry_has_exactly_the_documented_keys_and_the_row_adds_the_run():
    result = measured(before=0.5, after=0.75)
    assert set(result.to_dict()) == PAYLOAD_KEYS
    assert set(result.to_row()) == PAYLOAD_KEYS | {"run_id", "task_id", "ts"}
    assert MetricResult.from_row(result.to_row()) == result
    with pytest.raises(ValueError):
        MetricResult.from_row({"source": "measured", "before": "x"})


def test_free_text_is_cut_so_a_line_stays_small():
    result = MetricResult(source=SOURCE_RECORDED, run_id="r1", metric_id="m", before=1, name="n" * 1000,
                          milestone="m" * 1000)
    assert len(result.name) <= 160 and len(result.milestone) <= 300


# -- the ledger --------------------------------------------------------------------------------

def test_rows_roundtrip_under_their_run_and_an_unknown_run_is_empty(tmp_path):
    ledger = FileMetricLedger(str(tmp_path))
    assert ledger.record(measured(before=0.5)) and ledger.record(recorded(after=0.9))
    assert [r.source for r in ledger.for_run("r1")] == [SOURCE_MEASURED, SOURCE_RECORDED]
    assert ledger.for_run("other") == [] and ledger.for_run("") == []
    assert not ledger.record(MetricResult(source=SOURCE_RECORDED, metric_id="m", before=1))   # no run id: nowhere to keep it


def test_a_malformed_line_is_skipped_not_fatal(tmp_path):
    ledger = FileMetricLedger(str(tmp_path))
    ledger.record(measured(before=0.5))
    with open(ledger.files.path_for("r1"), "a", encoding="utf-8") as fh:
        fh.write("not json\n{\"source\": \"measured\", \"before\": \"text\"}\n[1]\n")
    ledger.record(recorded(after=0.9))
    assert [r.source for r in ledger.for_run("r1")] == [SOURCE_MEASURED, SOURCE_RECORDED]


def test_threads_appending_together_never_tear_a_line(tmp_path):
    ledger = FileMetricLedger(str(tmp_path))
    barrier = threading.Barrier(8)

    def writer(n):
        barrier.wait()
        for i in range(25):
            assert ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="r1", metric_id=f"m{n}-{i}",
                                              before=float(i), reason="x" * 200))

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(ledger.for_run("r1")) == 8 * 25


def write_rows(directory, n):
    ledger = FileMetricLedger(directory)
    for i in range(30):
        ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="shared", metric_id=f"p{n}-{i}", after=float(i)))


def test_processes_appending_together_share_one_run(tmp_path):
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(write_rows, [str(tmp_path)] * 4, range(4)))
    assert len(FileMetricLedger(str(tmp_path)).for_run("shared")) == 4 * 30


def test_a_new_ledger_file_has_the_permissions_an_ordinary_write_gets(tmp_path):
    old = os.umask(0o027)
    try:
        ledger = FileMetricLedger(str(tmp_path / "fresh"))
        ledger.record(measured(before=1))
    finally:
        os.umask(old)
    assert os.stat(ledger.files.path_for("r1")).st_mode & 0o777 == 0o640   # 0666 minus the umask, never mkstemp's 0600


def test_a_file_untouched_for_days_is_pruned_when_the_next_row_is_kept(tmp_path):
    ledger = FileMetricLedger(str(tmp_path))
    ledger.record(measured(before=1))
    old = ledger.files.path_for("r1")
    os.utime(old, (1, 1))
    ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="r2", metric_id="m", before=1))
    assert not os.path.exists(old) and len(ledger.for_run("r2")) == 1


def test_a_free_text_run_id_cannot_leave_the_directory(tmp_path):
    ledger = FileMetricLedger(str(tmp_path / "ledger"))
    assert ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="../../escape", metric_id="m", before=1))
    assert os.path.dirname(ledger.files.path_for("../../escape")) == str(tmp_path / "ledger")
    assert len(ledger.for_run("../../escape")) == 1


def test_the_payload_cap_is_an_argument():
    rows = [MetricResult(source=SOURCE_RECORDED, run_id="r1", metric_id=f"m{i}", after=1) for i in range(5)]
    assert len(reconcile(rows, limit=2)) == 2 and len(reconcile(rows)) == 5


# -- reconciling rows --------------------------------------------------------------------------

def test_a_measured_before_and_the_later_after_become_one_row():
    rows = [measured(before=0.5, ts=1.0), measured(after=0.75, ts=2.0)]
    (only,) = reconcile(rows)
    assert (only.before, only.after, only.delta, only.disagrees) == (0.5, 0.75, 0.25, False)


def test_measured_and_recorded_stay_two_rows_and_disagreement_flags_both():
    out = reconcile([measured(before=0.5, after=0.75), recorded(before=0.5, after=0.9)])
    assert [r.source for r in out] == [SOURCE_MEASURED, SOURCE_RECORDED]
    assert all(r.disagrees for r in out)
    assert (out[0].after, out[1].after) == (0.75, 0.9)   # neither overwrote the other


@pytest.mark.parametrize("value, places", [(0.4, 1), (0.38, 2), (14.0, 1), (1, 1), (0.125, 3), (100.0, 1), (1e-05, 5),
                                            (1e22, 0), (0.30000000000000004, 17)])
def test_the_decimals_a_number_is_written_with_are_those_of_its_shortest_exact_form(value, places):
    assert decimals_written(value) == places


@pytest.mark.parametrize("measured_value, recorded_value", [
    (0.38, 0.4), (0.91, 0.9), (0.381, 0.38), (0.25, 0.3), (0.35, 0.4), (0.9, 0.9), (14.04, 14.0), (0.1 + 0.2, 0.3),
    (0.0, 0.0), (0.96, 1.0),
])
def test_a_measured_value_rounded_to_the_decimals_the_recorded_one_is_written_with_agrees(measured_value, recorded_value):
    assert differs(measured_value, recorded_value) is False


@pytest.mark.parametrize("measured_value, recorded_value", [
    (0.38, 0.3), (0.38, 0.5), (0.4, 0.38), (0.6, 1.0), (0.91, 0.89), (0.404, 0.41), (0.0, 0.1), (1e30, 1e29),
])
def test_anything_else_is_a_real_difference_and_a_more_exact_recorded_number_cannot_be_rounded_into_agreement(
        measured_value, recorded_value):
    assert differs(measured_value, recorded_value) is True


def test_a_missing_value_never_differs():
    assert differs(None, 0.5) is False and differs(0.5, None) is False and differs(None, None) is False


def test_there_is_no_tolerance_a_tiny_gap_the_recorded_precision_shows_is_a_difference():
    assert differs(0.3000001, 0.3000002) is True
    assert differs(0.30000004, 0.3000000) is False   # the recorded value is written with seven decimals


def test_rounding_that_makes_the_numbers_agree_flags_nothing_in_the_ledger_rows():
    """0.38 measured and 0.4 recorded say the same thing; 0.91 and 0.9 likewise. Only a true difference is flagged."""
    out = reconcile([measured(before=0.38, after=0.91), recorded(before=0.4, after=0.9)])
    assert not any(r.disagrees for r in out)
    out = reconcile([measured(before=0.38, after=0.91), recorded(before=0.4, after=0.8)])
    assert all(r.disagrees for r in out)


def test_agreement_flags_nothing_and_an_unshared_end_is_not_a_disagreement():
    out = reconcile([measured(before=0.5, after=0.75), recorded(before=0.5)])
    assert not any(r.disagrees for r in out)


def na(reason):
    return MetricResult(source=SOURCE_NOT_APPLICABLE, run_id="r1", reason=reason)


def test_not_applicable_rows_are_deduplicated_by_reason_and_stay_when_they_are_all_there_is():
    out = reconcile([na("a draft"), na("a draft"), na("an edit")])
    assert [(r.source, r.reason) for r in out] == [(SOURCE_NOT_APPLICABLE, "a draft"), (SOURCE_NOT_APPLICABLE, "an edit")]


@pytest.mark.parametrize("number", [dict(before=0.5), dict(after=1), dict(before=0.5, after=1)])
def test_a_reading_beats_a_shrug_a_not_applicable_row_is_dropped_once_any_row_holds_a_number(number):
    """The same run showed "1 -> 1 (measured)" and "Nothing to measure" together; the ledger still holds both."""
    rows = [measured(**number), na("a draft"), recorded(**number), na("an edit")]
    assert [r.source for r in reconcile(rows)] == [SOURCE_MEASURED, SOURCE_RECORDED]
    assert [r.source for r in reconcile([na("a draft"), recorded(**number)])] == [SOURCE_RECORDED]
    assert [r.source for r in reconcile([measured(**number), na("a draft")])] == [SOURCE_MEASURED]


def test_the_dropped_not_applicable_rows_stay_in_the_ledger_file(tmp_path):
    ledger = FileMetricLedger(str(tmp_path))
    for row in (measured(before=1.0), na("a draft"), measured(after=1.0)):
        assert ledger.record(row)
    assert [r.source for r in ledger.for_run("r1")] == [SOURCE_MEASURED, SOURCE_NOT_APPLICABLE, SOURCE_MEASURED]
    assert [r.source for r in reconcile(ledger.for_run("r1"))] == [SOURCE_MEASURED]


def test_the_payload_is_capped():
    rows = [MetricResult(source=SOURCE_RECORDED, run_id="r1", metric_id=f"m{i}", after=1) for i in range(MAX_METRICS + 5)]
    assert len(reconcile(rows)) == MAX_METRICS


def test_the_text_line_is_written_from_the_payload():
    payload = payload_of(reconcile([measured(before=0.5, after=0.75)]))
    assert render_line(payload) == "Metric: Pass rate 0.5 -> 0.75 (measured)"
    assert render_line([]) == "" and render_line([], missing=True) == NOT_RECORDED_LINE
    na = payload_of([MetricResult(source=SOURCE_NOT_APPLICABLE, run_id="r1", reason="a draft")])
    assert render_line(na) == "Metric: not applicable (a draft)"
    flagged = payload_of(reconcile([measured(after=0.75), recorded(after=0.9)]))
    assert "differs" in render_line(flagged)
    for text in (render_line(payload), render_line(na), NOT_RECORDED_LINE):
        assert chr(0x2014) not in text


def test_a_consumer_that_shows_the_entries_itself_can_drop_the_plain_line_and_nothing_else():
    payload = payload_of(reconcile([measured(before=0.5, after=0.75)]))
    line = render_line(payload)
    assert without_line(f"Changed it.\n\n{line}", payload) == "Changed it."
    assert without_line(f"First.\n\n{line}\n\nSecond.", payload) == "First.\n\nSecond."
    assert without_line(f"Changed it.\n\n{NOT_RECORDED_LINE}", [], missing=True) == "Changed it."
    # Only the whole line written for exactly these entries goes: other text, other entries, a quoted line stay.
    other = payload_of(reconcile([measured(before=0.1, after=0.2)]))
    assert without_line(f"Changed it.\n\n{line}", other) == f"Changed it.\n\n{line}"
    assert without_line(f"I wrote: {line} myself.", payload) == f"I wrote: {line} myself."
    assert without_line("", payload) == "" and without_line("Same.", []) == "Same."
