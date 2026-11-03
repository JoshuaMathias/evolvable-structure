"""Claims on held-out cases, two-sided tests, alpha shared across looks, and promotion that never rewrites a metric command."""
import pytest

from esoi import leaderboard as lb
from esoi import stats, tables
from test_cascade import set_cascade


def row(impl, outcomes, sample="", sha="x"):
    return dict(date="d", component="c", impl=impl, passed=str(sum(outcomes)), cases=str(len(outcomes)), cost_usd="0", cases_sha=sha,
                sample=sample, model_calls="0", tokens_in="0", tokens_out="0", heldout="0/0")


def log(impl, outcomes, sample="", sha="x"):
    return [{"component": "c", "impl": impl, "cases_sha": sha, "sample": sample, "case_id": f"k{i}", "ok": "1" if ok else "0", "score": ""}
            for i, ok in enumerate(outcomes)]


def test_two_sided_fisher_is_twice_the_one_sided_tail_when_symmetric():
    assert stats.fisher_exact_two_sided(8, 10, 2, 10) == pytest.approx(2 * stats.fisher_exact_greater(8, 10, 2, 10))
    assert stats.fisher_exact_two_sided(5, 10, 5, 10) == 1.0


def test_alpha_is_divided_by_the_looks_and_the_split_is_stable():
    assert stats.bonferroni_alpha(0.05, 3) == pytest.approx(0.05 / 3) and stats.bonferroni_alpha(0.05, 0) == 0.05
    ids = [f"k{i}" for i in range(500)]
    selection, held = stats.split_cases(ids, 0.3)
    assert sorted(selection + held) == sorted(ids) and 110 < len(held) < 190
    again = stats.split_cases(ids + ["new"], 0.3)[1]
    assert [c for c in again if c != "new"] == held   # adding cases never moves an old case
    assert stats.split_cases(ids, 0.0)[1] == []


def concentrated(fraction):
    """60 cases where arm b alone passes 10 cases of the selection part and 1 of the held-out part; arm a passes nothing b misses."""
    ids = [f"k{i}" for i in range(60)]
    selection, held = stats.split_cases(ids, fraction)
    wins = set(selection[:10]) | set(held[:1])
    a = [False] * 60
    b = [f"k{i}" in wins for i in range(60)]
    return a, b


def test_in_sample_significant_but_held_out_is_not():
    a, b = concentrated(0.3)
    data = {"a": row("a", a), "b": row("b", b)}
    every = log("a", a) + log("b", b)
    whole = lb.decisions(data, "a", per_case=every)[0]
    assert whole.significant and whole.p < 0.05                      # in sample the lead looks real
    held = lb.decisions(data, "a", per_case=every, policy=lb.Policy(holdout=0.3))[0]
    assert not held.significant and held.p > 0.05 and held.outcome == "rival"
    assert "best guess, not yet significant" in held.text and "1 of " in held.text   # one case of the held-out part disagrees
    assert held.other["part"] == "heldout" and int(held.other["cases"]) < 30


def test_the_claim_is_two_sided_and_holm_adjusted():
    a = [False] * 40
    b = [True] * 5 + [False] * 35
    found = lb.decisions({"a": row("a", a), "b": row("b", b)}, "a", per_case=log("a", a) + log("b", b))[0]
    assert found.p == pytest.approx(2 / 32) and not found.significant   # one-sided it would be 1/32 and pass


def test_a_claim_at_one_of_several_looks_spends_a_share_of_alpha():
    a = [False] * 40
    b = [True] * 6 + [False] * 34                                       # two-sided p = 1/32 = 0.031
    history = {"a": [row("a", a[:3], "sample:3"), row("a", a[:10], "sample:10"), row("a", a)],
               "b": [row("b", b[:3], "sample:3"), row("b", b[:10], "sample:10"), row("b", b)]}
    every = log("a", a) + log("b", b)
    alone = lb.decisions({"a": history["a"][-1], "b": history["b"][-1]}, "a", per_case=every)[0]
    assert alone.significant
    looked = lb.decisions({"a": history["a"][-1], "b": history["b"][-1]}, "a", history=history, per_case=every)[0]
    assert not looked.significant and "one of 3 looks" in looked.text


def test_holdout_is_read_from_the_selection_table_and_is_not_a_solution_choice(cfg):
    import dataclasses
    held = dataclasses.replace(cfg, selection={"holdout": 0.3})
    assert lb.holdout_fraction(held) == 0.3 and held.selection_choices == {}
    assert lb.holdout_fraction(cfg) == 0.0


def test_promotion_changes_selected_and_never_the_metric_command(cfg):
    from esoi import promote, registry
    set_cascade(cfg, "whole [sample=full | real=no]")
    metrics_before = (cfg.structure / "metrics.csv").read_bytes()
    results, header = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in results:
        r.update(cases="40", passed="40", dev="40/40") if r["impl"] == "shout" else r.update(cases="40", passed="20", dev="20/40")
    tables.write_csv(cfg.results_path, header, results)
    loaded = registry.load(cfg)
    [proposal] = promote.propose(cfg, loaded, stale=lambda c, comp, row, strict: "")
    assert proposal.winner == "shout" and not any(edit.startswith("metrics.csv") for edit in proposal.edits)
    promote.apply(cfg, loaded, proposal)
    assert (cfg.structure / "metrics.csv").read_bytes() == metrics_before
    again = registry.load(cfg)
    solution = next(s for s in again.solutions if s["solution_id"] == proposal.solution_id)
    assert lb.selected_arm(cfg, solution, "", again)[1] == "shout"
