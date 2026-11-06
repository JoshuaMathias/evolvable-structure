"""Ranking, verdicts, noise margins and arm tags."""
import pytest

from esoi.optimization.leaderboard import arm_kinds, board_report, case_identity, held_out_parts, ranking, results_log, rival_decisions, rival_pairing, switching_policy, verdict_labels
from esoi.optimization.leaderboard import stats
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import Registry


def row(impl, passed, cases=10, cost=0.0, sha="x", **extra):
    base = dict(date="d", component="c", impl=impl, passed=str(passed), cases=str(cases), cost_usd=str(cost), cases_sha=sha,
                model_calls="0", tokens_in="0", tokens_out="0", heldout="0/0")
    return {**base, **extra}


def rows(*items):
    return {r["impl"]: r for r in items}


def test_higher_pass_rate_wins_and_ties_break_on_cost():
    ranked = [r["impl"] for r in ranking.rank(rows(row("a", 5), row("b", 6), row("c", 6, cost=0.1)))]
    assert ranked == ["b", "c", "a"]


def test_the_highest_result_is_the_challenger_significant_or_not_and_equal_keeps_the_selected_arm():
    assert [r["impl"] for r in rival_decisions.challengers(rows(row("a", 5), row("b", 10)), "a")] == ["b"]
    assert [r["impl"] for r in rival_decisions.challengers(rows(row("a", 5), row("b", 6)), "a")] == ["b"]   # a gap of one case in ten is a best guess, still ahead
    assert rival_decisions.challengers(rows(row("a", 5), row("b", 6)), "a", policy=switching_policy.Policy(require_significance=True)) == []
    assert rival_decisions.challengers(rows(row("a", 5), row("b", 5)), "a") == []
    assert rival_decisions.challengers(rows(row("a", 5), row("b", 9, sha="y")), "a") == []   # other cases are no evidence


def test_verdicts():
    assert verdict_labels.verdict(rows(row("a", 10), row("b", 5)), "a")[0] == "WIN"
    assert verdict_labels.verdict(rows(row("a", 6, cost=1.0), row("b", 6, cost=1.05)), "a")[0] == "TIE"
    assert verdict_labels.verdict(rows(row("a", 5), row("b", 10)), "a")[0] == "LOSS"
    assert verdict_labels.verdict(rows(row("a", 5), row("b", 6)), "a")[0] == "LOSS"
    assert verdict_labels.verdict(rows(row("a", 5), row("b", 6)), "a", policy=switching_policy.Policy(require_significance=True))[0] == "TIE"
    assert verdict_labels.verdict(rows(row("a", 6)), "a")[0] == "UNMEASURED"
    assert verdict_labels.verdict(rows(row("b", 6)), "a")[0] == "UNMEASURED"


def test_ablation_and_validity_arms_are_no_rivals(tmp_path):
    impls = tmp_path / "c" / "impls"
    impls.mkdir(parents=True)
    (impls / "part.py").write_text('"""ABLATION: part of the job."""\n')
    (impls / "check.py").write_text('"""VALIDITY: checks the metric."""\n')
    (impls / "floor.py").write_text('"""FLOOR: the cheap way."""\n')
    data = rows(row("a", 5), row("part", 9), row("check", 9), row("floor", 5))
    assert arm_kinds.arm_kind(data["part"], tmp_path) == "ablation" and arm_kinds.arm_kind(data["floor"], tmp_path) == ""   # no baseline mark: it competes
    assert rival_decisions.challengers(data, "a", tmp_path) == []
    assert verdict_labels.verdict(data, "a", tmp_path)[0] in ("TIE", "WIN")


def test_unverified_rows_are_flagged_and_incomparable():
    assert case_identity.unverified(row("a", 5, sha="")) and not case_identity.unverified(row("a", 5))
    assert not case_identity.comparable(row("a", 5, sha=""), row("b", 5))


def test_cases_digest_ignores_line_endings(tmp_path):
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "cases.json").write_bytes(b"[]\r\n")
    first = case_identity.cases_digest("c", tmp_path)
    (tmp_path / "c" / "cases.json").write_bytes(b"[]\n")
    assert first == case_identity.cases_digest("c", tmp_path) != "" and case_identity.cases_digest("none", tmp_path) == ""


