"""The measurement harness: the call meter, sampling, recording and running."""
import csv
import importlib

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
    latest = [r for r in csv.DictReader(cfg.results_path.open()) if r["impl"] == "live"][-1]
    assert latest["git_sha"] and latest["cases_sha"]
    lines.clear()
    harness.rerun_stale(cfg, lines.append)
    assert lines == ["greet_a_person/live: current"]
