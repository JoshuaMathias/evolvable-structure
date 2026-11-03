"""The iterative use of metrics: every run is saved, an unrecorded run stops at the first failure, only the failing cases are rerun,
the whole set waits for them, and a later stage reuses the cases an earlier one ran."""
import importlib

import pytest

from esoi import cascade, harness, run_guards, run_log
from esoi.config import Config

BUILD = ('def build(meter):\n    def run(kind, args):\n        meter.record()\n        return {"n": args["n"] if args["n"] != 2 '
         'else (2 if __import__("os").environ.get("ESOI_TEST_B") == "1" else 0)}\n    return run\n')


def make(tmp_path, name):
    comp = tmp_path / "evaluation" / "components" / name
    (comp / "impls").mkdir(parents=True)
    for init in (comp / "__init__.py", comp / "impls" / "__init__.py"):
        init.write_text("")
    (comp / "score.py").write_text("from esoi import expect\n\n\ndef score_case(fn, case):\n    return expect.score_kind_case(fn, case)\n")
    (comp / "impls" / "live.py").write_text(BUILD)
    cases = ",".join(f'{{"id": "C{i}", "kind": "k", "args": {{"n": {i}}}, "expect": {{"eq": {{"n": {i}}}}}}}' for i in (1, 2, 3))
    (comp / "cases.json").write_text(f"[{cases}]")
    harness.prepare_path(Config(root=tmp_path, package="nopkg"))
    return Config(root=tmp_path, package="nopkg"), importlib.import_module(f"{name}.score").score_case


def run(cfg, score, name, *flags, monkeypatch=None):
    lines = []
    summary, rows = harness.run_component(name, score, ["--impl", "live", *flags], cfg, lines.append)
    return summary, rows, lines


def entries(cfg, kind):
    return [e for e in run_log.read(cfg.root / cfg.runs_log) if e["kind"] == kind]


def test_an_unrecorded_run_stops_at_the_first_failure_and_still_saves_what_it_scored(tmp_path, monkeypatch):
    monkeypatch.delenv("ESOI_TEST_B", raising=False)
    cfg, score = make(tmp_path, "rl_stop")
    summary, rows, lines = run(cfg, score, "rl_stop")
    assert [r["id"] for r in rows] == ["C1", "C2"] and summary["passed"] == 1
    assert [e["case_id"] for e in entries(cfg, "case")] == ["C1", "C2"]
    assert entries(cfg, "end")[0]["status"].startswith("stopped")
    assert not cfg.results_path.exists()   # saved in the run log, never in the results the leaderboard reads
    assert any("--failed" in line for line in lines)
    _, rows, _ = run(cfg, score, "rl_stop", "--only", "C1", "--keep-going")
    assert len(rows) == 1


def test_keep_going_and_record_run_every_case(tmp_path, monkeypatch):
    monkeypatch.delenv("ESOI_TEST_B", raising=False)
    cfg, score = make(tmp_path, "rl_all")
    _, rows, _ = run(cfg, score, "rl_all", "--keep-going")
    assert len(rows) == 3
    cfg2, score2 = make(tmp_path / "second", "rl_all2") if (tmp_path / "second").mkdir() is None else (None, None)
    _, rows, _ = run(cfg2, score2, "rl_all2", "--record")
    assert len(rows) == 3 and cfg2.results_path.exists()


def test_a_budget_abort_keeps_the_cases_scored_before_it(tmp_path):
    cfg, score = make(tmp_path, "rl_budget")
    with pytest.raises(harness.BudgetExceeded):
        run(cfg, score, "rl_budget", "--max-calls", "1", "--keep-going")
    assert [e["case_id"] for e in entries(cfg, "case")] == ["C1"]
    assert entries(cfg, "end")[0]["status"] == "stopped: BudgetExceeded"


