"""Cascading conditionals: the stage grammar, the selection rule, expiry, null results and what to run next."""
import datetime

from esoi import cascade, check, tables

TODAY = datetime.date(2026, 10, 29)
LIST = ("offline [sample=full | real=no | gate=all-pass] > staged [sample=sample | real=yes | gate=competitive | "
        "max-age-days=90 | when=a person approved the spend] > whole [sample=full | real=yes]")


def row(impl, passed, cases=10, sample="", calls=0, date="2026-10-20", sha="x"):
    return dict(date=date, component="c", impl=impl, passed=str(passed), cases=str(cases), cost_usd="0.0", cases_sha=sha,
                model_calls=str(calls), tokens_in="0", tokens_out="0", heldout="0/0", sample=sample, model="m" if calls else "none")


def fresh(result):
    return ""


def stages():
    found, errors = cascade.parse(LIST)
    assert errors == []
    return found


def test_the_list_is_read_into_ordered_stages():
    first, second, third = stages()
    assert [s.name for s in (first, second, third)] == ["offline", "staged", "whole"]
    assert (first.sample, first.real, first.gate) == ("full", False, "all-pass")
    assert (second.gate, second.max_age_days, second.when) == ("competitive", 90, "a person approved the spend")
    assert not third.gated


def test_an_empty_cell_is_no_cascade_and_the_unconfirmed_marker_is_not_part_of_the_list():
    assert cascade.parse("") == ([], [])
    marked, errors = cascade.parse("unconfirmed: for Joshua to confirm. a [gate=all-pass] > b")
    assert errors == [] and [s.name for s in marked] == ["a", "b"]


def test_a_malformed_list_says_what_is_wrong():
    _, errors = cascade.parse("a [gate=sometimes | colour=red | min-pass-rate=2 | max-age-days=0] > a > B C")
    text = " ".join(errors)
    for expected in ("gate=sometimes", "colour=red", "min-pass-rate=2", "max-age-days=0", "used twice", "is not `name"):
        assert expected in text
    assert any("no gate or min-pass-rate" in e for e in cascade.parse("a > b")[1])


def test_a_row_belongs_to_the_first_stage_that_claims_it():
    s = stages()
    assert cascade.stage_index(s, row("x", 10)) == 0                           # whole set, no model
    assert cascade.stage_index(s, row("x", 5, 5, sample="sample:5", calls=3)) == 1
    assert cascade.stage_index(s, row("x", 10, calls=3)) == 2                  # whole set with a model
    assert cascade.stage_index(s, row("x", 5, 5, sample="sample:5")) is None  # sampled, no model: no stage claims it


def test_a_stage_that_was_not_run_has_no_result_and_is_next():
    s = stages()
    standing = cascade.standings(s, {"a": [row("a", 10)]}, TODAY, fresh)
    assert standing["a"].rows.keys() == {0}
    assert cascade.next_stage(s, standing["a"])[0] == 1
    assert cascade.next_stage(s, standing["a"])[1] == "not run"


def test_a_failed_gate_stops_the_cascade():
    s = stages()
    standing = cascade.standings(s, {"a": [row("a", 9)]}, TODAY, fresh)
    index, why = cascade.next_stage(s, standing["a"])
    assert index is None and "not every case passed" in why


def test_the_competitive_gate_compares_with_the_selected_implementation():
    s = stages()
    history = {"sel": [row("sel", 10), row("sel", 9, 10, "sample:10", 3)], "new": [row("new", 10), row("new", 3, 10, "sample:10", 3)]}
    standing = cascade.standings(s, history, TODAY, fresh)
    index, why = cascade.next_stage(s, standing["new"], standing["sel"])
    assert index is None and "sel clearly beats it" in why


def test_a_result_expires_when_it_is_stale_or_older_than_the_stage_allows():
    s = stages()
    old = row("a", 9, 10, "sample:10", 3, date="2026-06-01")
    standing = cascade.standings(s, {"a": [row("a", 10), old]}, TODAY, fresh)["a"]
    assert 1 in standing.expired and "days old" in standing.expired[1][1] and 1 not in standing.rows
    assert cascade.next_stage(s, standing)[1].startswith("expired")
    changed = cascade.standings(s, {"a": [row("a", 10)]}, TODAY, lambda r: "the measured code changed")["a"]
    assert changed.rows == {} and 0 in changed.expired


