"""Cascading conditionals: the stage grammar, the selection rule, expiry, null results and what to run next."""
import datetime

from esoi.optimization.leaderboard import cascade_report, cascade_stages, stage_standings
from esoi.structure.structure_check import check
from esoi.structure.intent_registry import tables

TODAY = datetime.date(2026, 10, 29)
LIST = ("offline [sample=full | real=no | gate=all-pass] > staged [sample=sample | real=yes | gate=competitive | "
        "max-age-days=90 | when=a person approved the spend] > whole [sample=full | real=yes]")


def row(impl, passed, cases=10, sample="", calls=0, date="2026-10-20", sha="x", model=""):
    return dict(date=date, component="c", impl=impl, passed=str(passed), cases=str(cases), cost_usd="0.0", cases_sha=sha,
                model_calls=str(calls), tokens_in="0", tokens_out="0", heldout="0/0", sample=sample,
                model=model or ("m" if calls else "none"))


def offline(impl, passed):
    """A whole-set run of an arm with a simulated model: a free first stage of an arm that does call a model later."""
    return row(impl, passed, model="simulated")


def fresh(result):
    return ""


def stages():
    found, errors = cascade_stages.parse(LIST)
    assert errors == []
    return found


def test_the_list_is_read_into_ordered_stages():
    first, second, third = stages()
    assert [s.name for s in (first, second, third)] == ["offline", "staged", "whole"]
    assert (first.sample, first.real, first.gate) == ("full", False, "all-pass")
    assert (second.gate, second.max_age_days, second.when) == ("competitive", 90, "a person approved the spend")
    assert not third.gated


def test_an_empty_cell_is_no_cascade_and_the_unconfirmed_marker_is_not_part_of_the_list():
    assert cascade_stages.parse("") == ([], [])
    marked, errors = cascade_stages.parse("unconfirmed: for Joshua to confirm. a [gate=all-pass] > b")
    assert errors == [] and [s.name for s in marked] == ["a", "b"]


def test_a_malformed_list_says_what_is_wrong():
    _, errors = cascade_stages.parse("a [gate=sometimes | colour=red | min-pass-rate=2 | max-age-days=0] > a > B C")
    text = " ".join(errors)
    for expected in ("gate=sometimes", "colour=red", "min-pass-rate=2", "max-age-days=0", "used twice", "is not `name"):
        assert expected in text
    assert any("no gate or min-pass-rate" in e for e in cascade_stages.parse("a > b")[1])


def test_a_row_belongs_to_the_first_stage_that_claims_it():
    s = stages()
    assert stage_standings.stage_index(s, row("x", 10)) == 0                           # whole set, no model
    assert stage_standings.stage_index(s, row("x", 5, 5, sample="sample:5", calls=3)) == 1
    assert stage_standings.stage_index(s, row("x", 10, calls=3)) == 2                  # whole set with a model
    assert stage_standings.stage_index(s, row("x", 5, 5, sample="sample:5")) == 1     # no model does not keep a sample out of the sampled stage


def test_an_arm_that_calls_no_model_meets_the_model_arms_at_the_same_stage():
    s = stages()
    free, paid = row("free", 9), row("paid", 8, calls=3)
    standing = stage_standings.standings(s, {"free": [free], "paid": [paid]}, TODAY, fresh)
    assert sorted(standing["free"].rows) == [0, 2] and sorted(standing["paid"].rows) == [2]
    decision = stage_standings.decide(s, standing)
    assert (decision.winner, decision.stage) == ("free", 2)   # compared directly on the same cases, the higher result wins


def test_a_stage_that_was_not_run_has_no_result_and_is_next():
    s = stages()
    standing = stage_standings.standings(s, {"a": [offline("a", 10)]}, TODAY, fresh)
    assert standing["a"].rows.keys() == {0}
    assert stage_standings.next_stage(s, standing["a"])[0] == 1
    assert stage_standings.next_stage(s, standing["a"])[1] == "not run"


def test_a_failed_gate_stops_the_cascade():
    s = stages()
    standing = stage_standings.standings(s, {"a": [row("a", 9)]}, TODAY, fresh)
    index, why = stage_standings.next_stage(s, standing["a"])
    assert index is None and "not every case passed" in why


