"""Ranking, verdicts, noise margins and arm tags."""
from esoi import leaderboard as lb
from esoi.config import Config
from esoi.registry import Registry


def row(impl, passed, cases=10, cost=0.0, sha="x", **extra):
    base = dict(date="d", component="c", impl=impl, passed=str(passed), cases=str(cases), cost_usd=str(cost), cases_sha=sha,
                model_calls="0", tokens_in="0", tokens_out="0", heldout="0/0")
    return {**base, **extra}


def rows(*items):
    return {r["impl"]: r for r in items}


def test_higher_pass_rate_wins_and_ties_break_on_cost():
    ranked = [r["impl"] for r in lb.rank(rows(row("a", 5), row("b", 6), row("c", 6, cost=0.1)))]
    assert ranked == ["b", "c", "a"]


def test_a_challenger_must_beat_the_selected_outside_the_margin():
    assert [r["impl"] for r in lb.challengers(rows(row("a", 5), row("b", 6)), "a")] == ["b"]
    assert lb.challengers(rows(row("a", 5), row("b", 5)), "a") == []
    assert lb.challengers(rows(row("a", 5), row("b", 9, sha="y")), "a") == []   # other cases are no evidence


def test_verdicts():
    assert lb.verdict(rows(row("a", 6), row("b", 5)), "a")[0] == "WIN"
    assert lb.verdict(rows(row("a", 6, cost=1.0), row("b", 6, cost=1.05)), "a")[0] == "TIE"
    assert lb.verdict(rows(row("a", 5), row("b", 6)), "a")[0] == "LOSS"
    assert lb.verdict(rows(row("a", 6)), "a")[0] == "UNMEASURED"
    assert lb.verdict(rows(row("b", 6)), "a")[0] == "UNMEASURED"


def test_a_sampled_comparison_has_a_wider_margin():
    sampled = rows(row("a", 5, model_calls="3"), row("b", 6, model_calls="3"))
    assert lb.verdict(sampled, "a")[0] == "TIE"
    assert lb.noise(sampled["a"], sampled["b"]) == (lb.SAMPLED_PASS_MARGIN, lb.SAMPLED_SPEND_TOLERANCE)


def test_noise_json_overrides_the_margin(tmp_path):
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "noise.json").write_text('{"pass_margin": 0.5, "spend_tolerance": 0.4}')
    a, b = row("a", 5, model_calls="3"), row("b", 6, model_calls="3")
    assert lb.noise(a, b, tmp_path) == (0.5, 0.4)


def test_ablation_and_validity_arms_are_no_rivals(tmp_path):
    impls = tmp_path / "c" / "impls"
    impls.mkdir(parents=True)
    (impls / "part.py").write_text('"""ABLATION: part of the job."""\n')
    (impls / "check.py").write_text('"""VALIDITY: checks the metric."""\n')
    (impls / "floor.py").write_text('"""FLOOR: the cheap way."""\n')
    data = rows(row("a", 5), row("part", 9), row("check", 9), row("floor", 5))
    assert lb.arm_kind(data["part"], tmp_path) == "ablation" and lb.arm_kind(data["floor"], tmp_path) == "baseline"
    assert lb.challengers(data, "a", tmp_path) == []
    assert lb.verdict(data, "a", tmp_path)[0] in ("TIE", "WIN")


def test_unverified_rows_are_flagged_and_incomparable():
    assert lb.unverified(row("a", 5, sha="")) and not lb.unverified(row("a", 5))
    assert not lb.comparable(row("a", 5, sha=""), row("b", 5))


def test_cases_digest_ignores_line_endings(tmp_path):
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "cases.json").write_bytes(b"[]\r\n")
    first = lb.cases_digest("c", tmp_path)
    (tmp_path / "c" / "cases.json").write_bytes(b"[]\n")
    assert first == lb.cases_digest("c", tmp_path) != "" and lb.cases_digest("none", tmp_path) == ""