def test_the_latest_stage_run_decides_between_the_implementations_that_reached_it():
    s = stages()
    history = {"a": [row("a", 10), row("a", 6, 10, "sample:10", 3)], "b": [row("b", 10), row("b", 9, 10, "sample:10", 3)]}
    decision = cascade.decide(s, cascade.standings(s, history, TODAY, fresh))
    assert (decision.winner, decision.stage, decision.pending) == ("b", 1, [])


def test_one_that_led_at_a_shared_earlier_stage_stays_chosen_until_run_at_the_latest():
    s = stages()
    base = {"a": [row("a", 7), row("a", 6, 10, "sample:10", 3)], "b": [row("b", 7), row("b", 8, 10, "sample:10", 3)]}
    assert cascade.decide(s, cascade.standings(s, base, TODAY, fresh)).winner == "b"       # b leads the latest stage
    held = cascade.decide(s, cascade.standings(s, {**base, "c": [row("c", 10)]}, TODAY, fresh))
    # c scored higher than b at offline, the stage they share, and has not been run at staged
    assert held.winner == "c" and held.pending == ["c"] and held.leader == "b"
    assert any("run it there" in n for n in held.notes)
    run = {**base, "c": [row("c", 10), row("c", 3, 10, "sample:10", 3)]}                   # once run, its later score decides
    settled = cascade.decide(s, cascade.standings(s, run, TODAY, fresh))
    assert settled.winner == "b" and settled.pending == []


def test_results_on_other_cases_are_not_compared():
    s = stages()
    history = {"a": [row("a", 10)], "b": [row("b", 10, 20, sha="other")]}
    decision = cascade.decide(s, cascade.standings(s, history, TODAY, fresh))
    assert decision.winner == "b" and any("not compared" in n for n in decision.notes)


def test_nothing_counting_chooses_nothing():
    decision = cascade.decide(stages(), cascade.standings(stages(), {}, TODAY, fresh))
    assert decision.winner == "" and decision.stage == -1


def test_the_run_line_reproduces_the_stage_sample():
    s = cascade.parse("a [sample=sample:10 | real=yes | gate=all-pass] > b [sample=full]")[0]
    assert cascade.run_command("comp", "impl", s[0]) == "esoi run comp --impl impl --sample 10 --record"
    assert cascade.run_command("comp", "impl", s[1]) == "esoi run comp --impl impl --record"


def set_cascade(cfg, text):
    path = cfg.structure / "metrics.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    assert "cascading_conditionals" in cols
    for r in rows:
        if r["metric_id"] == "greeting-pass-rate":
            r["cascading_conditionals"] = text
    tables.write_csv(path, cols, rows)


def test_s32_reports_a_list_that_cannot_be_read(cfg):
    assert not any(line.startswith("S32") for line in check.check(cfg))
    set_cascade(cfg, "offline [gate=maybe]")
    assert any(line.startswith("S32 metrics.csv greeting-pass-rate") and "gate=maybe" in line for line in check.check(cfg))


def test_s33_follows_the_cascade_and_a_waiver_names_the_pending_decision(cfg):
    set_cascade(cfg, "whole [sample=full | real=no]")
    selected = "live"
    assert not any(line.startswith("S33") for line in check.check(cfg))
    results = tables.read_csv(cfg.results_path)
    for r in results:
        if r["impl"] != "live":
            r["passed"], r["dev"] = "0", "0/2"                              # the selected arm is the best: still clean
    assert not any(line.startswith("S33") for line in check.check(cfg))
    for r in results:
        r["passed"], r["dev"] = ("2", "2/2") if r["impl"] == "shout" else ("0", "0/2")
    tables.write_csv(cfg.results_path, tables.read_header(cfg.results_path), results)
    found = [line for line in check.check(cfg) if line.startswith("S33")]
    assert found and "shout" in found[0] and selected in found[0]


def test_the_cascade_command_reports_stages_results_and_the_next_run(cfg, capsys):
    set_cascade(cfg, "whole [sample=full | real=no]")
    assert cascade.run_cli(cfg, "greet-a-person", strict=False) == 0
    out = capsys.readouterr().out
    assert "greeting-pass-rate: whole" in out and "chosen by the cascade:" in out and "next for" in out
