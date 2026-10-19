"""The measurement harness: the call meter, sampling, recording and running."""
import csv
import importlib
import sys

import pytest

from esoi import harness
from esoi.config import Config

BUILD = 'def build(meter):\n    def run(kind, args):\n        meter.record()\n        return {"n": args["n"]}\n    return run\n'


class Provider:
    tokens_in = tokens_out = 0
    cost_usd = 0.0

    def plan(self, x):
        self.tokens_in += 10
        return x

    def answer(self, x):
        return x


def test_the_meter_counts_calls_tokens_and_enforces_a_budget():
    meter, provider = harness.CallMeter(max_calls=2), Provider()
    meter.wrap(provider)
    provider.plan(1)
    provider.answer(2)
    assert meter.calls == 2 and meter.tokens_in == 10
    with pytest.raises(harness.BudgetExceeded):
        provider.plan(3)
    assert meter.wrap(provider) is provider


def test_stratified_sample_is_stable_and_a_smaller_sample_is_a_prefix():
    cases = [{"id": f"c{i:02d}", "area": "ab"[i % 2]} for i in range(20)]
    small, big = harness.stratified_sample(cases, 4), harness.stratified_sample(cases, 8)
    assert harness.stratified_sample(cases, 4) == small
    assert {c["id"] for c in small} <= {c["id"] for c in big}
    assert {c["area"] for c in small} == {"a", "b"}


def make(tmp_path, name):
    comp = tmp_path / "evaluation" / "components" / name
    (comp / "impls").mkdir(parents=True)
    for init in (comp / "__init__.py", comp / "impls" / "__init__.py"):
        init.write_text("")
    (comp / "score.py").write_text("from esoi import expect\n\n\ndef score_case(fn, case):\n    return expect.score_kind_case(fn, case)\n\n\n"
                                   "def aggregate(rows):\n    return 'agg'\n")
    (comp / "impls" / "live.py").write_text(BUILD)
    (comp / "cases.json").write_text('[{"id": "A", "kind": "k", "args": {"n": 1}, "expect": {"eq": {"n": 1}}},'
                                     ' {"id": "B", "kind": "k", "args": {"n": 2}, "expect": {"eq": {"n": 2}}, "heldout": true}]')
    return Config(root=tmp_path, package="nopkg")


def test_run_component_scores_cases_and_records_provenance(tmp_path):
    cfg = make(tmp_path, "comp_run")
    lines = []
    harness.prepare_path(cfg)
    score = importlib.import_module("comp_run.score")
    summary, rows = harness.run_component("comp_run", score.score_case, ["--impl", "live", "--record"], cfg, lines.append)
    assert summary["passed"] == 2 and summary["model_calls"] == 2 and summary["heldout"] == "1/1"
    written = list(csv.DictReader(cfg.results_path.open()))
    assert written[0]["impl"] == "live" and written[0]["cases_sha"] and written[0]["component"] == "comp_run"
    assert any("agg" in line for line in lines)


def test_only_and_max_calls(tmp_path):
    cfg = make(tmp_path, "comp_flags")
    harness.prepare_path(cfg)
    score = importlib.import_module("comp_flags.score").score_case
    summary, _ = harness.run_component("comp_flags", score, ["--impl", "live", "--only", "A"], cfg, lambda text: None)
    assert summary["cases"] == 1
    with pytest.raises(harness.BudgetExceeded):
        harness.run_component("comp_flags", score, ["--impl", "live", "--max-calls", "1"], cfg, lambda text: None)


def test_run_cli_lists_components_when_the_name_is_wrong(tmp_path):
    cfg = make(tmp_path, "comp_cli")
    lines = []
    assert harness.run_cli(["nothing"], cfg, lines.append) == 2 and "comp_cli" in lines[-1]
    assert harness.run_cli(["comp_cli", "--impl", "live"], cfg, lambda text: None) == 0