def test_latest_results_keeps_the_newest_row(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text("date,component,impl,cases,passed\n2026-01-01,c,a,10,5\n2026-02-01,c,a,10,7\n")
    assert lb.latest_results(path)["c"]["a"]["passed"] == "7"


def test_the_board_prints_a_verdict_and_strict_fails_on_a_challenger(tmp_path):
    cfg = Config(root=tmp_path)
    (tmp_path / "evaluation" / "components").mkdir(parents=True)
    (tmp_path / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,cases_sha\n"
        "2026-01-01,mini,a,10,5,0/0,0,0,0,0.0,x\n2026-01-01,mini,b,10,8,0/0,0,0,0,0.0,x\n")
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "selected_by": "hand",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert lb.board(cfg, registry, strict=False, say=lines.append) == 0
    assert any("! b beats the selected a" in line for line in lines) and any("LOSS" in line for line in lines)
    assert lb.board(cfg, registry, strict=True, say=lambda text: None) == 1


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
    lb.board(cfg, registry, strict=False, say=lines.append)
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
    assert lb.board(cfg, registry, strict=True, say=lines.append) == 0
    assert any("Complementary arms" in line for line in lines)


def test_one_malformed_results_line_does_not_stop_the_board(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text("date,component,impl,cases,passed\n2026-01-01,c,a,2,\n,,,,\n2026-01-01,c,b,x,1\n")
    rows = lb.latest_results(path)
    assert set(rows["c"]) == {"a", "b"}
    assert lb.pass_rate(rows["c"]["a"]) == 0.0 and lb.pass_rate(rows["c"]["b"]) == 1.0


def history(*items):
    out = {}
    for r in items:
        out.setdefault(r["impl"], []).append(r)
    return {impl: sorted(h, key=lambda r: r["date"]) for impl, h in out.items()}


def test_rows_on_different_samples_are_not_compared():
    full = row("a", 458, cases=1137, sample="")
    sampled = row("b", 12, cases=40, sample="sample:40")
    now = rows(full, sampled)
    assert not lb.comparable(full, sampled)
    assert lb.challengers(now, "a") == []
    label, detail = lb.verdict(now, "a")
    assert label == "UNMEASURED" and "40 cases (sample:40)" in detail and "1137 cases" in detail
    # a log recorded before the sample column still tells the two apart by the number of cases
    assert lb.verdict(rows(row("a", 458, cases=1137), row("b", 12, cases=40)), "a")[0] == "UNMEASURED"
    # same count, different selection
    assert not lb.comparable(row("a", 5, sample="sample:10"), row("b", 5, sample="only:A,B"))


def test_each_arm_is_compared_on_the_newest_run_both_have():
    old = dict(date="2026-01-01")
    new = dict(date="2026-02-01")
    hist = history(row("a", 458, cases=1137, **new), row("a", 23, cases=40, sample="sample:40", **old),
                   row("b", 12, cases=40, sample="sample:40", **new))
    latest = {impl: h[-1] for impl, h in hist.items()}
    assert lb.verdict(latest, "a")[0] == "UNMEASURED"   # the latest rows alone share nothing
    label, detail = lb.verdict(latest, "a", history=hist)   # but both ran the 40-case sample: 23 against 12
    assert label == "WIN" and "b" in detail
    assert [r["impl"] for r in lb.challengers(latest, "a", history=hist)] == []
    losing = history(row("a", 5, cases=40, sample="sample:40", **old), row("a", 458, cases=1137, **new),
                     row("b", 12, cases=40, sample="sample:40", **new))
    assert lb.verdict({i: h[-1] for i, h in losing.items()}, "a", history=losing)[0] == "LOSS"


def test_the_board_names_the_mismatch_and_strict_reports_it(tmp_path):
    cfg = Config(root=tmp_path)
    (tmp_path / "evaluation" / "components").mkdir(parents=True)
    (tmp_path / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,cases_sha,sample\n"
        "2026-01-01,mini,a,1137,458,0/0,0,0,0,0.0,x,\n2026-01-01,mini,b,40,12,0/0,0,0,0,0.0,x,sample:40\n")
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "selected_by": "hand",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert lb.board(cfg, registry, strict=False, say=lines.append) == 0
    text = "\n".join(lines)
    assert "UNMEASURED" in text and "mini (selected: a) UNMEASURED" in text and "WIN:" not in text and "LOSS" not in text and "? b is not comparable with a" in text
    assert lb.board(cfg, registry, strict=True, say=lambda t: None) == 1


def test_a_recorded_only_run_does_not_decide_the_default_verdict():
    """Hazard: `esoi run --only ids --record` once made the slice the newest key both arms share, so it decided the verdict."""
    full_a, full_b = row("a", 8, cases=10, date="2026-01-01"), row("b", 5, cases=10, date="2026-01-01")
    only_a = row("a", 0, cases=2, sample="only:X,Y", date="2026-02-01")
    only_b = row("b", 2, cases=2, sample="only:X,Y", date="2026-02-01")
    hist = history(full_a, full_b, only_a, only_b)
    latest = {impl: h[-1] for impl, h in hist.items()}
    assert lb.verdict(latest, "a", history=hist)[0] == "WIN"
    assert lb.challengers(latest, "a", history=hist) == []


def test_a_rival_recorded_only_on_named_cases_is_reported_not_comparable_never_skipped():
    """Hazard: a rival whose rows were all `only:` or `slice:` was dropped without a note (a real results log has such arms)."""
    own = row("a", 8, cases=10, date="2026-01-01")
    rival_only = row("b", 9, cases=2, sample="only:X,Y", date="2026-02-01")
    rival_slice = row("c", 9, cases=3, sample="slice:big", date="2026-02-01")
    hist = history(own, rival_only, rival_slice)
    latest = {impl: h[-1] for impl, h in hist.items()}
    pairs, unmatched = lb.rival_pairs(latest, "a", history=hist)
    assert pairs == [] and [i for i, _ in unmatched] == ["b", "c"]
    assert "not comparable: named cases only" in unmatched[0][1]
    label, detail = lb.verdict(latest, "a", history=hist)
    assert label == "UNMEASURED" and "b scored on only:X,Y only; not comparable: named cases only" in detail
    both = history(own, row("d", 5, cases=10, date="2026-01-01"), rival_only)
    pairs, unmatched = lb.rival_pairs({i: h[-1] for i, h in both.items()}, "a", history=both)
    assert [r["impl"] for _, r in pairs] == ["d"] and [i for i, _ in unmatched] == ["b"]   # compared where it can be, noted where not


def test_a_variant_row_finds_the_arm_kind_of_its_base(tmp_path):
    impls = tmp_path / "c" / "impls"
    impls.mkdir(parents=True)
    (impls / "guard.py").write_text('"""BASELINE: nothing added."""\n')
    assert lb.arm_kind(row("guard@harness=native", 1), tmp_path) == "baseline"


# ---- the statistical rule: paired McNemar, Holm, cost and dependency tie-breaks

def per_case(impl, outcomes, sha="x", component="c", sample=""):
    return [{"component": component, "impl": impl, "cases_sha": sha, "sample": sample, "case_id": f"k{i}", "ok": "1" if ok else "0"}
            for i, ok in enumerate(outcomes)]


def arms(a_ok, b_ok, a_cost=0.0, b_cost=0.0):
    data = rows(row("a", sum(a_ok), len(a_ok), cost=a_cost), row("b", sum(b_ok), len(b_ok), cost=b_cost))
    return data, per_case("a", a_ok) + per_case("b", b_ok)


def test_a_significant_paired_lead_beats_the_selected_arm():
    data, log = arms([True] * 20 + [False] * 20, [True] * 20 + [False] * 8 + [True] * 12 + [False] * 0)
    # b passes 12 cases a misses, a misses none of b's: p = 2/4096
    label, detail = lb.verdict(data, "a", per_case=log)
    assert label == "LOSS" and "paired McNemar test" in detail and "beaten by b" in detail
    assert [r["impl"] for r in lb.challengers(data, "a", per_case=log)] == ["b"]


def test_a_gap_that_chance_explains_is_a_tie_even_where_the_old_margin_would_call_it():
    a = [True] * 21 + [False] * 9
    b = [True] * 17 + [False] * 4 + [False] * 9                 # a passes 4 that b misses, b none: p = 0.125
    data, log = arms(a, b)
    assert lb.verdict(data, "a", per_case=log)[0] == "TIE"   # a passes more but not significantly, costs equal, no dependency info
    assert "dependency information is not available" in lb.verdict(data, "a", per_case=log)[1]
    assert lb.verdict(data, "a")[0] == "WIN"   # without per-case rows the old exact-count rule calls the same data a win


def test_without_per_case_rows_the_old_margin_decides_and_says_so():
    label, detail = lb.verdict(rows(row("a", 5), row("b", 6)), "a")
    assert label == "LOSS"
    assert "fixed pass margin" in lb.verdict(rows(row("a", 6), row("b", 5)), "a")[1]


def test_a_tie_on_quality_goes_to_the_rival_that_costs_over_twenty_percent_less_per_passing_case():
    same = [True] * 15 + [False] * 15
    data, log = arms(same, same, a_cost=1.0, b_cost=0.7)
    label, detail = lb.verdict(data, "a", per_case=log)
    assert label == "LOSS" and "cost per passing case" in detail
    data, log = arms(same, same, a_cost=1.0, b_cost=0.85)   # only 15% cheaper: not enough
    assert lb.verdict(data, "a", per_case=log)[0] == "TIE"
    data, log = arms(same, same, a_cost=0.7, b_cost=1.0)
    assert lb.verdict(data, "a", per_case=log)[0] == "WIN"


def test_equal_cost_falls_to_fewer_dependencies_and_the_incumbent_stays_on_equal_or_unknown():
    same = [True] * 15 + [False] * 15
    data, log = arms(same, same)
    counts = {"a": 3, "b": 1}
    assert lb.verdict(data, "a", per_case=log, dependencies=counts.get)[0] == "LOSS"
    assert lb.verdict(data, "a", per_case=log, dependencies={"a": 1, "b": 3}.get)[0] == "WIN"
    assert lb.verdict(data, "a", per_case=log, dependencies={"a": 2, "b": 2}.get)[0] == "TIE"
    assert lb.verdict(data, "a", per_case=log, dependencies={"a": 2}.get)[0] == "TIE"   # unknown for b: say so, keep the incumbent


def test_fewer_than_thirty_shared_cases_is_labelled_early():
    data, log = arms([True] * 5 + [False] * 5, [True] * 5 + [False] * 5)
    assert "Early result" in lb.verdict(data, "a", per_case=log)[1]
    assert "early" in lb.verdict(rows(row("a", 6), row("b", 5)), "a")[1]
    big, log = arms([True] * 40, [True] * 40)
    assert "Early" not in lb.verdict(big, "a", per_case=log)[1]


def test_holm_adjusts_across_the_rivals_of_the_selected_arm():
    a = [True] * 30 + [False] * 10
    b = list(a)                                                       # b matches a exactly: a tie
    c = [True] * 22 + [False] * 8 + [False] * 10                      # a passes 8 c misses
    data = rows(row("a", 30, 40), row("b", 30, 40), row("c", 22, 40))
    log = per_case("a", a) + per_case("b", b) + per_case("c", c)
    found = {d.rival: d for d in lb.decisions(data, "a", per_case=log)}
    assert found["c"].outcome == "incumbent" and found["c"].adjusted is not None
    assert found["c"].adjusted >= found["c"].paired.p_value


def test_a_per_case_log_from_another_run_is_not_used():
    data, log = arms([True] * 30, [True] * 29 + [False])
    data["b"]["passed"] = "30"   # the results row no longer matches the logged outcomes
    assert lb.case_outcomes(log, data["b"]) is None
    assert "fixed pass margin" in lb.verdict(data, "a", per_case=log)[1]


def test_noise_json_still_decides_the_fallback(tmp_path):
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "noise.json").write_text('{"pass_margin": 0.5, "spend_tolerance": 0.4}')
    sampled = rows(row("a", 5, model_calls="3"), row("b", 9, model_calls="3"))
    assert lb.verdict(sampled, "a", tmp_path)[0] == "TIE"


def test_dependency_counter_reads_uses_and_the_declared_extra_count():
    registry = Registry(implementations=[
        {"implementation_id": "s:a", "solution_id": "s", "uses_solution_ids": "x;y"},
        {"implementation_id": "s:b", "solution_id": "s", "uses_solution_ids": "", "extra_dependencies": "2"},
        {"implementation_id": "s:c", "solution_id": "s"}])
    count = lb.dependency_counter(registry, "s")
    assert (count("a"), count("b"), count("c"), count("zzz")) == (2, 2, None, None)