def test_cases_digest_publishes_case_sources_first_so_every_caller_agrees(tmp_path):
    (tmp_path / "c" / "datasets").mkdir(parents=True)
    (tmp_path / "c" / "cases.json").write_text("[]")
    sources = tmp_path / "c" / "datasets" / "sources.json"
    sources.write_text("absent")
    (tmp_path / "c" / "case_sources.py").write_text(
        f"from pathlib import Path\n\ndef publish():\n    Path({str(sources)!r}).write_text('present')\n")
    digest = case_identity.cases_digest("c", tmp_path)
    assert sources.read_text() == "present" and digest == case_identity.cases_digest("c", tmp_path)


def test_latest_results_keeps_the_newest_row(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text("date,component,impl,cases,passed\n2026-01-01,c,a,10,5\n2026-02-01,c,a,10,7\n")
    assert results_log.latest_results(path)["c"]["a"]["passed"] == "7"


def test_the_board_prints_a_verdict_and_strict_fails_on_a_challenger(tmp_path):
    cfg = Config(root=tmp_path)
    (tmp_path / "evaluation" / "components").mkdir(parents=True)
    (tmp_path / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,cases_sha\n"
        "2026-01-01,mini,a,10,5,0/0,0,0,0,0.0,x\n2026-01-01,mini,b,10,10,0/0,0,0,0,0.0,x\n")
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "selected_by": "hand",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert board_report.board(cfg, registry, strict=False, say=lines.append) == 0
    assert any("! b should replace the selected a" in line for line in lines) and any("LOSS" in line for line in lines)
    assert board_report.board(cfg, registry, strict=True, say=lambda text: None) == 1


def test_the_board_shows_the_rows_a_verdict_compared_when_they_are_not_the_latest(tmp_path):
    cfg = Config(root=tmp_path)
    (tmp_path / "evaluation" / "components").mkdir(parents=True)
    (tmp_path / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,cases_sha,sample\n"
        "2026-01-01,mini,a,40,23,0/0,0,0,0,0.0,x,sample:40\n2026-01-01,mini,b,40,12,0/0,0,0,0,0.0,x,sample:40\n"
        "2026-02-01,mini,a,1137,458,0/0,0,0,0,0.0,x,\n")
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "selected_by": "hand",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    board_report.board(cfg, registry, strict=False, say=lines.append)
    assert any("= compared on 40 cases (sample:40)" in line and "a 23/40" in line and "b 12/40" in line
               for line in lines)


def test_complementary_arms_are_listed_apart(tmp_path):
    cfg = Config(root=tmp_path)
    (tmp_path / "evaluation" / "components" / "mini").mkdir(parents=True)
    (tmp_path / "evaluation" / "components" / "mini" / "invariant.txt").write_text("The arms cover different cases.\n")
    (tmp_path / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,cases_sha\n"
        "2026-01-01,mini,a,10,5,0/0,0,0,0,0.0,x\n2026-01-01,mini,b,10,8,0/0,0,0,0,0.0,x\n")
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert board_report.board(cfg, registry, strict=True, say=lines.append) == 0
    assert any("Complementary arms" in line for line in lines)


def test_one_malformed_results_line_does_not_stop_the_board(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text("date,component,impl,cases,passed\n2026-01-01,c,a,2,\n,,,,\n2026-01-01,c,b,x,1\n")
    rows = results_log.latest_results(path)
    assert set(rows["c"]) == {"a", "b"}
    assert ranking.pass_rate(rows["c"]["a"]) == 0.0 and ranking.pass_rate(rows["c"]["b"]) == 1.0


def history(*items):
    out = {}
    for r in items:
        out.setdefault(r["impl"], []).append(r)
    return {impl: sorted(h, key=lambda r: r["date"]) for impl, h in out.items()}


def test_rows_on_different_samples_are_not_compared():
    full = row("a", 458, cases=1137, sample="")
    sampled = row("b", 12, cases=40, sample="sample:40")
    now = rows(full, sampled)
    assert not case_identity.comparable(full, sampled)
    assert rival_decisions.challengers(now, "a") == []
    label, detail = verdict_labels.verdict(now, "a")
    assert label == "UNMEASURED" and "40 cases (sample:40)" in detail and "1137 cases" in detail
    # a log recorded before the sample column still tells the two apart by the number of cases
    assert verdict_labels.verdict(rows(row("a", 458, cases=1137), row("b", 12, cases=40)), "a")[0] == "UNMEASURED"
    # same count, different selection
    assert not case_identity.comparable(row("a", 5, sample="sample:10"), row("b", 5, sample="only:A,B"))


def test_each_arm_is_compared_on_the_newest_run_both_have():
    old = dict(date="2026-01-01")
    new = dict(date="2026-02-01")
    hist = history(row("a", 458, cases=1137, **new), row("a", 23, cases=40, sample="sample:40", **old),
                   row("b", 12, cases=40, sample="sample:40", **new))
    latest = {impl: h[-1] for impl, h in hist.items()}
    assert verdict_labels.verdict(latest, "a")[0] == "UNMEASURED"   # the latest rows alone share nothing
    label, detail = verdict_labels.verdict(latest, "a", history=hist)   # but both ran the 40-case sample: 23 against 12
    assert label == "WIN" and "b" in detail
    assert [r["impl"] for r in rival_decisions.challengers(latest, "a", history=hist)] == []
    losing = history(row("a", 5, cases=40, sample="sample:40", **old), row("a", 458, cases=1137, **new),
                     row("b", 12, cases=40, sample="sample:40", **new))
    assert verdict_labels.verdict({i: h[-1] for i, h in losing.items()}, "a", history=losing)[0] == "LOSS"


def test_the_board_names_the_mismatch_and_strict_reports_it(tmp_path):
    cfg = Config(root=tmp_path)
    (tmp_path / "evaluation" / "components").mkdir(parents=True)
    (tmp_path / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,cases_sha,sample\n"
        "2026-01-01,mini,a,1137,458,0/0,0,0,0,0.0,x,\n2026-01-01,mini,b,40,12,0/0,0,0,0,0.0,x,sample:40\n")
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "selected_by": "hand",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert board_report.board(cfg, registry, strict=False, say=lines.append) == 0
    text = "\n".join(lines)
    assert "UNMEASURED" in text and "mini (selected: a) UNMEASURED" in text and "WIN:" not in text and "LOSS" not in text and "? b is not comparable with a" in text
    assert board_report.board(cfg, registry, strict=True, say=lambda t: None) == 1


def test_a_recorded_only_run_does_not_decide_the_default_verdict():
    """Hazard: `esoi run --only ids --record` once made the slice the newest key both arms share, so it decided the verdict."""
    full_a, full_b = row("a", 10, cases=10, date="2026-01-01"), row("b", 5, cases=10, date="2026-01-01")
    only_a = row("a", 0, cases=2, sample="only:X,Y", date="2026-02-01")
    only_b = row("b", 2, cases=2, sample="only:X,Y", date="2026-02-01")
    hist = history(full_a, full_b, only_a, only_b)
    latest = {impl: h[-1] for impl, h in hist.items()}
    assert verdict_labels.verdict(latest, "a", history=hist)[0] == "WIN"
    assert rival_decisions.challengers(latest, "a", history=hist) == []


def test_a_rival_recorded_only_on_named_cases_is_reported_not_comparable_never_skipped():
    """Hazard: a rival whose rows were all `only:` or `slice:` was dropped without a note (a real results log has such arms)."""
    own = row("a", 8, cases=10, date="2026-01-01")
    rival_only = row("b", 9, cases=2, sample="only:X,Y", date="2026-02-01")
    rival_slice = row("c", 9, cases=3, sample="slice:big", date="2026-02-01")
    hist = history(own, rival_only, rival_slice)
    latest = {impl: h[-1] for impl, h in hist.items()}
    pairs, unmatched = rival_pairing.rival_pairs(latest, "a", history=hist)
    assert pairs == [] and [i for i, _ in unmatched] == ["b", "c"]
    assert "not comparable: named cases only" in unmatched[0][1]
    label, detail = verdict_labels.verdict(latest, "a", history=hist)
    assert label == "UNMEASURED" and "b scored on only:X,Y only; not comparable: named cases only" in detail
    both = history(own, row("d", 5, cases=10, date="2026-01-01"), rival_only)
    pairs, unmatched = rival_pairing.rival_pairs({i: h[-1] for i, h in both.items()}, "a", history=both)
    assert [r["impl"] for _, r in pairs] == ["d"] and [i for i, _ in unmatched] == ["b"]   # compared where it can be, noted where not


def test_a_variant_row_finds_the_arm_kind_of_its_base(tmp_path):
    impls = tmp_path / "c" / "impls"
    impls.mkdir(parents=True)
    (impls / "guard.py").write_text('"""ABLATION: nothing added."""\n')
    assert arm_kinds.arm_kind(row("guard@harness=native", 1), tmp_path) == "ablation"


# ---- the rule: a significant two-sided paired test, else the selected arm stays; a best guess where no test is possible

def per_case(impl, outcomes, sha="x", component="c", sample="", scores=None):
    return [{"component": component, "impl": impl, "cases_sha": sha, "sample": sample, "case_id": f"k{i}", "ok": "1" if ok else "0",
             "score": "" if scores is None else str(scores[i])} for i, ok in enumerate(outcomes)]


def arms(a_ok, b_ok):
    data = rows(row("a", sum(a_ok), len(a_ok)), row("b", sum(b_ok), len(b_ok)))
    return data, per_case("a", a_ok) + per_case("b", b_ok)


def test_a_significant_paired_gain_replaces_the_selected_arm():
    data, log = arms([True] * 20 + [False] * 20, [True] * 20 + [False] * 8 + [True] * 12)   # b alone passes 12 cases, a alone none
    label, detail = verdict_labels.verdict(data, "a", per_case=log)
    assert label == "LOSS" and "b is better than a" in detail and "12 of 40 cases disagree" in detail and "exact McNemar" in detail
    assert [r["impl"] for r in rival_decisions.challengers(data, "a", per_case=log)] == ["b"]
    found = rival_decisions.decisions(data, "a", per_case=log)[0]
    assert found.basis == "significance" and found.p == pytest.approx(1 / 2048) and found.switch


def test_a_lead_chance_could_explain_still_wins_by_default_and_says_it_is_a_best_guess():
    data, log = arms([True] * 21 + [False] * 9, [True] * 17 + [False] * 13)   # a alone passes 4, b alone none: a leads
    found = rival_decisions.decisions(data, "a", per_case=log)[0]
    assert found.outcome == "incumbent" and not found.significant and "best guess, not yet significant" in found.text
    data, log = arms([True] * 17 + [False] * 13, [True] * 21 + [False] * 9)   # b alone passes 4: two-sided p = 0.125, above 0.05
    label, detail = verdict_labels.verdict(data, "a", per_case=log)
    assert label == "LOSS" and "best guess, not yet significant" in detail and "p=0.125" in detail and "4 of 30 cases disagree" in detail
    assert [r["impl"] for r in rival_decisions.challengers(data, "a", per_case=log)] == ["b"]


def test_require_significance_keeps_the_selected_arm_until_the_lead_is_significant():
    data, log = arms([True] * 17 + [False] * 13, [True] * 21 + [False] * 9)
    strict = switching_policy.Policy(require_significance=True)
    label, detail = verdict_labels.verdict(data, "a", per_case=log, policy=strict)
    assert label == "TIE" and "is not shown better than a (p=0.125, 4 of 30 cases disagree); more cases would settle it" in detail
    assert rival_decisions.challengers(data, "a", per_case=log, policy=strict) == []


def test_the_selected_arm_is_a_win_when_it_is_ahead_and_says_if_shown():
    data, log = arms([True] * 30 + [False] * 10, [True] * 18 + [False] * 22)
    label, detail = verdict_labels.verdict(data, "a", per_case=log)
    assert label == "WIN" and "a is better than b" in detail


def test_equal_arms_are_a_tie_whatever_they_cost():
    same = [True] * 15 + [False] * 15
    data = rows(row("a", 15, 30, cost=1.0), row("b", 15, 30, cost=0.1))
    log = per_case("a", same) + per_case("b", same)
    label, detail = verdict_labels.verdict(data, "a", per_case=log)
    assert label == "TIE" and "exactly equal" in detail   # cost counts only inside the metric; equal keeps the incumbent


def test_holm_adjusts_across_the_rivals_of_the_selected_arm():
    a = [False] * 40
    b = [True] * 6 + [False] * 34     # two-sided p = 1/32 alone
    c = [True] * 6 + [False] * 34
    data = rows(row("a", 0, 40), row("b", 6, 40), row("c", 6, 40))
    log = per_case("a", a) + per_case("b", b) + per_case("c", c)
    found = {d.rival: d for d in rival_decisions.decisions(data, "a", per_case=log)}
    assert found["b"].p == pytest.approx(2 / 32) and not found["b"].significant   # 0.031 alone, 0.0625 after Holm over two rivals
    assert found["b"].outcome == "rival" and found["b"].switch   # still ahead, so it wins as a best guess
    assert rival_decisions.decisions(data, "a", per_case=log, policy=switching_policy.Policy(require_significance=True))[0].outcome == "tie"
    lone = rows(row("a", 0, 40), row("b", 6, 40))
    assert rival_decisions.decisions(lone, "a", per_case=per_case("a", a) + per_case("b", b))[0].significant


def test_a_per_case_log_from_another_run_is_not_used():
    data, log = arms([True] * 30, [True] * 29 + [False])
    data["b"]["passed"] = "28"   # the results row no longer matches the logged outcomes
    assert held_out_parts.case_outcomes(log, data["b"]) is None
    found = rival_decisions.decisions(data, "a", per_case=log)[0]   # without matching per-case rows the pass counts still allow Fisher's exact test
    assert found.basis == "significance" and "Fisher" in found.text


def test_a_balanced_metric_is_tested_with_an_exact_sign_test_on_per_case_scores():
    a = row("a", 20, 20, balanced="0.80")
    b = row("b", 20, 20, balanced="0.85")
    ok = [True] * 20
    log = per_case("a", ok, scores=[0.80] * 20) + per_case("b", ok, scores=[0.80] * 4 + [0.85] * 16)   # same passes, b cheaper in 16
    found = rival_decisions.decisions(rows(a, b), "a", per_case=log)[0]
    assert found.basis == "significance" and found.outcome == "rival" and "sign test" in found.text and found.p == pytest.approx(2 * 0.5 ** 16)
    nothing = rival_decisions.decisions(rows(a, b), "a", per_case=per_case("a", ok) + per_case("b", ok))[0]   # no per-case scores recorded
    assert nothing.basis == "best guess"


def test_aggregate_pass_counts_on_the_same_cases_get_fishers_exact_test():
    data = rows(row("a", 10, 40), row("b", 22, 40))
    found = rival_decisions.decisions(data, "a")[0]
    assert found.basis == "significance" and found.outcome == "rival" and "exact Fisher test" in found.text and found.switch
    assert found.p == pytest.approx(stats.fisher_exact_two_sided(22, 40, 10, 40))
    label, detail = verdict_labels.verdict(rows(row("a", 20, 40), row("b", 24, 40)), "a")
    assert label == "LOSS" and "best guess, not yet significant" in detail   # ahead by 4 of 40, not significant: still the best guess
    assert verdict_labels.verdict(rows(row("a", 20, 40), row("b", 24, 40)), "a", policy=switching_policy.Policy(require_significance=True))[0] == "TIE"
    assert rival_decisions.decisions(rows(row("a", 20, 40), row("b", 24, 40, sha="")), "a") == []   # an unverified row is no comparison


def test_a_best_guess_is_for_figures_a_test_cannot_use_and_stays_only_if_significance_is_required():
    data = rows(row("a", 5, balanced="0.50"), row("b", 6, balanced="0.60"))   # an aggregate balanced score has no case counts to test
    label, detail = verdict_labels.verdict(data, "a")
    assert label == "LOSS" and "best guess" in detail and "allow a test" in detail
    assert rival_decisions.challengers(data, "a") != []
    off = switching_policy.Policy(require_significance=True)
    label, detail = verdict_labels.verdict(data, "a", policy=off)
    assert label == "TIE" and "requires significance" in detail and rival_decisions.challengers(data, "a", policy=off) == []
    assert verdict_labels.verdict(rows(row("a", 6, balanced="0.60"), row("b", 5, balanced="0.50")), "a")[0] == "WIN"
    label, detail = verdict_labels.verdict(rows(row("a", 6, cost=1.0, balanced="0.6"), row("b", 6, cost=0.1, balanced="0.6")), "a")
    assert label == "TIE" and "exactly equal" in detail   # equal estimates keep the incumbent, whatever the cost


def test_best_guess_selects_the_best_point_estimate_or_nothing_on_an_exact_tie():
    assert rival_decisions.best_guess(rows(row("a", 5), row("b", 7), row("c", 6)))[0] == "b"
    arm, why = rival_decisions.best_guess(rows(row("a", 6), row("b", 6)))
    assert arm is None and "tie" in why and "nothing is selected" in why
    assert "best guess" in verdict_labels.verdict(rows(row("b", 6), row("c", 4)), "a")[1]   # selected arm has no row: the best guess is named


def test_policy_only_gets_stricter_and_a_solution_overrides_the_project(tmp_path):
    cfg = Config(root=tmp_path, switching={"alpha": 0.02, "min_cases": 20, "s": {"alpha": 0.01}, "t": {"alpha": 0.2, "min_cases": -3}})
    s = switching_policy.policy_for(cfg, "s", "c", [])
    assert (s.alpha, s.min_cases, s.source("alpha"), s.source("min_cases")) == (0.01, 20, "solution", "project")
    t = switching_policy.policy_for(cfg, "t", "c", [])
    assert (t.alpha, t.min_cases) == (0.05, 0)   # looser than the library default is read as the default
    assert switching_policy.policy_for(Config(root=tmp_path), "s", "c", []) == switching_policy.Policy()
    assert not s.require_significance
    strict = Config(root=tmp_path, switching={"s": {"require_significance": True}, "t": {"best_guess_switch": False}, "u": {"best_guess_switch": True}})
    assert switching_policy.policy_for(strict, "s").require_significance and switching_policy.policy_for(strict, "s").source("require_significance") == "solution"
    assert switching_policy.policy_for(strict, "t").require_significance   # the deprecated alias of require_significance = true
    assert not switching_policy.policy_for(strict, "u").require_significance   # true cannot be looser than the default


def test_with_require_significance_a_stricter_alpha_or_minimum_of_cases_keeps_the_selected_arm_and_names_the_requirement(tmp_path):
    data, log = arms([True] * 20 + [False] * 20, [True] * 20 + [False] * 8 + [True] * 12)   # p = 1/4096
    strict = Config(root=tmp_path, switching={"s": {"alpha": 0.0001, "require_significance": True}})
    label, detail = verdict_labels.verdict(data, "a", per_case=log, policy=switching_policy.policy_for(strict, "s", "c", log))
    assert label == "TIE" and "significant at alpha 0.05 but the solution requires alpha 0.0001" in detail
    few = Config(root=tmp_path, switching={"min_cases": 50, "require_significance": True})
    label, detail = verdict_labels.verdict(data, "a", per_case=log, policy=switching_policy.policy_for(few, "s", "c", log))
    assert label == "TIE" and "the project requires at least 50 shared cases and there are 40" in detail


def test_alpha_and_min_cases_alone_only_change_what_counts_as_significant(tmp_path):
    data, log = arms([True] * 20 + [False] * 20, [True] * 20 + [False] * 8 + [True] * 12)
    found = rival_decisions.decisions(data, "a", per_case=log, policy=switching_policy.Policy(alpha=0.0001))[0]
    assert found.switch and not found.significant and "best guess, not yet significant" in found.text