def test_the_competitive_gate_compares_with_the_selected_implementation():
    s = stages()
    history = {"sel": [row("sel", 10), row("sel", 9, 10, "sample:10", 3)], "new": [row("new", 10), row("new", 3, 10, "sample:10", 3)]}
    standing = stage_standings.standings(s, history, TODAY, fresh)
    index, why = stage_standings.next_stage(s, standing["new"], standing["sel"])
    assert index is None and "sel has a better result at this stage" in why


def test_a_result_expires_when_it_is_stale_or_older_than_the_stage_allows():
    s = stages()
    old = row("a", 9, 10, "sample:10", 3, date="2026-06-01")
    standing = stage_standings.standings(s, {"a": [row("a", 10), old]}, TODAY, fresh)["a"]
    assert 1 in standing.expired and "days old" in standing.expired[1][1] and 1 not in standing.rows
    assert stage_standings.next_stage(s, standing)[1].startswith("expired")
    changed = stage_standings.standings(s, {"a": [row("a", 10)]}, TODAY, lambda r: "the measured code changed")["a"]
    assert changed.rows == {} and 0 in changed.expired


def test_the_latest_stage_run_decides_between_the_implementations_that_reached_it():
    s = stages()
    history = {"a": [offline("a", 10), row("a", 6, 10, "sample:10", 3)], "b": [offline("b", 10), row("b", 9, 10, "sample:10", 3)]}
    decision = stage_standings.decide(s, stage_standings.standings(s, history, TODAY, fresh))
    assert (decision.winner, decision.stage, decision.pending) == ("b", 1, [])


def test_one_that_led_at_a_shared_earlier_stage_stays_chosen_until_run_at_the_latest():
    s = stages()
    base = {"a": [offline("a", 7), row("a", 6, 10, "sample:10", 3)], "b": [offline("b", 7), row("b", 8, 10, "sample:10", 3)]}
    assert stage_standings.decide(s, stage_standings.standings(s, base, TODAY, fresh)).winner == "b"       # b leads the latest stage
    held = stage_standings.decide(s, stage_standings.standings(s, {**base, "c": [offline("c", 10)]}, TODAY, fresh))
    # c scored higher than b at offline, the stage they share, and has not been run at staged
    assert held.winner == "c" and held.pending == ["c"] and held.leader == "b"
    assert any("run it there" in n for n in held.notes)
    run = {**base, "c": [offline("c", 10), row("c", 3, 10, "sample:10", 3)]}                   # once run, its later score decides
    settled = stage_standings.decide(s, stage_standings.standings(s, run, TODAY, fresh))
    assert settled.winner == "b" and settled.pending == []


def test_results_on_other_cases_are_not_compared():
    s = stages()
    history = {"a": [row("a", 10)], "b": [row("b", 10, 20, sha="other")]}
    decision = stage_standings.decide(s, stage_standings.standings(s, history, TODAY, fresh))
    assert decision.winner == "b" and any("not compared" in n for n in decision.notes)


def test_nothing_counting_chooses_nothing():
    decision = stage_standings.decide(stages(), stage_standings.standings(stages(), {}, TODAY, fresh))
    assert decision.winner == "" and decision.stage == -1


def test_the_run_line_reproduces_the_stage_sample():
    s = cascade_stages.parse("a [sample=sample:10 | real=yes | gate=all-pass] > b [sample=full]")[0]
    assert cascade_report.run_command("comp", "impl", s[0]) == "esoi run comp --impl impl --sample 10 --record"
    assert cascade_report.run_command("comp", "impl", s[1]) == "esoi run comp --impl impl --record"


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
    assert cascade_report.run_cli(cfg, "greet-a-person", strict=False) == 0
    out = capsys.readouterr().out
    assert "greeting-pass-rate: whole" in out and "chosen by the cascade:" in out and "next for" in out


