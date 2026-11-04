"""Rules S41, S42, S44 and S45 (a cascade runs one criterion; no arm is excluded by a mark). All advisory, none calls a model."""
import subprocess
from pathlib import Path

from esoi import check, config, leaderboard, promote, tables
from esoi.rules import one_criterion


def context(root):
    return check.build_context(config.load(root), False, None)


def with_metrics(ctx, *rows):
    ctx.registry.metrics = [dict({"metric_id": "", "solution_ids": "", "command": "", "cascading_conditionals": ""}, **r) for r in rows]
    return ctx


CASCADE = "free [sample=full | real=no | gate=all-pass] > live [sample=full | real=yes]"


def test_a_cascade_whose_command_scores_two_components_is_advice(repo):
    ctx = with_metrics(context(repo), {"metric_id": "m-both", "solution_ids": "s", "cascading_conditionals": CASCADE,
                                       "command": "esoi run files --impl a; esoi run topics --impl a"})
    found = one_criterion.single_number(ctx)
    assert len(found) == 1 and found[0].startswith("S41 m-both") and "same number at rising fidelity" in found[0] and "files, topics" in found[0]


def test_one_component_or_one_stage_is_not_advice(repo):
    ctx = with_metrics(context(repo),
                       {"metric_id": "one", "cascading_conditionals": CASCADE, "command": "esoi run files --impl a; esoi run files --impl b"},
                       {"metric_id": "flat", "cascading_conditionals": "", "command": "esoi run files --impl a; esoi run topics --impl a"})
    assert one_criterion.single_number(ctx) == []


def test_a_waiver_excuses_the_metric(repo):
    ctx = with_metrics(context(repo), {"metric_id": "m-both", "cascading_conditionals": CASCADE,
                                       "command": "esoi run files --impl a; esoi run topics --impl a"})
    ctx.registry.waivers = [{"rule": "S41", "path": "m-both", "reason": "two products"}]
    assert one_criterion.single_number(ctx) == []


def row(impl, **more):
    return dict({"impl": impl, "component": "", "date": "2026-11-01", "passed": "1", "cases": "2"}, **more)


def test_two_metrics_ranking_the_same_arms_are_separate_leaderboards(repo):
    ctx = with_metrics(context(repo),
                       {"metric_id": "m-files", "solution_ids": "s", "command": "esoi run files --impl a; esoi run files --impl b"},
                       {"metric_id": "m-topics", "solution_ids": "s", "command": "esoi run topics --impl a; esoi run topics --impl b"})
    ctx.registry.solutions = [{"solution_id": "s", "metric_ids": "m-files;m-topics", "authoritative_metric_id": "m-files"}]
    ctx.registry.solution_order = ["s"]
    ctx.history = {c: {i: [row(i, component=c)] for i in "ab"} for c in ("files", "topics")}
    found = one_criterion.separate_leaderboards(ctx)
    assert len(found) == 1 and found[0].startswith("S42 s") and "m-files is authoritative" in found[0] and "case sources" in found[0]
    ctx.history["topics"] = {}   # no recorded result for one of them: not two leaderboards
    assert one_criterion.separate_leaderboards(ctx) == []


def test_metrics_over_different_arms_are_not_advice(repo):
    ctx = with_metrics(context(repo),
                       {"metric_id": "m1", "solution_ids": "s", "command": "esoi run files --impl a; esoi run files --impl b"},
                       {"metric_id": "m2", "solution_ids": "s", "command": "esoi run topics --impl c; esoi run topics --impl d"})
    ctx.registry.solutions = [{"solution_id": "s", "metric_ids": "m1;m2"}]
    ctx.registry.solution_order = ["s"]
    ctx.history = {"files": {i: [row(i)] for i in "ab"}, "topics": {i: [row(i)] for i in "cd"}}
    assert one_criterion.separate_leaderboards(ctx) == []


def diagnostic_ctx(repo, table, history_rows):
    ctx = context(repo)
    ctx.config.balance = {"files": table}
    ctx.history = {"files": {impl: [row(impl, component="files", **extra)] for impl, extra in history_rows.items()}}
    return ctx


def test_a_best_scoring_arm_outside_the_declared_diagnostics_is_advice_and_is_not_excluded(repo):
    table = {"diagnostics": {"cards": {"min": 50}}}
    ctx = diagnostic_ctx(repo, table, {"one_per_file": {"passed": "10", "details": "cards=2000"}, "topics": {"passed": "8", "details": "cards=300"}})
    assert one_criterion.degenerate_leader(ctx) == []                       # within bounds: 2000 cards is not below 50
    ctx = diagnostic_ctx(repo, {"diagnostics": {"cards": {"max": 1000}}},
                         {"one_per_file": {"passed": "10", "details": "cards=2000"}, "topics": {"passed": "8", "details": "cards=300"}})
    found = one_criterion.degenerate_leader(ctx)
    assert len(found) == 1 and found[0].startswith("S45 files: one_per_file scores best") and "not excluded" in found[0] and "Next:" in found[0]
    assert one_criterion.run(ctx) == [] and any(line.startswith("S45 files") for line in ctx.advisory)   # advice, never a problem


