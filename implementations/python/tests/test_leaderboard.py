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
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "metric_kind": "eval", "selected_by": "hand",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert lb.board(cfg, registry, strict=False, say=lines.append) == 0
    assert any("! b beats the selected a" in line for line in lines) and any("LOSS" in line for line in lines)
    assert lb.board(cfg, registry, strict=True, say=lambda text: None) == 1


def test_invariant_components_are_listed_apart(tmp_path):
    cfg = Config(root=tmp_path)
    (tmp_path / "evaluation" / "components").mkdir(parents=True)
    (tmp_path / "evaluation" / "components" / "results.csv").write_text(
        "date,component,impl,cases,passed,heldout,model_calls,tokens_in,tokens_out,cost_usd,cases_sha\n"
        "2026-01-01,mini,a,10,5,0/0,0,0,0,0.0,x\n2026-01-01,mini,b,10,8,0/0,0,0,0,0.0,x\n")
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "metric_kind": "invariant", "invariant_reason": "A rule.",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert lb.board(cfg, registry, strict=True, say=lines.append) == 0
    assert any(line.startswith("Invariant solutions") or "Invariant solutions" in line for line in lines)


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
    registry = Registry(solutions=[{"solution_id": "s", "selected": "a", "metric_kind": "eval", "selected_by": "hand",
                                    "metric_command": "esoi run mini --impl a"}])
    lines = []
    assert lb.board(cfg, registry, strict=False, say=lines.append) == 0
    text = "\n".join(lines)
    assert "UNMEASURED" in text and "mini (selected: a) UNMEASURED" in text and "WIN:" not in text and "LOSS" not in text and "? b is not comparable with a" in text
    assert lb.board(cfg, registry, strict=True, say=lambda t: None) == 1
