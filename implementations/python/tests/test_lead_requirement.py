"""The lead a cascade stage requires: the grammar, the test statistic, the default, part scoping and the tie-break."""
import datetime
from math import comb

from esoi.optimization.leaderboard import cascade_stages, lead_requirement, stage_standings, stats

TODAY = datetime.date(2026, 11, 12)


def result(impl, passed, cases, cost="1.0", seconds="10", date="2026-11-10", sha="s1", runs=1):
    """A whole-run row of a model arm; a pool of runs carries the summed counts as ``stage_standings.pooled_row`` writes them."""
    found = dict(date=date, component="c", impl=impl, passed=str(passed), cases=str(cases), cost_usd=cost, seconds=seconds, cases_sha="x",
                 git_sha=sha, model_calls="3", tokens_in="0", tokens_out="0", heldout="0/0", sample="", model="m")
    if runs > 1:
        found.update(runs=str(runs), passed_total=str(passed), cases_total=str(cases * runs))
    return found


def fresh(row):
    return ""


def stage(cell):
    found, errors = cascade_stages.parse(f"whole [sample=full | real=yes | {cell}]" if cell else "whole [sample=full | real=yes]")
    assert errors == []
    return found


def decide(cell, rows, incumbent="", parts=None):
    stages = stage(cell)
    standing = stage_standings.standings(stages, {r["impl"]: [r] for r in rows}, TODAY, fresh)
    part_standing = {name: stage_standings.standings(stages, {impl: [r] for impl, r in found.items()}, TODAY, fresh)
                     for name, found in (parts or {}).items()}
    return stage_standings.decide(stages, standing, None, incumbent, part_standing)


# the grammar

def test_the_keys_are_read_into_a_requirement():
    found = stage("lead=margin:0.05+significant:0.05 | lead-on=code:significant:0.1,prose:margin:0.2 | tie-break=cost_usd:low,seconds:low")[0].requirement
    assert [(l.kind, l.value) for l in found.whole] == [("margin", 0.05), ("significant", 0.05)]
    assert [(n, [(l.kind, l.value) for l in ls]) for n, ls in found.parts] == [("code", [("significant", 0.1)]), ("prose", [("margin", 0.2)])]
    assert found.tie_break == (("cost_usd", "low"), ("seconds", "low"))
    assert found.declared and found.part_names == ["code", "prose"]


def test_a_stage_without_the_keys_declares_nothing_and_any_is_the_default():
    assert not stage("")[0].requirement.declared
    assert not stage("lead=any")[0].requirement.declared


def test_a_malformed_requirement_says_what_is_wrong():
    cell = "whole [sample=full | lead=margin:-1+significant:2 | lead-on=Bad:margin:0.1,code:any,kind:margin:0.1,kind:margin:0.2,x | tie-break=price:low,seconds:up]"
    _, errors = cascade_stages.parse(cell)
    text = " ".join(errors)
    for expected in ("margin:-1", "significant:2", "Bad", "code:any", "twice", "not part:requirement", "price:low", "seconds:up"):
        assert expected in text
    assert any("no effect without a lead" in e for e in cascade_stages.parse("whole [tie-break=cost_usd:low]")[1])


# the statistic, against hand-computed values

def test_fisher_25_of_27_against_24_of_27_is_exactly_one():
    # margins 27, 27 and 49 passes: the six tables k=22..27 have 80730, 473850, 1026675, 1026675, 473850, 80730 of C(54, 5) = 3162510 ways,
    # and the table seen (k=25) is among the least likely or equal to the largest, so every table counts and p = 1
    assert sum(comb(27, k) * comb(27, 49 - k) for k in range(22, 28)) == comb(54, 5) == 3162510
    assert stats.fisher_exact_two_sided(25, 27, 24, 27) == 1.0


