"""What a recorded result measures: the three staleness rules (repo_wide, component_paths, import_closure), their fallbacks, the
plan that says why a row is or is not re-run, and the offline guard."""
import csv
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation" / "components"))

from esoi import config as config_module, harness, staleness  # noqa: E402
import staleness_fixture  # noqa: E402

SCORE = importlib.import_module("staleness_precision.score")
CASES = harness.load_cases("staleness_precision", config_module.Config(root=ROOT, package="esoi", evaluation_dir="evaluation/components"))


def run_arm(rule):
    return [dict(SCORE.score_case(lambda kind, args: staleness_fixture.decide(rule, args["step"], args["component"]), case), id=case["id"])
            for case in CASES]


def counts(rule):
    return SCORE.aggregate(run_arm(rule))


def test_repo_wide_is_safe_and_calls_every_change_stale():
    got = counts("repo_wide")
    assert got["false_fresh"] == 0 and got["false_stale"] > 20


def test_another_solutions_code_never_stales_a_result_and_import_closure_ignores_a_shared_fixture():
    for rule in ("component_paths", "import_closure"):
        assert SCORE.aggregate(run_arm(rule))["false_fresh"] == 0
        assert decide(rule, "touch-the-shared-utility", "alpha")["stale"] is False        # util.py is sol-util's implementation
    assert decide("import_closure", "touch-a-shared-evaluation-fixture", "alpha")["stale"] is False   # a shared test fixture
    assert decide("repo_wide", "touch-the-shared-utility", "alpha")["stale"] is True


def test_import_closure_never_keeps_a_changed_row_and_is_more_precise_than_repo_wide():
    got = counts("import_closure")
    assert got["false_fresh"] == 0
    assert got["false_stale"] < counts("repo_wide")["false_stale"] / 3


def test_the_naive_arm_that_is_never_stale_is_all_false_fresh():
    never = importlib.import_module("staleness_precision.broken.never_stale").build(None)
    rows = [SCORE.score_case(never, case) for case in CASES]
    assert SCORE.aggregate(rows)["false_fresh"] == sum(c["expect"]["stale"] for c in CASES)


def decide(rule, step, component):
    return staleness_fixture.decide(rule, step, component)


def test_an_unowned_component_falls_back_to_the_whole_repository_never_silently_fresh():
    assert decide("component_paths", "touch-another-components-file", "orphan")["stale"] is True
    assert decide("import_closure", "touch-another-components-file", "orphan")["stale"] is True


def test_the_reason_names_the_changed_file_and_who_owns_it():
    why = decide("import_closure", "touch-the-measured-file", "alpha")["why"]
    assert "pkg/alpha.py" in why and "own code" in why
    assert "owned by component util" in staleness.explain(
        *explain_args("component_paths", "touch-the-shared-utility", "beta"))["ignored"][0]
    assert any("pkg/util.py" in line and "not the arm's code" not in line for line in staleness.explain(
        *explain_args("import_closure", "touch-the-shared-utility", "alpha"))["ignored"])


def explain_args(rule, step, component):
    built = staleness_fixture.build(step)
    cfg = config_module.load(built.root / "esoi.toml")
    return cfg, f"{component}_eval", "live", built.sha, rule


def test_a_rename_counts_under_both_names_and_a_doc_outside_the_code_never_counts():
    assert decide("import_closure", "rename-a-file", "delta")["stale"] is True
    assert decide("import_closure", "rename-a-file", "alpha")["stale"] is False
    assert not any(decide(rule, "touch-a-doc", c)["stale"] for rule in staleness.RULES for c in ("alpha", "beta", "delta"))


def test_a_dynamic_import_the_scan_cannot_read_falls_back_to_the_components_files(tmp_path):
    built = staleness_fixture.build("touch-the-measured-file")
    cfg = config_module.load(built.root / "esoi.toml")
    live = built.root / "evaluation/components/beta_eval/impls/live.py"
    live.write_text(live.read_text() + "\nimport importlib\n\n\ndef late(name):\n    return importlib.import_module(name)\n")
    scope = staleness.scope_for(cfg, "beta_eval", "live", "import_closure")
    assert scope.rule == "component_paths" and "computed import" in scope.note


def test_the_rule_comes_from_the_configuration_then_the_records_then_the_default(tmp_path):
    built = staleness_fixture.build("touch-a-doc")
    cfg = config_module.load(built.root / "esoi.toml")
    assert staleness.rule_for(cfg) == staleness.DEFAULT_RULE
    cfg.staleness_rule = "component_paths"
    assert staleness.rule_for(cfg) == "component_paths"
    with pytest.raises(config_module.ConfigError):
        config_module.Config(root=built.root, staleness_rule="whatever")


def test_the_offline_guard_refuses_a_model_command_and_counts_the_attempt():
    meter = harness.CallMeter()
    guard = harness.OfflineGuard(meter)
    guard.start()
    try:
        with pytest.raises(harness.OfflineViolation):
            subprocess.run(["claude", "-p", "hello"])
        with pytest.raises(harness.OfflineViolation):
            subprocess.run("/home/someone/.local/bin/claude -p hi", shell=True)
        assert subprocess.run(["echo", "fine"], capture_output=True).returncode == 0
    finally:
        guard.stop()
    assert meter.attempted == 2
    assert subprocess.run(["echo", "after"], capture_output=True).returncode == 0


