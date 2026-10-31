"""Public evidence: the record format, the grading table, the caps and flags, units, ranking and agreement with our results."""
import datetime

import pytest

from esoi import cascade, evidence

TODAY = datetime.date(2026, 10, 31)


def ev(id_, candidate="alpha", dimension="quality", value=0.7, unit="fraction", kind="independent_benchmark", by="yes",
       method="yes", n=500, status="live", published="2026-09-01", confounds="", measure="pass_rate", comparator="bench-1",
       url=None, better="higher"):
    cells = dict(evidence_id=id_, candidate=candidate, dimension=dimension, measure=measure, value=str(value), unit=unit,
                 better=better, comparator=comparator, source_url=url or f"https://example.org/{id_}", source_kind=kind,
                 run_by_independent=by, method_disclosed=method, n=str(n) if n else "", benchmark_status=status,
                 date_published=published, date_checked="2026-10-30", confounds=confounds, note="")
    return cells


def rows(*cells):
    found, problems = evidence.parse_rows(cells)
    assert problems == []
    return found


def grade(*cells, **kw):
    return evidence.estimates(rows(*cells), TODAY)[("alpha", "quality")]


def test_the_record_is_read_and_every_problem_is_named_not_dropped():
    good = ev("E1")
    bad = dict(ev("E2"), dimension="speedy", value="fast", n="-3", source_url="not a link", date_checked="yesterday")
    dup = ev("E1", candidate="beta")
    found, problems = evidence.parse_rows([good, bad, dup])
    assert [e.evidence_id for e in found] == ["E1"]
    text = "\n".join(problems)
    for needle in ("dimension", "value", "n is", "source_url", "date_checked", "repeats line 2"):
        assert needle in text
    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.parse_text(evidence.header_line() + "\n" + "E9,a,quality\n")
    assert any("empty" in p for p in caught.value.problems)


def test_a_header_with_a_missing_or_unknown_column_is_refused_and_a_blank_enum_must_say_unknown():
    with pytest.raises(evidence.EvidenceError, match="column note is missing"):
        evidence.parse_text(",".join(c for c in evidence.COLUMNS if c != "note") + "\n")
    blank = dict(ev("E1"), benchmark_status="")
    assert any("benchmark_status is empty" in p for p in evidence.parse_rows([blank])[1])


def test_two_rows_for_one_measure_cannot_disagree_on_which_direction_is_better():
    found, problems = evidence.parse_rows([ev("E1"), ev("E2", better="lower")])
    assert any("says higher" in p for p in problems)


@pytest.mark.parametrize("cells,letter", [
    ([ev("E1", kind="independent_benchmark", n=500, method="yes", by="yes", published="2026-10-01")], "B"),   # 10 points, capped by one source
    ([ev("E1", n=40, method="partial", by="unknown")], "B"),                                                  # 4+0+1+1 = 6
    ([ev("E1", n=None, method="no", by="unknown", status="unknown")], "D"),                                   # 4+0+0+0-1 = 3
    ([ev("E1", kind="community_report", by="unknown", method="partial", n=40)], "C"),                         # 2+0+1+1 = 4
])
def test_the_grading_table_gives_the_letter_for_the_points(cells, letter):
    assert grade(*cells).grade == letter


def test_a_lone_vendor_number_is_grade_d_whatever_it_discloses_and_needs_an_own_run():
    est = grade(ev("V1", kind="vendor_reported", by="no", method="yes", n=1000, published="2026-10-20"))
    assert est.grade == "D" and "vendor_only" in est.flags and est.needs_own_run
    assert "independent run" in est.settle


def test_a_vendor_cannot_rank_above_an_independently_measured_arm():
    data = rows(ev("V1", candidate="vendorco", value=0.95, kind="vendor_reported", by="no"),
                ev("I1", candidate="steady", value=0.70))
    ranking = evidence.rank(data, {"quality": 1}, today=TODAY)
    order = [p.candidate for p in ranking.dimensions["quality"].ordered]
    assert order == ["steady", "vendorco"]
    assert "below every candidate with better evidence" in ranking.dimensions["quality"].ordered[1].reason
    assert [o.candidate for o in ranking.overall][0] == "steady"