def test_stratified_cases_csv_marks_heldout(tmp_path):
    cfg = make(tmp_path, "comp_csv")
    folder = tmp_path / "evaluation" / "components" / "comp_csv"
    (folder / "cases.json").unlink()
    (folder / "cases.csv").write_text("id,kind,heldout\nA,k,yes\nB,k,\n")
    cases = harness.load_cases("comp_csv", cfg)
    assert [c["heldout"] for c in cases] == [True, False]


def test_current_sha_is_empty_outside_git_and_dirty_marks_code(tmp_path):
    cfg = Config(root=tmp_path, package="pkg")
    assert harness.current_sha(cfg) == ""


def git(root, *args):
    import subprocess
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_stale_reason_names_each_way_a_result_stops_counting(tmp_path):
    cfg = make(tmp_path, "comp_stale")
    cfg.code_paths = ["pkg"]
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "live.py").write_text("X = 1\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    harness.record_result(dict(component="comp_stale", impl="live", cases=2, passed=2, model_calls=0), cfg, date="2026-01-01")
    row = list(csv.DictReader(cfg.results_path.open()))[-1]
    assert harness.stale_reason(cfg, "comp_stale", row) == ""
    assert "no recorded result" in harness.stale_reason(cfg, "comp_stale", None)
    (tmp_path / "pkg" / "live.py").write_text("X = 2\n")
    assert "changed since its commit" in harness.stale_reason(cfg, "comp_stale", row)
    assert harness.stale_reason(cfg, "comp_stale", row, strict=False) == ""
    assert "uncommitted" in harness.stale_reason(cfg, "comp_stale", dict(row, git_sha=row["git_sha"] + "-dirty"))
    assert "other cases" in harness.stale_reason(cfg, "comp_stale", dict(row, cases_sha="deadbeef"))
    assert "no git_sha" in harness.stale_reason(cfg, "comp_stale", dict(row, git_sha=""))


def test_rerun_stale_runs_only_what_is_stale(repo):
    from esoi import config as config_module
    cfg = config_module.load(repo)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    cases = cfg.evaluation / "greet_a_person" / "cases.json"
    cases.write_text(cases.read_text() + " ")
    git(repo, "commit", "-q", "-am", "cases changed")
    lines = []
    harness.rerun_stale(cfg, lines.append)
    assert any("greet_a_person/live: stale, its latest row was recorded on other cases" in line for line in lines)
    assert any("greet_a_person/live: run and recorded" in line for line in lines)
    assert any("greet_a_person/shout: run and recorded" in line for line in lines)   # the rival the verdict rests on
    latest = [r for r in csv.DictReader(cfg.results_path.open()) if r["impl"] == "live"][-1]
    assert latest["git_sha"] and latest["cases_sha"]
    lines.clear()
    harness.rerun_stale(cfg, lines.append)
    assert lines == ["greet_a_person/live: current", "greet_a_person/shout: current"]


def run_summary(**changes):
    return {**dict(component="comp_cost", impl="live", cases=1, passed=1, model_calls=2, tokens_in=1_000_000, tokens_out=100_000,
                   cli_reported_cost_usd=0.0, model="model-x-20260101"), **changes}


def test_cost_is_computed_from_the_price_table_and_blank_when_the_price_is_unknown(tmp_path):
    cfg = make(tmp_path, "comp_cost")
    cfg.prices = {"model-x": {"input": 3.0, "output": 15.0}}
    assert harness.record_result(run_summary(), cfg, date="2026-01-01")["cost_usd"] == 4.5   # 3.0 + 1.5, USD per million tokens
    assert harness.record_result(run_summary(model="other-model"), cfg, date="2026-01-02")["cost_usd"] == ""
    assert harness.record_result(run_summary(cli_reported_cost_usd=0.25), cfg, date="2026-01-03")["cost_usd"] == 0.25   # reported wins
    assert harness.record_result(dict(run_summary(), model_calls=0, tokens_in=0, tokens_out=0), cfg, date="2026-01-04")["cost_usd"] == 0.0
    written = list(csv.DictReader(cfg.results_path.open()))
    assert [r["cost_usd"] for r in written] == ["4.5", "", "0.25", "0.0"]


def test_an_unknown_cost_never_counts_as_free_on_the_board():
    from esoi import leaderboard
    known = dict(component="c", impl="a", cases="2", passed="2", model_calls="3", tokens_in="0", tokens_out="0", cost_usd="0.5")
    unknown = dict(known, impl="b", cost_usd="")
    assert [r["impl"] for r in leaderboard.rank({"a": unknown, "b": known})] == ["a", "b"]   # the priced run first
    assert leaderboard.dollars(unknown) == float("inf") and leaderboard.dollars(dict(unknown, model_calls="0")) == 0.0
    assert "cost=unknown" in "\n".join(leaderboard.format_rows({"b": unknown}, None))


def test_a_code_path_in_another_repository_is_diffed_in_that_repository(tmp_path):
    sibling = tmp_path / "sibling"
    (sibling / "lib").mkdir(parents=True)
    (sibling / "lib" / "a.py").write_text("X = 1\n")
    git(sibling, "init", "-q")
    git(sibling, "add", "-A")
    git(sibling, "commit", "-q", "-m", "init")
    main = tmp_path / "main"
    main.mkdir()
    cfg = make(main, "comp_ext")
    cfg.code_paths = ["pkg", "../sibling/lib"]
    (main / "pkg").mkdir()
    (main / "pkg" / "live.py").write_text("Y = 1\n")
    git(main, "init", "-q")
    git(main, "add", "-A")
    git(main, "commit", "-q", "-m", "init")
    row = harness.record_result(dict(component="comp_ext", impl="live", cases=2, passed=2, model_calls=0), cfg, date="2026-01-01")
    assert row["code_shas"].startswith("../sibling/lib@") and not row["code_shas"].endswith("-dirty")
    assert harness.stale_reason(cfg, "comp_ext", row) == ""
    (sibling / "lib" / "a.py").write_text("X = 2\n")
    assert "../sibling/lib changed since its commit" in harness.stale_reason(cfg, "comp_ext", row)
    assert harness.stale_reason(cfg, "comp_ext", row, strict=False) == ""
    git(sibling, "commit", "-q", "-am", "change")
    assert "changed since its commit" in harness.stale_reason(cfg, "comp_ext", row)
    assert "records no commit" in harness.stale_reason(cfg, "comp_ext", dict(row, code_shas=""))
    (sibling / "lib" / "a.py").write_text("X = 3\n")
    assert harness.record_result(dict(component="comp_ext", impl="live", cases=2, passed=2, model_calls=0), cfg,
                                 date="2026-01-02")["code_shas"].endswith("-dirty")
    assert "uncommitted code in ../sibling/lib" in harness.stale_reason(cfg, "comp_ext", list(csv.DictReader(cfg.results_path.open()))[-1])


def test_the_results_log_gains_the_code_shas_column_without_losing_rows(tmp_path):
    cfg = make(tmp_path, "comp_col")
    harness.record_result(dict(component="comp_col", impl="live", cases=2, passed=2, model_calls=0), cfg, date="2026-01-01")
    assert "code_shas" not in cfg.results_path.read_text().splitlines()[0]   # a repository with no outside code keeps its header
    (tmp_path.parent / "elsewhere").mkdir(exist_ok=True)
    harness.append_row(cfg.results_path, dict(date="2026-01-02", component="comp_col", impl="b", code_shas="x@1"), True)
    rows = list(csv.DictReader(cfg.results_path.open()))
    assert [r["impl"] for r in rows] == ["live", "b"] and rows[0]["code_shas"] == "" and rows[1]["code_shas"] == "x@1"


def paid_repo(repo):
    from esoi import config as config_module
    cfg = config_module.load(repo)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    cases = cfg.evaluation / "greet_a_person" / "cases.json"
    cases.write_text(cases.read_text() + " ")
    git(repo, "commit", "-q", "-am", "cases changed")
    return cfg


def test_rerun_stale_skips_a_paid_arm_unless_asked(repo):
    cfg = paid_repo(repo)
    shout = cfg.evaluation / "greet_a_person" / "impls" / "shout.py"
    shout.write_text("PAID = True\n" + shout.read_text())
    git(repo, "commit", "-q", "-am", "shout now calls a paid model")
    lines = []
    harness.rerun_stale(cfg, lines.append)
    assert any("greet_a_person/shout: stale" in line and "SKIPPED" in line and "PAID = True" in line for line in lines)
    assert any("--include greet_a_person/shout" in line for line in lines)
    assert not any("shout: run" in line for line in lines) and any("live: run and recorded" in line for line in lines)
    lines.clear()
    harness.rerun_stale(cfg, lines.append, include=["greet_a_person/shout"])
    assert any("greet_a_person/shout: run and recorded" in line for line in lines)


def test_an_arm_listed_in_paid_arms_or_recorded_with_model_calls_is_paid(repo):
    cfg = paid_repo(repo)
    assert harness.paid_reason(cfg, "greet_a_person", "live", None) == ""
    cfg.paid_arms = ["greet_a_person/live"]
    assert "paid_arms" in harness.paid_reason(cfg, "greet_a_person", "live", None)
    cfg.paid_arms = []
    assert "called a model" in harness.paid_reason(cfg, "greet_a_person", "live", {"model_calls": "4"})
    lines = []
    cfg.paid_arms = ["greet_a_person/live", "greet_a_person/shout"]
    harness.rerun_stale(cfg, lines.append)
    assert sum("SKIPPED" in line for line in lines) == 2 and not any(": run" in line for line in lines)
    lines.clear()
    harness.rerun_stale(cfg, lines.append, include_paid=True)
    assert sum(": run and recorded" in line for line in lines) == 2


def test_a_sampled_run_records_its_sample_and_a_full_run_leaves_it_blank(tmp_path):
    cfg = make(tmp_path, "comp_sample")
    harness.prepare_path(cfg)
    score = importlib.import_module("comp_sample.score").score_case
    quiet = lambda text: None
    harness.run_component("comp_sample", score, ["--impl", "live", "--sample", "1", "--record"], cfg, quiet)
    harness.run_component("comp_sample", score, ["--impl", "live", "--sample", "5", "--record"], cfg, quiet)   # whole set
    harness.run_component("comp_sample", score, ["--impl", "live", "--only", "B", "--record"], cfg, quiet)
    written = list(csv.DictReader(cfg.results_path.open()))
    assert [r["sample"] for r in written] == ["sample:1", "", "only:B"]
    assert harness.sample_args(cfg, "comp_sample", written[0]) == ["--sample", "1"]
    assert harness.sample_args(cfg, "comp_sample", written[1]) == []
    assert harness.sample_args(cfg, "comp_sample", written[2]) == ["--only", "B"]
    legacy = dict(written[0], sample="", cases="1")   # recorded before the column: fewer cases than the set
    assert harness.sample_args(cfg, "comp_sample", legacy) == ["--sample", "1"]
    assert harness.sample_args(cfg, "comp_sample", dict(legacy, cases_sha="deadbeef")) == []   # other cases: the full set


def test_rerun_stale_keeps_the_sample_and_runs_a_rival_on_the_selected_arms_sample(repo):
    from esoi import config as config_module
    cfg = config_module.load(repo)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    harness.prepare_path(cfg)
    score = importlib.import_module("greet_a_person.score").score_case
    quiet = lambda text: None
    harness.run_component("greet_a_person", score, ["--impl", "live", "--sample", "1", "--record"], cfg, quiet)
    harness.run_component("greet_a_person", score, ["--impl", "shout", "--record"], cfg, quiet)   # the whole set
    lines = []
    harness.rerun_stale(cfg, lines.append)
    assert "greet_a_person/live: current" in lines
    assert any("shout: stale, it was scored on a different sample" in line and "not comparable" in line for line in lines)
    latest = {r["impl"]: r for r in csv.DictReader(cfg.results_path.open())}
    assert latest["live"]["sample"] == "sample:1" and latest["shout"]["sample"] == "sample:1"
    lines.clear()
    harness.rerun_stale(cfg, lines.append)
    assert lines == ["greet_a_person/live: current", "greet_a_person/shout: current"]
    lines.clear()
    harness.rerun_stale(cfg, lines.append, full=True)   # --full asks for the whole set
    latest = {r["impl"]: r for r in csv.DictReader(cfg.results_path.open())}
    assert latest["live"]["sample"] == "" and latest["shout"]["sample"] == "" and latest["live"]["cases"] == "2"


def forget_modules(*prefixes):
    """Drop the modules a test imported from its throwaway repository, so the next test imports its own."""
    for name in [m for m in sys.modules if any(m == p or m.startswith(p + ".") for p in prefixes)]:
        del sys.modules[name]


def test_rerun_stale_runs_an_arm_that_declares_itself_simulated_and_skips_one_that_does_not(repo):
    cfg = paid_repo(repo)
    live = cfg.evaluation / "greet_a_person" / "impls" / "live.py"
    live.write_text(live.read_text().replace("    def run(kind, args):\n", "    def run(kind, args):\n        meter.record()   # a stand-in that counts the calls a model would make\n"))
    git(repo, "commit", "-q", "-am", "the live arm becomes a stand-in")
    forget_modules("greet_a_person")   # other tests imported the unedited arm
    harness.prepare_path(cfg)
    score = importlib.import_module("greet_a_person.score").score_case
    harness.run_component("greet_a_person", score, ["--impl", "live", "--record"], cfg, lambda text: None)
    row = list(csv.DictReader(cfg.results_path.open()))[-1]
    assert row["model"] == "unknown" and row["cost_usd"] == "" and int(row["model_calls"]) > 0   # the false-loss precondition
    cases = cfg.evaluation / "greet_a_person" / "cases.json"
    cases.write_text(cases.read_text() + " ")
    git(repo, "commit", "-q", "-am", "cases changed again")
    lines = []
    harness.rerun_stale(cfg, lines.append)
    assert any("greet_a_person/live: stale" in line and "SKIPPED" in line and "called a model" in line for line in lines)
    live.write_text('"""CURRENT: a stand-in."""\nSIMULATED = True\n' + live.read_text().split('"""\n', 1)[1])
    git(repo, "commit", "-q", "-am", "the stand-in declares itself simulated")
    forget_modules("greet_a_person")
    lines.clear()
    harness.rerun_stale(cfg, lines.append)
    assert any("greet_a_person/live: run and recorded" in line for line in lines) and not any("live: stale" in line and "SKIPPED" in line for line in lines)
    row = [r for r in csv.DictReader(cfg.results_path.open()) if r["impl"] == "live"][-1]
    assert (row["model"], row["cost_usd"]) == ("simulated", "0.0")
    forget_modules("greet_a_person", "demo")


def test_the_harness_runs_an_implementation_the_code_declares_without_a_wrapper_file(repo):
    from esoi import config as config_module, runtime
    cfg = config_module.load(repo)
    harness.prepare_path(cfg)
    try:
        summary, _ = harness.run_component("greet_a_person", importlib.import_module("greet_a_person.score").score_case,
                                           ["--impl", "greet"], cfg, lambda text: None)
        assert summary["passed"] == summary["cases"] == 2
        with pytest.raises(harness.RunError, match="no implementation 'ghost'; known: live, shout"):
            harness.load_impl("ghost", "greet_a_person", cfg)
    finally:
        runtime.forget("greet-a-person")
        runtime.PROJECTS.clear()
        forget_modules("greet_a_person", "demo")