def test_a_rival_that_does_not_import_the_changed_file_stays_current_under_the_default_rule(repo):
    cfg = config_module.load(repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=a@b.c", "-c", "user.name=a", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    (repo / "demo" / "greet.py").write_text((repo / "demo" / "greet.py").read_text() + "\n# changed\n")
    rows = {impl: dict(impl=impl, git_sha=sha, cases_sha=harness.cases_digest("greet_a_person", cfg.evaluation)) for impl in ("live", "shout")}
    assert harness.stale_reason(cfg, "greet_a_person", rows["shout"]) == ""   # shout never imports demo/greet.py
    cfg.staleness_rule = "repo_wide"
    assert "demo/greet.py" in harness.stale_reason(cfg, "greet_a_person", rows["shout"])


def test_a_scan_that_meets_a_computed_import_still_counts_the_files_it_found(tmp_path):
    built = staleness_fixture.build("touch-the-shared-utility")
    cfg = config_module.load(built.root / "esoi.toml")
    live = built.root / "evaluation/components/beta_eval/impls/live.py"
    live.write_text(live.read_text() + "\nimport importlib\nfrom pkg import unowned_helper\n\n\ndef late(name):\n    return importlib.import_module(name)\n")
    cfg.staleness_rule = "import_closure"
    scope = staleness.scope_for(cfg, "beta_eval", "live", "import_closure")
    assert scope.rule == "component_paths" and not scope.complete
    assert staleness.judge(cfg, scope, "pkg/unowned_helper.py") == (True, "imported by the arm")   # found by the partial scan, though component_paths alone would miss it
    assert staleness.judge(cfg, scope, "pkg/util.py")[0] is False                        # another solution's implementation is never this arm's code
    assert staleness.judge(cfg, scope, "pkg/alpha.py")[0] is False                       # owned by another component and not seen importing


def test_the_offline_guard_sets_the_variable_a_provider_reads_and_restores_it(monkeypatch):
    monkeypatch.delenv("ESOI_OFFLINE", raising=False)
    guard = harness.OfflineGuard(harness.CallMeter())
    guard.start()
    try:
        assert os.environ["ESOI_OFFLINE"] == "1"
    finally:
        guard.stop()
    assert "ESOI_OFFLINE" not in os.environ
    monkeypatch.setenv("ESOI_OFFLINE", "0")
    guard.start()
    guard.stop()
    assert os.environ["ESOI_OFFLINE"] == "0"


def judged(rule_step, path, component="alpha"):
    built = staleness_fixture.build(rule_step)
    cfg = config_module.load(built.root / "esoi.toml")
    cfg.staleness_rule = "import_closure"
    return staleness.judge(cfg, staleness.scope_for(cfg, f"{component}_eval", "live", "import_closure"), path)


def test_editing_the_arms_own_code_stales_it_and_nothing_else_does():
    step = "touch-the-measured-file"
    assert judged(step, "pkg/alpha.py")[0] is True                                           # the record's implementation file
    assert judged(step, "evaluation/components/alpha_eval/impls/live.py")[0] is True         # the wrapper
    assert judged(step, "pkg/util.py")[0] is False                                           # another solution's implementation, though imported
    assert judged(step, "evaluation/components/fixture_shared.py")[0] is False               # a shared fixture the wrapper imports
    assert judged(step, "evaluation/components/alpha_eval/score.py")[0] is False             # the scorer
    assert judged(step, "evaluation/components/alpha_eval/cases.json")[0] is False           # the dataset
    assert judged(step, "evaluation/components/beta_eval/impls/live.py")[0] is False         # another arm
    assert judged(step, "pkg/beta.py")[0] is False                                           # another solution's code
    assert judged(step, "tests/test_alpha.py")[0] is False and judged(step, "pkg/conftest.py")[0] is False
    assert judged(step, "pkg/unowned_helper.py")[0] is False                                 # a plain helper the arm does not import


def test_a_helper_that_belongs_to_no_implementation_counts_when_the_arm_imports_it():
    built = staleness_fixture.build("touch-the-measured-file")
    cfg = config_module.load(built.root / "esoi.toml")
    live = built.root / "evaluation/components/alpha_eval/impls/live.py"
    live.write_text(live.read_text() + "\nfrom pkg import unowned_helper\n")
    cfg.staleness_rule = "import_closure"
    scope = staleness.scope_for(cfg, "alpha_eval", "live", "import_closure")
    assert "pkg/unowned_helper.py" in scope.closure and "pkg/util.py" not in scope.closure
    assert staleness.judge(cfg, scope, "pkg/unowned_helper.py") == (True, "imported by the arm")


def test_test_files_are_recognised_by_name_and_folder():
    for path in ("tests/test_a.py", "pkg/test_b.py", "pkg/c_test.py", "pkg/conftest.py", "pkg/fixtures/x.py", "evaluation/components/test_components.py"):
        assert staleness.is_test_file(path), path
    for path in ("pkg/contest.py", "pkg/testing_utils.py", "pkg/latest.py"):
        assert not staleness.is_test_file(path), path