def test_two_independent_sources_that_agree_raise_confidence_and_one_source_is_capped_at_b():
    one = grade(ev("I1"))
    two = grade(ev("I1"), ev("I2", value=0.72))
    assert "single_source" in one.flags and one.grade == "B"
    assert two.grade == "A" and "single_source" not in two.flags and not two.needs_own_run
    assert two.value == pytest.approx(0.71)


def test_a_contradiction_lowers_the_grade_names_both_rows_and_blocks_use():
    est = grade(ev("I1", value=0.80), ev("I2", value=0.50))
    assert "contradicts" in est.flags and est.grade == "B" and est.needs_own_run   # A lowered one letter
    assert est.contradictions[0][:2] == ("I1", "I2")
    assert any("I1 and I2" in r for r in est.reasons)
    assert "I1 and I2" in est.settle


def test_a_vendor_outlier_next_to_agreeing_independents_is_ignored_but_said():
    est = grade(ev("I1"), ev("I2", value=0.71), ev("V1", kind="vendor_reported", by="no", value=0.99))
    assert est.grade == "A" and "contradicts" not in est.flags
    assert any("V1 is not counted" in r or "V1" in r and "not counted" in r for r in est.reasons)


def test_units_convert_only_through_the_table_and_otherwise_are_flagged():
    est = evidence.estimates(rows(ev("T1", dimension="speed", value=1.2, unit="s", measure="latency", better="lower", comparator=""),
                                  ev("T2", dimension="speed", value=1200, unit="ms", measure="latency", better="lower", comparator="")),
                             TODAY)[("alpha", "speed")]
    assert est.unit == "s" and est.value == pytest.approx(1.2) and "contradicts" not in est.flags and est.grade == "A"
    mixed = evidence.estimates(rows(ev("T1", dimension="speed", value=1.2, unit="s", measure="latency", better="lower", comparator=""),
                                    ev("T2", dimension="speed", value=900, unit="tokens/s", measure="latency", better="lower",
                                       comparator="")), TODAY)[("alpha", "speed")]
    assert "unit_mismatch" in mixed.flags and mixed.needs_own_run
    assert evidence.convert(80, "percent") == (pytest.approx(0.8), "fraction")


def test_different_measures_or_comparators_are_never_merged():
    found = evidence.all_estimates(rows(ev("E1"), ev("E2", comparator="bench-2", value=0.4)), TODAY)[("alpha", "quality")]
    assert len(found) == 2 and found[0].other_bases


def test_old_evidence_is_stale_and_prices_go_stale_before_quality():
    quality = grade(ev("I1", published="2026-01-15"))                    # 289 days: past half of 365
    assert "stale" not in quality.flags
    price = evidence.estimates(rows(ev("C1", dimension="cost", measure="price", unit="usd/mtok", better="lower", comparator="",
                                       published="2026-05-01")), TODAY)[("alpha", "cost")]
    assert "stale" in price.flags
    assert grade(ev("I1", published="2024-01-01")).points < grade(ev("I1")).points


def test_a_saturated_benchmark_is_flagged_and_blocks_use():
    est = grade(ev("I1", status="saturated"), ev("I2", status="saturated", value=0.71))
    assert "saturated" in est.flags and est.needs_own_run
    assert "own cases or a live benchmark" in est.settle


def test_a_named_confound_is_flagged_lowers_points_and_is_in_the_settle_text():
    clean = grade(ev("I1"))
    est = grade(ev("I1", confounds="different tool harness; longer prompt"))
    assert "confounded" in est.flags and est.points == clean.points - 2 and est.needs_own_run
    assert "different tool harness" in est.settle and est.confounds


def test_no_method_is_flagged():
    assert "no_method" in grade(ev("I1", method="no")).flags


def test_needs_own_run_is_false_for_good_unflagged_evidence():
    est = grade(ev("I1"), ev("I2", value=0.71))
    assert est.needs_own_run is False and est.settle == ""