def test_fisher_9_of_9_against_3_of_9_is_168_over_18564():
    # k=9 and k=3 are the only tables as unlikely as the one seen: each C(9, 9) * C(9, 3) / C(18, 12) = 84 / 18564
    assert comb(18, 12) == 18564
    assert abs(stats.fisher_exact_two_sided(9, 9, 3, 9) - 168 / 18564) < 1e-12


def test_a_significant_lead_needs_a_higher_pass_rate_and_a_p_below_alpha():
    lead = lead_requirement.Lead("significant", 0.05)
    shown, text = lead_requirement.lead_over(lead, result("a", 25, 27), result("b", 24, 27))
    assert (shown, text) == (False, "lead 25/27 vs 24/27 not significant at 0.05")
    assert lead_requirement.lead_over(lead, result("a", 9, 9), result("b", 3, 9))[0] is True
    assert lead_requirement.lead_over(lead, result("a", 3, 9), result("b", 9, 9)) == (False, "lead 3/9 vs 9/9 is not a higher pass rate")


def test_a_pool_counts_every_run_in_the_test():
    pool = result("a", 27, 9, runs=3)   # 27 of 27 pooled
    other = result("b", 18, 9, runs=3)  # 18 of 27 pooled
    assert lead_requirement.counts(pool) == (27, 27)
    assert lead_requirement.lead_over(lead_requirement.Lead("significant", 0.05), pool, other)[0] is True


def test_a_margin_is_an_absolute_difference_in_the_score():
    lead = lead_requirement.Lead("margin", 0.1)
    assert lead_requirement.lead_over(lead, result("a", 8, 10), result("b", 7, 10))[0] is True     # 0.8 - 0.7, within rounding
    assert lead_requirement.lead_over(lead, result("a", 8, 10), result("b", 75, 100))[0] is False


# the decision

def test_default_behaviour_is_unchanged_the_highest_result_wins():
    found = decide("", [result("a", 25, 27), result("b", 24, 27, cost="0.1")], incumbent="b")
    assert (found.winner, found.why, found.required) == ("a", "", False)


def test_a_lead_that_is_shown_lets_the_leader_win():
    found = decide("lead=significant:0.05 | tie-break=cost_usd:low", [result("a", 9, 9, cost="5"), result("b", 3, 9, cost="0.1")], incumbent="b")
    assert found.winner == "a" and found.required and found.contenders == []


def test_without_the_lead_the_cheaper_arm_per_case_wins_and_says_why():
    found = decide("lead=significant:0.05 | tie-break=cost_usd:low", [result("a", 25, 27, cost="5"), result("b", 24, 27, cost="1")], incumbent="a")
    assert found.winner == "b"
    assert found.why == "lead 25/27 vs 24/27 not significant at 0.05; b cheaper per case"
    assert found.contenders == ["a", "b"] and found.leader == "a"


def test_tie_break_is_per_case_and_an_unknown_figure_comes_last():
    rows = [result("a", 25, 27, cost="5"), result("b", 24, 27, cost=""), result("c", 24, 27, cost="2")]
    assert decide("lead=significant:0.05 | tie-break=cost_usd:low", rows).winner == "c"
    assert decide("lead=significant:0.05 | tie-break=seconds:high", [result("a", 25, 27, seconds="5"), result("b", 24, 27, seconds="50")]).winner == "b"
    second = decide("lead=significant:0.05 | tie-break=cost_usd:low,seconds:low", [result("a", 25, 27, cost="1", seconds="9"), result("b", 24, 27, cost="1", seconds="3")])
    assert second.winner == "b"


def test_without_a_tie_break_the_selected_arm_stays_when_the_lead_is_not_shown():
    rows = [result("a", 25, 27), result("b", 24, 27)]
    kept = decide("lead=significant:0.05", rows, incumbent="b")
    assert kept.winner == "b" and kept.why == "lead 25/27 vs 24/27 not significant at 0.05; b stays as the selected arm"
    assert decide("lead=significant:0.05", rows, incumbent="").winner == "a"          # no incumbent among the contenders: the leader
    assert decide("lead=significant:0.05", rows, incumbent="z").winner == "a"