def test_promotion_follows_the_cascade_when_the_metric_has_one(cfg):
    from esoi.optimization.promote_the_winner import promote
    from esoi.structure.intent_registry import registry
    set_cascade(cfg, "whole [sample=full | real=no]")
    results, header = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in results:   # the baseline passes every case and the live arm one
        r.update(cases="40", passed="40", dev="40/40") if r["impl"] == "shout" else r.update(cases="40", passed="20", dev="20/40")
    tables.write_csv(cfg.results_path, header, results)
    [proposal] = promote.propose(cfg, registry.load(cfg), stale=lambda c, comp, row, strict: "")
    assert (proposal.winner, proposal.current) == ("shout", "live")
    assert "metric cascade" in proposal.selected_by and "latest stage run" in proposal.selected_by
    for r in results:   # the live arm passes every case: the cascade keeps it
        r.update(cases="40", passed="40", dev="40/40") if r["impl"] == "live" else r.update(cases="40", passed="20", dev="20/40")
    tables.write_csv(cfg.results_path, header, results)
    assert promote.propose(cfg, registry.load(cfg), stale=lambda c, comp, row, strict: "") == []


def clear_selected(cfg):
    path = cfg.structure / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for r in rows:
        if r["solution_id"] == "greet-a-person":
            r["selected"] = ""
    tables.write_csv(path, cols, rows)


def test_an_empty_selected_gets_its_first_choice_from_the_metric_and_a_tie_names_the_arms(cfg):
    from esoi.optimization.promote_the_winner import promote
    from esoi.structure.intent_registry import registry
    set_cascade(cfg, "whole [sample=full | real=no | gate=all-pass]")
    clear_selected(cfg)
    results, header = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in results:   # one arm passes every case, the others one
        r.update(passed="2", dev="2/2") if r["impl"] == "shout" else r.update(passed="1", dev="1/2")
    tables.write_csv(cfg.results_path, header, results)
    fresh_rows = lambda c, comp, row, strict: ""
    [proposal] = promote.propose(cfg, registry.load(cfg), stale=fresh_rows)
    assert (proposal.status, proposal.winner, proposal.selected) == ("propose", "shout", "shout")
    assert "selected" in proposal.selected_by and "shout 2/2" in proposal.selected_by
    for r in results:   # every arm passes every case: a tie, which the metric cannot break
        r.update(passed="2", dev="2/2")
    tables.write_csv(cfg.results_path, header, results)
    [tied] = promote.propose(cfg, registry.load(cfg), stale=fresh_rows)
    assert tied.status == "blocked" and "a tie at whole" in tied.reason and "shout 2/2" in tied.reason
    for r in results:   # one arm only
        if r["impl"] != "shout":
            r["impl"] = "other"
    only = [r for r in results if r["impl"] == "shout"][:1]
    tables.write_csv(cfg.results_path, header, only)
    [single] = promote.propose(cfg, registry.load(cfg), stale=fresh_rows)
    assert single.status == "propose" and single.winner == "shout"


def test_s33_does_not_fail_because_the_cases_changed_after_the_run(cfg):
    from esoi.optimization.leaderboard import case_identity
    set_cascade(cfg, "whole [sample=full | real=no]")
    path = case_identity.cases_files("greet_a_person", cfg.evaluation)[0]
    path.write_text(path.read_text() + "\n")   # every recorded row is now on other cases: the standing still holds, as advice
    assert not any(line.startswith("S33") for line in check.check(cfg))


def test_s33_disagreement_that_exists_only_on_results_from_other_cases_is_advice(cfg):
    from esoi.optimization.leaderboard import case_identity
    set_cascade(cfg, "whole [sample=full | real=no]")
    results = tables.read_csv(cfg.results_path)
    for r in results:
        r["passed"], r["dev"] = ("2", "2/2") if r["impl"] == "shout" else ("0", "0/2")
    tables.write_csv(cfg.results_path, tables.read_header(cfg.results_path), results)
    assert any(line.startswith("S33") for line in check.check(cfg))   # a real disagreement on current cases is still a problem
    path = case_identity.cases_files("greet_a_person", cfg.evaluation)[0]
    path.write_text(path.read_text() + "\n")   # now every result is on other cases: the same finding only informs
    problems, advice = check.check_all(cfg)
    assert not any(line.startswith("S33") for line in problems)
    assert any(line.startswith("S33") and "other cases" in line for line in advice)