def test_ranking_orders_by_better_direction_notes_ties_and_separates_bases():
    data = rows(ev("A1", candidate="fast", dimension="speed", value=2, unit="s", measure="latency", better="lower", comparator=""),
                ev("A2", candidate="slow", dimension="speed", value=9, unit="s", measure="latency", better="lower", comparator=""),
                ev("A3", candidate="same", dimension="speed", value=2.2, unit="s", measure="latency", better="lower", comparator=""),
                ev("A4", candidate="odd", dimension="speed", value=40, unit="tokens/s", measure="throughput", better="higher",
                   comparator=""))
    shortlist = evidence.rank(data, {"speed": 1}, today=TODAY).dimensions["speed"]
    assert [p.candidate for p in shortlist.ordered] == ["fast", "same", "slow"]
    assert shortlist.ordered[1].tied_with == ("fast",)
    assert [name for name, _ in shortlist.not_comparable] == ["odd"]


def test_ranking_names_candidates_with_no_evidence_and_rejects_an_unknown_dimension():
    ranking = evidence.rank(rows(ev("I1")), {"quality": 1}, candidates=["alpha", "ghost"], today=TODAY)
    assert ranking.dimensions["quality"].no_evidence == ["ghost"]
    with pytest.raises(ValueError):
        evidence.rank(rows(ev("I1")), {"vibes": 1})


def test_agrees_with_results_reports_agreement_and_conflict_as_information():
    data = rows(ev("I1", candidate="alpha", value=0.80), ev("I2", candidate="alpha", value=0.81, ),
                ev("I3", candidate="beta", value=0.60), ev("I4", candidate="beta", value=0.61))
    ranking = evidence.rank(data, {"quality": 1}, today=TODAY)
    assert ranking.agrees_with_results({"alpha": 0.9, "beta": 0.5}).verdict == "agree"
    conflict = ranking.agrees_with_results({"alpha": 0.4, "beta": 0.9})
    assert conflict.verdict == "conflict" and "Information, not an error" in conflict.lines[0]
    assert ranking.agrees_with_results({"alpha": 0.5, "beta": 0.51}).verdict == "insufficient"
    assert ranking.agrees_with_results({"alpha": 0.9}).verdict == "insufficient"


def test_a_grade_d_candidate_is_left_out_of_the_comparison_with_our_results():
    data = rows(ev("I1", candidate="alpha"), ev("V1", candidate="vendorco", value=0.99, kind="vendor_reported", by="no"))
    agreement = evidence.rank(data, {"quality": 1}, today=TODAY).agrees_with_results({"alpha": 0.5, "vendorco": 0.9})
    assert agreement.verdict == "insufficient" and any("vendorco" in line for line in agreement.excluded)


def test_the_cascade_reads_a_public_stage_as_a_stage_that_runs_nothing():
    stages, errors = cascade.parse("public [real=no | when=others measured it] > offline [sample=full | real=no | gate=all-pass]")
    assert errors == [] and stages[0].public
    assert cascade.matches(stages[0], dict(sample="", model_calls="0", model="none")) is False
    assert cascade.parse("public [real=yes]")[1]
    ok, why = evidence.public_stage_met([grade(ev("I1"), ev("I2", value=0.71))])
    assert ok and "A" in why
    assert evidence.public_stage_met([])[0] is False


class Stub:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_the_cascade_shows_public_evidence_per_implementation_labelled_and_never_as_a_result():
    registry = Stub(implementations=[{"solution_id": "s", "implementation_id": "s:Lexical-Only", "name": "Lexical only"},
                                     {"solution_id": "s", "implementation_id": "s:other", "name": "Other"},
                                     {"solution_id": "t", "implementation_id": "t:alpha", "name": "Alpha"}])
    config = Stub(evidence={"aliases": {"Vendor-Lex": "other"}})
    found = evidence.estimates(rows(ev("I1", candidate="lexical_only"), ev("V1", candidate="vendor-lex", kind="vendor_reported", by="no")),
                               TODAY)
    out = []
    stages, _ = cascade.parse("public [real=no | when=others measured it] > offline [sample=full | real=no]")
    cascade.public_lines(evidence, config, registry, "s", found, stages, out.append)
    text = "\n".join(out)
    assert "public evidence for Lexical-Only (others' measurements, not our result)" in text
    assert "public stage satisfied" in text and "public stage not satisfied" in text   # the vendor-only alias reads D
    assert "public evidence for alpha" not in text
