"""Rules S41 to S44 (a cascade runs one criterion) and the floor rule of select/promote. All advisory, none calls a model."""
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


def floor_repo(repo, kind):
    """The scaffold's component gets a floor-marked arm named `floor`; returns (config, component)."""
    cfg = config.load(repo)
    component = next(iter(sorted(p.name for p in cfg.evaluation.iterdir() if (p / "impls").is_dir())))
    (cfg.evaluation / component / "impls" / "floor.py").write_text(f'"""{kind}: one card per file."""\n')
    return cfg, component


def test_a_selected_baseline_is_advice_and_a_problem_only_when_the_repository_opts_in(repo):
    cfg, component = floor_repo(repo, "BASELINE")
    ctx = context(repo)
    ctx.registry.solutions = [{"solution_id": "s", "metric_command": f"esoi run {component} --impl floor; esoi run {component} --impl live",
                               "selected": "floor"}]
    ctx.registry.solution_order = ["s"]
    ctx.history = {component: {"floor": [row("floor", component=component)]}}
    found = one_criterion.floor_arms(ctx)
    assert found and found[0].startswith("S43 s") and "never" in found[0] and "next:" in found[0]
    assert one_criterion.run(ctx) == [] and ctx.advisory                      # advice by default
    ctx.config.rules["S43"] = {"problem": True}
    assert one_criterion.run(ctx) and one_criterion.run(ctx)[0].startswith("S43 s")   # a problem where the repository opts in
    ctx.registry.solutions[0]["selected"] = "live"
    ctx.history[component]["live"] = [row("live", component=component)]
    assert one_criterion.floor_arms(ctx) == []


def test_promotion_never_offers_a_baseline_as_the_winner(repo):
    cfg, component = floor_repo(repo, "BASELINE")
    assert promote.floor_only(cfg, component, "floor") is True
    assert promote.floor_only(cfg, component, "no-such-arm") is False


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
    assert not [p for p in problems if p[:3] in ("S41", "S42", "S43", "S44")]
    from esoi import rules
    assert {"S41", "S42", "S43", "S44"} <= set(rules.summaries(config.load(repo)))


def test_a_baseline_that_scores_best_is_blocked_by_promotion_and_a_first_choice_skips_it(cfg):
    from esoi import registry
    from test_cascade import clear_selected, set_cascade
    path = cfg.evaluation / "greet_a_person" / "impls" / "shout.py"
    path.write_text(path.read_text().replace("ALTERNATIVE", "BASELINE", 1))
    set_cascade(cfg, "whole [sample=full | real=no]")
    results, header = tables.read_csv(cfg.results_path), tables.read_header(cfg.results_path)
    for r in results:
        r.update(cases="40", passed="40", dev="40/40") if r["impl"] == "shout" else r.update(cases="40", passed="20", dev="20/40")
    tables.write_csv(cfg.results_path, header, results)
    fresh = lambda c, comp, row, strict: ""
    [proposal] = promote.propose(cfg, registry.load(cfg), stale=fresh)
    assert proposal.status == "blocked" and "never selected" in proposal.reason and proposal.selected == ""
    clear_selected(cfg)
    [first] = promote.propose(cfg, registry.load(cfg), stale=fresh)
    assert first.winner != "shout"