def test_failed_reruns_only_the_failing_cases_and_the_whole_set_waits_for_them(tmp_path, monkeypatch):
    monkeypatch.delenv("ESOI_TEST_B", raising=False)
    cfg, score = make(tmp_path, "rl_failed")
    run(cfg, score, "rl_failed")   # stops at C2
    with pytest.raises(harness.RunError, match="not run on the whole set.*C2.*--failed"):
        run(cfg, score, "rl_failed")
    with pytest.raises(harness.RunError, match="drop --only"):
        run(cfg, score, "rl_failed", "--failed", "--only", "C1")
    _, rows, _ = run(cfg, score, "rl_failed", "--failed")
    assert [r["id"] for r in rows] == ["C2"] and not rows[0]["ok"]
    summary, _, _ = run(cfg, score, "rl_failed", "--force", "checking the guard", "--keep-going")
    assert "forced past unsolved failures: checking the guard" in summary["details"]
    monkeypatch.setenv("ESOI_TEST_B", "1")
    _, rows, _ = run(cfg, score, "rl_failed", "--failed")
    assert rows[0]["ok"]
    run(cfg, score, "rl_failed")   # solved: the whole set runs
    with pytest.raises(harness.RunError, match="nothing to rerun"):
        run(cfg, score, "rl_failed", "--failed")


def test_a_failure_inside_a_finished_recorded_whole_run_is_a_measurement_not_work_in_progress(tmp_path, monkeypatch):
    monkeypatch.delenv("ESOI_TEST_B", raising=False)
    cfg, score = make(tmp_path, "rl_baseline")
    run(cfg, score, "rl_baseline", "--record")
    assert run_guards.unsolved_reason(cfg, "rl_baseline", "live") == ""
    _, rows, _ = run(cfg, score, "rl_baseline", "--failed")   # still rerunnable by hand
    assert [r["id"] for r in rows] == ["C2"]
    assert "C2" in run_guards.unsolved_reason(cfg, "rl_baseline", "live")


def test_a_later_stage_reuses_cases_run_for_the_same_code_and_reruns_them_after_a_change(tmp_path, monkeypatch):
    monkeypatch.setenv("ESOI_TEST_B", "1")
    cfg, score = make(tmp_path, "rl_reuse")
    version = ["abc1234"]
    monkeypatch.setattr(harness, "current_sha", lambda config: version[0])
    first, _, _ = run(cfg, score, "rl_reuse", "--sample", "1", "--record")
    assert first["model_calls"] == 1
    second, rows, lines = run(cfg, score, "rl_reuse", "--record")
    assert len(rows) == 3 and second["model_calls"] == 3   # the spend of the reused case is counted once, in its own row
    assert sum("reused" in line for line in lines) == 1 and "reused 1 case(s)" in second["details"]
    again, _, lines = run(cfg, score, "rl_reuse", "--fresh")
    assert not any("reused" in line for line in lines)
    version[0] = "def5678"
    _, _, lines = run(cfg, score, "rl_reuse")
    assert not any("reused" in line for line in lines)
    version[0] = "def5678-dirty"
    assert run_log.reusable(cfg.root / cfg.runs_log, "rl_reuse", "live", harness.cases_digest("rl_reuse", cfg.evaluation), "def5678-dirty") == {}


def stage_notes(text):
    found, errors = cascade.parse(text)
    assert errors == []
    return cascade.expectation_notes(found)


def test_a_free_full_set_stage_then_one_real_case_then_more_is_the_expected_order():
    assert stage_notes("free [sample=full | real=no | gate=all-pass] > one [sample=sample:1 | real=yes | gate=all-pass] > "
                       "three [sample=sample:3 | real=yes | gate=all-pass] > real-use [real=yes | when=used in production]") == []
    assert stage_notes("free [sample=full | real=no | gate=all-pass] > one [sample=sample:1 | real=yes]") == []


def test_the_cascade_expectations_are_notes_about_a_free_first_stage_and_growing_model_stages():
    assert stage_notes("free [sample=full | real=no | gate=all-pass] > one [sample=sample:1 | real=yes | gate=all-pass] > "
                       "ten [sample=sample:10 | real=yes | gate=all-pass] > all [sample=full | real=yes]") == []
    assert stage_notes("one [sample=full | real=no]") == []
    assert len(stage_notes("a [sample=sample:3 | real=yes | gate=all-pass] > b [sample=sample:10 | real=yes]")) == 1
    shrinking = stage_notes("free [real=no | gate=all-pass] > a [sample=sample:10 | real=yes | gate=all-pass] > b [sample=sample:3 | real=yes | gate=all-pass] > c [sample=full]")
    assert len(shrinking) == 1 and "fewer cases" in shrinking[0]