def test_a_margin_requirement_decides_the_same_way():
    rows = [result("a", 9, 10), result("b", 8, 10)]
    assert decide("lead=margin:0.2", rows, incumbent="b").winner == "b"
    assert decide("lead=margin:0.1", rows, incumbent="b").winner == "a"


def test_a_part_carries_its_own_requirement():
    rows = [result("a", 9, 9), result("b", 3, 9)]
    code = {"a": result("a", 5, 6), "b": result("b", 4, 6)}              # not significant on the code cases
    assert decide("lead=significant:0.05", rows, incumbent="b").winner == "a"
    scoped = decide("lead=significant:0.05 | lead-on=code:significant:0.05", rows, incumbent="b", parts={"code": code})
    assert scoped.winner == "b" and scoped.why.startswith("on code: lead 5/6 vs 4/6 not significant at 0.05")
    only_part = decide("lead-on=code:margin:0.1", rows, incumbent="b", parts={"code": {"a": result("a", 6, 6), "b": result("b", 4, 6)}})
    assert only_part.winner == "a"


def test_an_arm_with_no_rows_for_the_part_has_not_shown_its_lead_there():
    found = decide("lead-on=code:margin:0.1", [result("a", 9, 9), result("b", 3, 9)], incumbent="b", parts={"code": {"a": result("a", 6, 6)}})
    assert found.winner == "b" and "no recorded rows for b" in found.why


def test_the_requirement_of_the_stage_the_choice_rests_on_is_the_one_that_applies():
    found, errors = cascade_stages.parse("offline [sample=full | real=no | gate=all-pass | lead=significant:0.05] > whole [sample=full | real=yes]")
    assert errors == []
    rows = {"a": [result("a", 9, 9)], "b": [result("b", 8, 9)]}
    for impl in rows:
        rows[impl][0].update(model_calls="3")
    standing = stage_standings.standings(found, rows, TODAY, fresh)
    assert stage_standings.decide(found, standing, None, "b").winner == "a"      # the latest stage run declares nothing: the highest result


# requires: another component's results gate the stage

def test_requires_is_read_and_a_malformed_one_says_what_is_wrong():
    found = stage("requires=open:0.9,depth:0.8:3,hard::2")[0].requirement
    assert found.requires == (("open", 0.9, 1), ("depth", 0.8, 3), ("hard", None, 2)) and found.declared
    assert any("requires `x:2`" in e for e in cascade_stages.parse("whole [sample=full | requires=x:2]")[1])


def test_an_arm_without_what_a_stage_requires_is_not_selectable_and_a_requirement_nobody_meets_yet_is_skipped():
    stages = stage("requires=depth:0.8:3")
    req = stages[0].requirement
    depth = {"a": result("a", 24, 10, runs=3), "b": result("b", 15, 10, runs=3)}
    assert lead_requirement.unmet(req, "a", {"depth": depth}) == ""
    assert lead_requirement.unmet(req, "b", {"depth": depth}) == "depth pass rate 0.5 is below the floor 0.8"
    assert lead_requirement.unmet(req, "c", {"depth": depth}) == "no counting depth result"
    assert lead_requirement.unmet(req, "c", {"depth": {"a": result("a", 8, 10)}}) == ""     # no arm has three depth runs yet: skipped
    rows = [result("a", 9, 10, cost="5"), result("b", 9, 10, cost="1")]
    standing = stage_standings.standings(stages, {r["impl"]: [r] for r in rows}, TODAY, fresh)
    other = stage_standings.standings(stages, {"a": [result("a", 24, 10, runs=3)]}, TODAY, fresh)
    found = stage_standings.decide(stages, standing, None, "", None, {"depth": other})
    assert found.winner == "a" and any("b is not selectable" in n and "no counting depth result" in n for n in found.notes)
