"""esoi follow: the parent's current selections against this repository's lock and overrides, judged on this repository's metric.

The child is the scaffolded example repository (solution ``greet-a-person``, arms ``live`` and ``shout``, results recorded); the
parent is a one-line snapshot of selections in a temporary folder, so two tiny packages stand for the hub and its child."""
import csv
import json
import shutil
import subprocess

import pytest

from esoi import __main__ as cli
from esoi.optimization.measurement_harness import interface as harness_interface
from esoi.runtime.consumer_check import follow
from esoi.structure.intent_registry import tables
from esoi.structure.intent_registry import config as config_module

SOLUTION = "greet-a-person"
POLITE = 'def build(meter):\n    def run(kind, args):\n        return {"text": "Hello, " + args["name"] + "!"}\n    return run\n'


def child(repo, selected="live", reasons="greeting-pass-rate", scores=None, extra_arms=(), paid=()):
    """The child's records: its selected arm, an override reason, and the pass count of each arm on the recorded cases."""
    folder = repo / "esoi"
    path = folder / "solutions.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for row in rows:
        if row["solution_id"] == SOLUTION:
            row["selected"] = selected
    tables.write_csv(path, cols, rows)
    tables.write_csv(folder / "overrides.csv", ["solution_id", "reason_ids"], [{"solution_id": SOLUTION, "reason_ids": reasons}] if reasons is not None else [])
    impls = repo / "evaluation" / "components" / "greet_a_person" / "impls"
    for arm in extra_arms:
        (impls / f"{arm}.py").write_text(("PAID = True\n" if arm in paid else "") + POLITE)
    results = tables.read_csv(repo / "evaluation/components/results.csv")
    header = tables.read_header(repo / "evaluation/components/results.csv")
    template = results[0]
    kept = [r for r in results if r["impl"] not in (scores or {})]
    for arm, passed in (scores or {}).items():
        kept.append(dict(template, impl=arm, passed=str(passed), dev=f"{passed}/2"))
    tables.write_csv(repo / "evaluation/components/results.csv", header, kept)
    return config_module.load(repo)


def parent(tmp_path, arm):
    path = tmp_path / "parent" / "esoi_selection.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({SOLUTION: {"default": arm}}))
    return str(path)


def only(report):
    [found] = report.findings
    return found


def test_keep_the_override_when_the_childs_metric_says_the_parents_arm_loses(repo, tmp_path):
    cfg = child(repo, "live", scores={"live": 2, "shout": 1})
    found = only(follow.follow(cfg, parent(tmp_path, "shout")))
    assert (found.verdict, found.kind, found.parent_arm, found.child_arm) == ("keep", "override", "shout", "live")
    assert "keep the override" in found.advice and "shout 0.5 against live 1" in found.advice


def test_adopt_when_the_parents_arm_holds_and_override_can_be_dropped_when_it_now_beats_the_childs(repo, tmp_path):
    held = only(follow.follow(child(repo, "live", scores={"live": 2, "shout": 2}), parent(tmp_path, "shout")))
    assert held.verdict == "adopt" and "drop the override" in held.advice and held.numbers
    beaten = only(follow.follow(child(repo, "live", scores={"live": 1, "shout": 2}), parent(tmp_path, "shout")))
    assert beaten.verdict == "drop" and beaten.advice.startswith("override can be dropped") and "shout 1 against live 0.5" in beaten.numbers


def test_a_lock_that_trails_the_parent_is_judged_the_same_way_and_the_advice_is_to_update_the_lock(repo, tmp_path):
    cfg = child(repo, "shout", reasons=None, scores={"live": 2, "shout": 1})   # the child follows the parent's shout, locked at live
    (repo / "esoi.lock.json").write_text(json.dumps({"schema": "esoi.lock/1", "solutions": {SOLUTION: {"arm": "live", "scope": "parent"}}}))
    found = only(follow.follow(cfg, parent(tmp_path, "shout")))
    assert (found.kind, found.verdict) == ("inherited", "keep") and "keep the lock" in found.advice
    cfg = child(repo, "shout", reasons=None, scores={"live": 1, "shout": 2})
    found = only(follow.follow(cfg, parent(tmp_path, "shout")))
    assert found.verdict == "drop" and "esoi lock --update --solution greet-a-person" in found.advice


def test_not_measured_lists_the_free_command_and_plan_and_json_run_nothing(repo, tmp_path, capsys):
    cfg = child(repo, "live", scores={"live": 2}, extra_arms=("polite",))
    results = (repo / "evaluation/components/results.csv").read_text()
    found = only(follow.follow(cfg, parent(tmp_path, "polite")))
    assert found.verdict == "not-measured" and found.steps[0].free
    assert found.steps[0].command == "esoi run greet_a_person --impl polite --record" and found.steps[0].cost.startswith("free")
    lines = []
    assert follow.run_cli(cfg, parent(tmp_path, "polite"), plan=True, say=lines.append) == 0
    assert any("would run: esoi run greet_a_person --impl polite --record" in line and "free" in line for line in lines)
    assert (repo / "evaluation/components/results.csv").read_text() == results   # nothing ran
    assert follow.run_cli(cfg, parent(tmp_path, "polite"), as_json=True, say=lines.append) == 0
    data = json.loads(lines[-1])
    assert data["schema"] == "esoi.follow/1" and data["solutions"][0]["verdict"] == "not-measured"
    assert data["solutions"][0]["commands"][0]["runs_with_run_free"] is True


