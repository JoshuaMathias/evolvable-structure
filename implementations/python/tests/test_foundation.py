"""A metric builds on the metric of the library it depends on: reuse when the digests match, never mix a stale result, inherit gates."""
import csv
import itertools
import os
import subprocess
import sys

import pytest

from esoi.optimization.measurement_harness import access
from esoi.optimization.measurement_harness import case_loading
from esoi.optimization.measurement_harness import component_folder
from esoi.optimization.measurement_harness import run_component
from esoi.optimization.measurement_harness import run_errors
from esoi.optimization.measurement_harness import stale_reasons
from esoi.optimization.leaderboard import cascade_stages, stage_standings
from esoi.structure.intent_registry import config as config_module
from esoi.runtime.consumer_check import foundation

COUNTER = itertools.count()
GIT = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.org", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.org")
SCORE = ('import os\n\ndef score_case(fn, case):\n    with open(os.environ["FOUNDATION_MARK"], "a") as fh:\n        fh.write(case["id"] + "\\n")\n'
         '    return dict(ok=bool(fn(case)), note="n")\n')
ARM = 'def build(meter):\n    return lambda case: case["n"] % 2 == 0\n'


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=GIT)


def commit(root):
    (root / ".gitignore").write_text("__pycache__/\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "x")


def component(root, name, cases, score, arms):
    folder = root / "evaluation" / "components" / name
    (folder / "impls").mkdir(parents=True, exist_ok=True)
    for init in (folder / "__init__.py", folder / "impls" / "__init__.py"):
        init.write_text("")
    (folder / "score.py").write_text(score)
    (folder / "cases.json").write_text(cases)
    for arm, text in arms.items():
        (folder / "impls" / f"{arm}.py").write_text(text)


def cases_text(ids):
    return "[" + ",".join(f'{{"id": "{i}", "n": {i[1:]}}}' for i in ids) + "]"


@pytest.fixture
def world(tmp_path, monkeypatch):
    n = next(COUNTER)
    lib, app = tmp_path / "lib", tmp_path / "app"
    mark = tmp_path / "mark.txt"
    monkeypatch.setenv("FOUNDATION_MARK", str(mark))
    toml = 'package = "nopkg"\nstaleness_rule = "repo_wide"\ncode_paths = ["evaluation/components"]\n'
    foundation_name, own_name = f"core{n}", f"app{n}"
    for root in (lib, app):
        root.mkdir()
        git(root, "init", "-q")
    (lib / "esoi.toml").write_text(toml)
    component(lib, foundation_name, cases_text(["c1", "c2", "c3", "c4"]), SCORE, {"good": ARM, "other": ARM})
    commit(lib)
    lines = []
    fconf = config_module.load(lib)
    component_folder.prepare_path(fconf)
    import importlib
    scorer = importlib.import_module(f"{foundation_name}.score").score_case
    run_component.run_component(foundation_name, scorer, ["--impl", "good", "--record"], fconf, lines.append)   # the foundation measures its arm
    commit(lib)
    mark.unlink()
    (app / "esoi.toml").write_text(toml + f'[balance.{own_name}]\nweights = {{ accuracy = 0.7, cost = 0.15, time = 0.15 }}\ncost_per_case_usd = 1\n'
                                   f'seconds_per_case = 100\n[builds_on.{own_name}.core]\nrepo = "../lib"\ncomponent = "{foundation_name}"\nshare = 0.6\n')
    own_score = ('def score_case(fn, case):\n    return dict(ok=bool(fn(case)))\n\n\ndef foundation_fn(name, fn):\n    return fn\n')
    component(app, own_name, '[{"id": "x1", "n": 2}, {"id": "x2", "n": 4}]', own_score,
              {"good": 'FOUNDATION_ARM = "good"\n' + ARM, "plain": ARM})
    commit(app)
    return dict(lib=lib, app=app, mark=mark, foundation=foundation_name, own=own_name, fconf=fconf, aconf=config_module.load(app))


def run(world, impl, *extra):
    component_folder.prepare_path(world["aconf"])
    import importlib
    scorer = importlib.import_module(f"{world['own']}.score").score_case
    lines = []
    summary, _ = run_component.run_component(world["own"], scorer, ["--impl", impl, *extra], world["aconf"], lines.append)
    return summary, lines


def marked(world):
    return world["mark"].read_text().split() if world["mark"].exists() else []


def test_matching_digests_reuse_the_foundations_results_and_run_none_of_its_cases(world):
    summary, lines = run(world, "good", "--record")
    assert marked(world) == []                         # the foundation's scorer never ran: its recorded cases were reused
    assert summary["cases"] == 6 and summary["accuracy"] == 0.7   # 0.6 * (2 of 4) + 0.4 * (2 of 2)
    assert summary["builds_on"].startswith(f"core={world['foundation']}:good@")
    assert any("reused 4 case(s)" in line and "none run again" in line for line in lines)
    assert any("share-weighted equivalent" in line and "raw counts are 4/6" in line for line in lines)   # the weighted headline says how it differs from dev + held-out
    recorded = list(csv.DictReader(world["aconf"].results_path.open()))[-1]
    assert recorded["builds_on"] == summary["builds_on"]
    assert stale_reasons.stale_reason(world["aconf"], world["own"], recorded) == ""


def test_the_foundations_cases_are_not_copied_into_the_consumer(world):
    ids = [c["id"] for c in case_loading.load_cases(world["own"], world["aconf"])]
    assert ids == ["x1", "x2"]


def test_a_changed_foundation_is_run_through_its_own_scorer_never_mixed_stale(world):
    (world["lib"] / "evaluation" / "components" / world["foundation"] / "cases.json").write_text(cases_text(["c1", "c2", "c3", "c4", "c6"]))
    commit(world["lib"])                               # a new foundation case: the recorded result describes other cases
    summary, lines = run(world, "good")
    assert marked(world) == ["c1", "c2", "c3", "c4", "c6"]   # the foundation's scorer ran, on the foundation's current cases
    assert summary["cases"] == 7 and any("other cases" in line for line in lines)
    assert "run through the foundation's scorer" in summary["details"]


def test_on_stale_report_refuses_instead_of_mixing(world):
    path = world["app"] / "esoi.toml"
    path.write_text(path.read_text() + 'on_stale = "report"\n')
    (world["lib"] / "evaluation" / "components" / world["foundation"] / "impls" / "good.py").write_text(ARM + "# changed\n")
    commit(world["lib"])
    world["aconf"] = config_module.load(world["app"])
    with pytest.raises(run_errors.RunError, match="cannot be reused"):
        run(world, "good")
    assert marked(world) == []


def test_an_arm_that_names_no_foundation_arm_runs_the_foundations_cases_through_the_foundations_scorer(world):
    summary, _ = run(world, "plain")
    assert marked(world) == ["c1", "c2", "c3", "c4"] and summary["cases"] == 6


def test_a_composed_row_goes_stale_when_the_foundation_arms_code_changes(world):
    summary, _ = run(world, "good", "--record")
    row = list(csv.DictReader(world["aconf"].results_path.open()))[-1]
    (world["lib"] / "evaluation" / "components" / world["foundation"] / "impls" / "good.py").write_text(ARM + "# better\n")
    commit(world["lib"])
    assert "foundation core changed" in stale_reasons.stale_reason(world["aconf"], world["own"], row)


def test_a_sampled_run_scores_the_consumers_own_cases_only(world):
    summary, lines = run(world, "good", "--sample", "1")
    assert summary["cases"] == 1 and marked(world) == [] and "builds_on" not in summary
    assert any("own cases only" in line for line in lines)


def test_shares_must_leave_the_consumer_something(world):
    path = world["app"] / "esoi.toml"
    path.write_text(path.read_text().replace("share = 0.6", "share = 1.0"))
    found = foundation.problems(config_module.load(world["app"]))
    assert any("between 0 and 1" in line for line in found) and any("add up to" in line for line in found)


def test_blend_weights_shares_and_renormalises_over_the_parts_present():
    cfg = [foundation.Foundation("c", "a", None, "t", 0.5), foundation.Foundation("c", "b", None, "t", 0.25)]
    own = dict(cases=2, passed=2, model_calls=0, tokens_in=0, tokens_out=0, seconds=0.0, dev="2/2", heldout="0/0")
    both = foundation.blend(own, 0.0, [foundation.Part("a", "x", 4, 2), foundation.Part("b", "y", 4, 4)], cfg, None)
    assert both["passed"] == round((0.5 * 0.5 + 0.25 * 1.0 + 0.25 * 1.0) * 10)
    alone = foundation.blend(dict(own, cases=0, passed=0), 0.0, [foundation.Part("a", "x", 4, 2)], cfg, None)
    assert alone["passed"] == 2                           # one part present: its share renormalises to the whole


def test_an_inheriting_stage_needs_the_foundations_stage_and_a_gate_beside_it_only_tightens():
    stages, errors = cascade_stages.parse("safety [inherits=safety] > whole [sample=full | real=no | gate=all-pass | inherits=quality]")
    assert errors == [] and stages[0].unrun and not stages[1].unrun
    stuck = stage_standings.next_stage(stages, stage_standings.Standing("a"), inherited=lambda stage: (stage.inherits != "safety", "not run"))
    assert stuck[0] is None and "foundation's safety stage has not passed" in stuck[1]
    assert stage_standings.next_stage(stages, stage_standings.Standing("a"), inherited=lambda stage: (True, ""))[0] == 1   # now it is the consumer's own stage to run
    theirs = cascade_stages.parse("q [gate=all-pass | min-pass-rate=0.9] > w")[0][0]
    assert cascade_stages.loosens(cascade_stages.parse("q [gate=competitive | inherits=q] > w")[0][0], theirs)
    assert cascade_stages.loosens(cascade_stages.parse("q [min-pass-rate=0.5 | inherits=q] > w")[0][0], theirs)
    assert cascade_stages.loosens(cascade_stages.parse("q [gate=all-pass | min-pass-rate=0.95 | inherits=q] > w")[0][0], theirs) == ""
    assert cascade_stages.loosens(cascade_stages.parse("q [inherits=q] > w")[0][0], theirs) == ""


def test_the_inherited_gate_reads_the_foundations_cascade_and_results(world):
    lib = world["lib"]
    (lib / "esoi").mkdir(exist_ok=True)
    fname = world["foundation"]
    (lib / "esoi" / "metrics.csv").write_text(
        "metric_id,solution_ids,command,cascading_conditionals\n"
        f'm1,s1,"esoi run {fname} --impl good",offline [sample=full | real=no | gate=all-pass] > whole [sample=full | real=no]\n')
    commit(lib)
    gate = foundation.inherited_gate(world["aconf"], world["own"], "good")
    stage = cascade_stages.parse("offline [inherits=offline] > mine [sample=full | gate=all-pass]")[0][0]
    met, why = gate(stage)
    assert not met and "not every case passed" in why      # the recorded foundation arm passes 2 of 4, so its all-pass gate is not met
    other = foundation.inherited_gate(world["aconf"], world["own"], "plain")
    assert other(stage)[0] is False and "no foundation" in other(stage)[1]


def test_source_access_is_priced_bounded_and_only_tightened():
    table = {"source_access": {"usd_per_record": 0.01, "usd_per_call": 0.1, "max_records_per_request": 10, "allowed_scopes": ["workspace"]}}
    assert access.price(access.Reads(records=5, calls=2), table) == pytest.approx(0.25)
    assert access.violation(access.Reads(records=11, scopes={"workspace"}), table).startswith("the request read 11 records")
    assert "outside the allowed scopes" in access.violation(access.Reads(records=1, scopes={"workspace", "notes"}), table)
    assert "whole source" in access.violation(access.Reads(full_scan=True, scopes={"workspace"}), table)
    assert access.violation(access.Reads(records=10, scopes={"workspace"}), table) == ""
    tighter = {"source_access": {"max_records_per_request": 5, "allowed_scopes": ["workspace"]}}
    looser = {"source_access": {"max_records_per_request": 50, "allowed_scopes": ["workspace", "files"], "forbid_full_scan": False}}
    assert access.loosening(tighter, table) == []
    assert len(access.loosening(looser, table)) == 3
    assert access.loosening(None, table) == []          # a consumer that writes nothing inherits the foundation's table unchanged
    with pytest.raises(ValueError):
        access.settings({"source_access": {"max_record_per_request": 1}})


def test_a_request_that_breaks_a_read_gate_fails_and_reads_are_priced(tmp_path):
    root = tmp_path
    (root / "esoi.toml").write_text('package = "nopkg"\n[balance.reads_comp]\ncost_per_case_usd = 1\nseconds_per_case = 100\n'
                                    '[balance.reads_comp.source_access]\nusd_per_record = 0.5\nmax_records_per_request = 3\n')
    component(root, "reads_comp", '[{"id": "a", "n": 2}, {"id": "b", "n": 9}]',
              'def score_case(fn, case):\n    return dict(ok=bool(fn(case)))\n',
              {"reader": 'def build(meter):\n    def run(case):\n        meter.read(records=case["n"])\n        return True\n    return run\n'})
    cfg = config_module.load(root)
    component_folder.prepare_path(cfg)
    import importlib
    scorer = importlib.import_module("reads_comp.score").score_case
    summary, rows = run_component.run_component("reads_comp", scorer, ["--impl", "reader", "--keep-going"], cfg, lambda text: None)
    assert rows[0]["ok"] is True
    assert rows[1]["ok"] is False and "over max_records_per_request" in rows[1]["note"]
    assert summary["cli_reported_cost_usd"] == pytest.approx(5.5)   # (2 + 9 records) at 0.5


def test_a_configured_prefix_names_the_foundation_arm_of_a_delegating_arm(world):
    path = world["app"] / "esoi.toml"
    path.write_text(path.read_text() + 'arm_prefix = "lib_"\n')
    (world["app"] / "evaluation" / "components" / world["own"] / "impls" / "lib_good.py").write_text(ARM)
    config = config_module.load(world["app"])
    assert foundation.declared_arms(config, world["own"], "lib_good") == {"core": "good"}
    assert foundation.declared_arms(config, world["own"], "plain") == {}