def test_the_diagnostic_reads_a_result_column_and_stays_silent_when_the_leader_is_fine_or_undeclared(repo):
    ctx = diagnostic_ctx(repo, {"diagnostics": {"cost_usd": {"max": 0.5}}}, {"a": {"passed": "10", "cost_usd": "0.9"}, "b": {"passed": "4"}})
    assert one_criterion.degenerate_leader(ctx)[0].startswith("S45 files: a scores best but its cost_usd is 0.9")
    ctx = diagnostic_ctx(repo, {"diagnostics": {"cost_usd": {"max": 0.5}}}, {"a": {"passed": "4", "cost_usd": "0.9"}, "b": {"passed": "10", "cost_usd": "0.1"}})
    assert one_criterion.degenerate_leader(ctx) == []                       # the leader is within bounds; a degenerate loser is not the question
    assert one_criterion.degenerate_leader(diagnostic_ctx(repo, {}, {"a": {"passed": "10"}})) == []
    ctx = diagnostic_ctx(repo, {"diagnostics": {"cost_usd": {"max": 0.5}}}, {"a": {"passed": "10", "cost_usd": "0.9"}})
    ctx.registry.waivers = [{"rule": "S45", "path": "files", "reason": "decided"}]
    assert one_criterion.degenerate_leader(ctx) == []


def test_a_marked_arm_is_an_ordinary_competitor_and_promotion_can_pick_it(cfg):
    """BASELINE and FLOOR no longer mark an arm: a docstring opening with either is just prose, and the arm competes."""
    from esoi import registry
    from test_cascade import clear_selected, set_cascade
    path = cfg.evaluation / "greet_a_person" / "impls" / "shout.py"
    path.write_text(path.read_text().replace("ALTERNATIVE", "BASELINE", 1))
    assert leaderboard.arm_kind({"component": "greet_a_person", "impl": "shout"}, cfg.evaluation) == ""
    assert not hasattr(leaderboard, "FLOOR_KINDS") and not hasattr(promote, "floor_only")
    set_cascade(cfg, "whole [sample=full | real=no]")
    results, header = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in results:
        r.update(cases="40", passed="40", dev="40/40") if r["impl"] == "shout" else r.update(cases="40", passed="20", dev="20/40")
    tables.write_csv(cfg.results_path, header, results)
    fresh = lambda c, comp, row, strict: ""
    clear_selected(cfg)
    [first] = promote.propose(cfg, registry.load(cfg), stale=fresh)
    assert first.winner == "shout"                                          # the highest score wins, whatever the docstring says


def commit(root, text, day):
    env = {"GIT_AUTHOR_DATE": f"{day}T12:00:00", "GIT_COMMITTER_DATE": f"{day}T12:00:00", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}
    (Path(root) / "esoi.toml").write_text(text)
    subprocess.run(["git", "-C", str(root), "add", "esoi.toml"], check=True, env=env)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "x"], check=True, env=env)


def toml(weights):
    return ('package = "demo"\n[balance.files]\ncost_per_case_usd = 0.1\nseconds_per_case = 60\n'
            f'[balance.files.weights]\naccuracy = {weights[0]}\ncost = {weights[1]}\ntime = {weights[2]}\n')


def ctx_for(tmp_path, first_row_day):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commit(tmp_path, toml((0.7, 0.15, 0.15)), "2026-10-01")
    ctx = context_with_toml(tmp_path)
    ctx.history = {"files": {"a": [row("a", balanced="0.8", date=first_row_day)]}}
    return ctx


def context_with_toml(tmp_path):
    cfg = config.from_mapping({"package": "demo", "balance": {"files": {"cost_per_case_usd": 0.1, "seconds_per_case": 60}}}, tmp_path,
                              tmp_path / "esoi.toml")
    from esoi.rules.base import Context
    from esoi.registry import Registry
    return Context(cfg, Registry(), [], {}, {})


def test_a_weight_table_changed_after_the_first_scored_row_is_advice(tmp_path):
    ctx = ctx_for(tmp_path, "2026-10-05")
    assert one_criterion.weights_fixed_first(ctx) == []                       # unchanged since before the first row
    commit(tmp_path, toml((0.5, 0.25, 0.25)), "2026-10-20")
    found = one_criterion.weights_fixed_first(ctx)
    assert len(found) == 1 and found[0].startswith("S44 files") and "fixed before any alternative is scored" in found[0] and "2026-10-20" in found[0]


def test_a_weight_table_changed_before_any_row_is_not_advice(tmp_path):
    ctx = ctx_for(tmp_path, "2026-10-25")
    commit(tmp_path, toml((0.5, 0.25, 0.25)), "2026-10-20")
    assert one_criterion.weights_fixed_first(ctx) == []


def test_the_rules_are_listed_and_advisory_on_the_scaffold(repo):
    problems, advisory = check.check_all(config.load(repo))
    assert not [p for p in problems if p[:3] in ("S41", "S42", "S44", "S45")]
    from esoi import rules
    assert {"S41", "S42", "S44", "S45"} <= set(rules.summaries(config.load(repo)))