def test_a_paid_arm_is_listed_with_its_cost_class_and_never_run_even_with_run_free(repo, tmp_path):
    cfg = child(repo, "live", scores={"live": 2}, extra_arms=("big",), paid=("big",))
    results = (repo / "evaluation/components/results.csv").read_text()
    lines = []
    assert follow.run_cli(cfg, parent(tmp_path, "big"), free=True, say=lines.append) == 0
    text = "\n".join(lines)
    assert "NOT MEASURED" in text and "paid (declares PAID = True)" in text and "--max-calls <budget>" in text and "running (free" not in text
    assert (repo / "evaluation/components/results.csv").read_text() == results
    assert only(follow.follow(cfg, parent(tmp_path, "big"))).steps[0].free is False


def test_run_free_records_a_free_arm_and_the_next_look_has_a_verdict(repo, tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=a@b.c", "-c", "user.name=t", "add", "-A"], cwd=repo, check=True)
    cfg = child(repo, "live", scores={"live": 2}, extra_arms=("polite",))
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=a@b.c", "-c", "user.name=t", "commit", "-qm", "x"], cwd=repo, check=True)
    lines = []
    assert follow.run_cli(cfg, parent(tmp_path, "polite"), free=True, say=lines.append) == 0
    assert any(line.startswith("running (free, offline): esoi run greet_a_person --impl polite") for line in lines)
    rows = list(csv.DictReader((repo / "evaluation/components/results.csv").open()))
    assert "polite" in {r["impl"] for r in rows}
    assert only(follow.follow(cfg, parent(tmp_path, "polite"))).verdict in ("adopt", "drop", "keep")


def test_an_unchanged_parent_prints_one_line_and_exits_zero(repo, tmp_path):
    cfg = child(repo, "live", reasons=None, scores={"live": 2})
    (repo / "esoi.lock.json").write_text(json.dumps({"schema": "esoi.lock/1", "solutions": {SOLUTION: {"arm": "live", "scope": "parent"}}}))
    lines = []
    assert follow.run_cli(cfg, parent(tmp_path, "live"), say=lines.append) == 0
    assert len(lines) == 2 and lines[1].startswith("nothing changed")


def test_a_malformed_override_is_reported_as_advice_and_never_fails(repo, tmp_path):
    cfg = child(repo, "live", reasons="not a valid id!; no-such-record", scores={"live": 2, "shout": 1})
    lines = []
    assert follow.run_cli(cfg, parent(tmp_path, "shout"), say=lines.append) == 0
    text = "\n".join(lines)
    assert "malformed override: " in text and "not a valid id!" in text and "no-such-record is no problem, ideal or metric" in text
    assert "KEEP THE OVERRIDE" in text   # the comparison still ran
    tables.write_csv(repo / "esoi" / "overrides.csv", ["solution_id", "reason_ids"], [{"solution_id": "", "reason_ids": "x"}, {"solution_id": "ghost", "reason_ids": "greeting-pass-rate"}])
    report = follow.follow(config_module.load(repo), parent(tmp_path, "shout"))
    assert any("no solution_id" in p for p in report.problems) and any("ghost" in p and "nothing to override" in p for p in report.problems)


def test_a_stale_row_is_marked_with_the_command_that_re_records_it(repo, tmp_path, monkeypatch):
    cfg = child(repo, "live", scores={"live": 2, "shout": 1})
    monkeypatch.setattr(follow, "stale_reason", lambda config, comp, row, strict=True: "measured code changed" if row["impl"] == "shout" else "")
    found = only(follow.follow(cfg, parent(tmp_path, "shout")))
    assert found.verdict == "keep" and "shout: measured code changed" in found.stale
    assert found.steps[0].command == "esoi run greet_a_person --impl shout --record" and found.steps[0].free


def test_the_command_reads_the_parent_table_and_an_unreadable_parent_is_the_only_error(repo, tmp_path, capsys):
    child(repo, "live", scores={"live": 2, "shout": 1})
    snapshot = parent(tmp_path, "shout")
    with open(repo / "esoi.toml", "a") as fh:
        fh.write(f'\n[parent]\nsnapshot = "{snapshot}"\n')
    assert cli.main(["--config", str(repo), "follow", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["solutions"][0]["verdict"] == "keep"
    assert cli.main(["--config", str(repo), "follow", "--parent", str(tmp_path / "nowhere")]) == 2
    assert "esoi follow:" in capsys.readouterr().out
