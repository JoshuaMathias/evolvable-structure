"""esoi.runtime.implementation_selection.lock: write, read, the lock layer of the cascade, diff with requirement changes, safe update, and the agent status plan.

A toy package is written to a temporary folder; its packaged snapshot is rewritten to stand for a newer release."""
import itertools
import json
import sys
import textwrap

import pytest

from esoi import __main__ as cli
from esoi.runtime.implementation_selection import lock
from esoi.runtime.implementation_selection import selection_cascade
from esoi.runtime.assemble_by_name import intent_map
from esoi.runtime.implementation_selection import selection_registry
from esoi.runtime.assemble_by_name.assemble import Assembler
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.structure.intent_registry.assembly_errors import LockError

COUNTER = itertools.count()
ARMS = '''
from typing import Protocol
from esoi import solution, implementation
from esoi.runtime.assemble_by_name.environment_needs.declarations import env, python

@solution("seat")
class Seat(Protocol):
    def go(self) -> str: ...

@solution("other")
class Other(Protocol):
    def go(self) -> str: ...

@implementation("seat", "old")
class Old:
    def go(self): return "old"

@implementation("seat", "keyed")
class Keyed:
    REQUIRES = (env("LOCKTOY_KEY", secret=True), python("json", "json"))
    def go(self): return "keyed"

@implementation("seat", "plain")
class Plain:
    REQUIRES = (python("json", "json"),)
    def go(self): return "plain"

@implementation("seat", "needsmod")
class NeedsMod:
    REQUIRES = (python("locktoy_missing_module", "locktoy-missing-module>=1"),)
    def go(self): return "needsmod"

@implementation("other", "x")
class X:
    def go(self): return "x"

@implementation("other", "y")
class Y:
    def go(self): return "y"
'''
INIT = '''
from pathlib import Path
from esoi.runtime.assemble_by_name.assemble import Assembler
def assembler():
    return Assembler(__name__, Path(__file__).parent, modules=(__name__ + ".arms",))
'''


def release(folder, scope, defaults, evidence=None):
    snapshot = {sid: {"default": arm, "modules": {}, **({"evidence": evidence[sid]} if evidence and sid in evidence else {})}
                for sid, arm in defaults.items()}
    (folder / scope / "esoi_selection.json").write_text(json.dumps(snapshot))


@pytest.fixture
def toy(tmp_path, monkeypatch):
    scope = f"locktoy{next(COUNTER)}"
    (tmp_path / scope).mkdir()
    (tmp_path / scope / "__init__.py").write_text(INIT)
    (tmp_path / scope / "arms.py").write_text(ARMS)
    monkeypatch.syspath_prepend(str(tmp_path))
    release(tmp_path, scope, {"seat": "old", "other": "x"},
            {"seat": {"verdict": "WIN", "detail": "old is better than plain", "p": 0.01}})
    parts = Assembler(scope, tmp_path / scope, modules=(f"{scope}.arms",))
    parts.prepare()
    yield scope, tmp_path, parts
    for key in [k for k in selection_registry.REGISTRY if k[0] == scope]:
        selection_registry.REGISTRY.pop(key)
    for name in [m for m in sys.modules if m == scope or m.startswith(scope + ".")]:
        sys.modules.pop(name)
    lock.CACHE.clear()


def newer(toy, defaults, evidence=None):
    """Ship a new release: the snapshot changes and the assembler reads it again."""
    scope, folder, parts = toy
    release(folder, scope, defaults, evidence)
    parts.memo.pop("packaged", None)


def test_write_records_the_arm_scope_chain_evidence_and_requirements(toy):
    scope, folder, parts = toy
    data = lock.write(parts, folder / "esoi.lock.json")
    assert data["schema"] == lock.SCHEMA and data["packages"] == {scope: "unversioned"}
    seat = data["solutions"]["seat"]
    assert (seat["arm"], seat["scope"], seat["chain"], seat["verdict"], seat["p"]) == ("old", scope, [scope], "WIN", 0.01)
    assert "old is better than plain" in seat["evidence"]
    assert data["solutions"]["other"]["arm"] == "x" and "no results recorded" in data["solutions"]["other"]["evidence"]
    assert json.loads((folder / "esoi.lock.json").read_text()) == data


def test_the_lock_is_a_layer_between_consumer_choices_and_the_defaults(toy):
    scope, folder, parts = toy
    lock.write(parts, folder / "esoi.lock.json")
    newer(toy, {"seat": "plain", "other": "y"})
    assert parts.choice("seat").name == "plain"   # no lock: the latest selection
    locked = AssemblyConfig(lock=folder / "esoi.lock.json")
    assert parts.choice("seat", config=locked).name == "old" and parts.choice("seat", config=locked).layer == "lock"
    assert "lock" in str(parts.explain("seat", config=locked)) and parts.assemble(locked)["seat"].go() == "old"
    mapping = AssemblyConfig(lock=json.loads((folder / "esoi.lock.json").read_text()))
    assert parts.choice("other", config=mapping).name == "x"
    mine = AssemblyConfig(lock=folder / "esoi.lock.json", selections={"seat": "keyed"})
    assert parts.choice("seat", config=mine).layer == "consumer selections"   # the consumer's own choice outranks the lock


def test_a_locked_arm_that_no_longer_exists_fails_with_a_named_error(toy):
    scope, folder, parts = toy
    data = lock.write(parts, folder / "esoi.lock.json")
    data["solutions"]["seat"]["arm"] = "gone"
    with pytest.raises(LockError) as caught:
        parts.choice("seat", config=AssemblyConfig(lock=data))
    text = str(caught.value)
    assert "'gone'" in text and "'seat'" in text and "esoi lock --update --solution seat" in text
    with pytest.raises(LockError, match="not an esoi lock"):
        lock.read({"nothing": 1})
    with pytest.raises(LockError, match="cannot be read"):
        lock.read(folder / "missing.json")


def test_diff_reports_arms_verdict_p_and_requirement_changes_without_values(toy):
    scope, folder, parts = toy
    path = folder / "esoi.lock.json"
    lock.write(parts, path)
    assert lock.diff(parts, path) == []
    newer(toy, {"seat": "keyed", "other": "y"}, {"seat": {"verdict": "WIN", "detail": "keyed is better than old", "p": 0.003}})
    changes = {c.solution: c for c in lock.diff(parts, path, environ={})}
    seat, other = changes["seat"], changes["other"]
    assert (seat.old_arm, seat.new_arm, seat.verdict, seat.p) == ("old", "keyed", "WIN", 0.003)
    assert {a["label"]: a["status"] for a in seat.added} == {"env LOCKTOY_KEY": "unmet", "python json": "met"}
    assert not seat.safe and other.safe and other.added == [] and other.removed == []
    met = {c.solution: c for c in lock.diff(parts, path, environ={"LOCKTOY_KEY": "SECRETVALUE123"})}
    assert met["seat"].safe and "SECRETVALUE123" not in json.dumps([c.to_dict() for c in met.values()])
    removed = lock.diff(parts, path, solutions=("seat",), environ={})
    assert [c.solution for c in removed] == ["seat"]


def test_removed_requirements_are_reported(toy):
    scope, folder, parts = toy
    newer(toy, {"seat": "keyed", "other": "x"})
    path = folder / "esoi.lock.json"
    lock.write(parts, path)
    newer(toy, {"seat": "old", "other": "x"})
    change = lock.diff(parts, path, environ={})[0]
    assert [r["label"] for r in change.removed] == ["env LOCKTOY_KEY", "python json"] and change.safe


def test_safe_update_moves_only_what_adds_no_unmet_requirement(toy):
    scope, folder, parts = toy
    path = folder / "esoi.lock.json"
    lock.write(parts, path)
    newer(toy, {"seat": "keyed", "other": "y"})
    done = lock.update(parts, path, safe=True, environ={})
    assert [c.solution for c in done.moved] == ["other"] and [c.solution for c in done.blocked] == ["seat"]
    saved = json.loads(path.read_text())
    assert saved["solutions"]["other"]["arm"] == "y" and saved["solutions"]["seat"]["arm"] == "old"
    assert any("LOCKTOY_KEY" in a["remedy"] for a in done.blocked[0].added)
    again = lock.update(parts, path, safe=True, environ={"LOCKTOY_KEY": "k"})   # the variable is now set: the blocked one is safe
    assert [c.solution for c in again.moved] == ["seat"] and json.loads(path.read_text())["solutions"]["seat"]["arm"] == "keyed"


def test_update_without_safe_moves_everything_and_the_lock_file_can_set_the_policy(toy):
    scope, folder, parts = toy
    path = folder / "esoi.lock.json"
    lock.write(parts, path)
    newer(toy, {"seat": "keyed", "other": "y"})
    assert [c.solution for c in lock.update(parts, path, environ={}).moved] == ["other", "seat"]
    lock.write(parts, path, update_policy="safe")
    newer(toy, {"seat": "old", "other": "y"})
    lock.write(parts, path)   # an existing policy is kept
    assert json.loads(path.read_text())["update"] == "safe"
    newer(toy, {"seat": "needsmod", "other": "x"})
    done = lock.update(parts, path, environ={})   # safe=None follows the file's policy
    assert [c.solution for c in done.moved] == ["other"] and [c.solution for c in done.blocked] == ["seat"]
    forced = lock.update(parts, path, safe=False, environ={})
    assert [c.solution for c in forced.moved] == ["seat"]
    with pytest.raises(LockError):
        lock.write(parts, path, update_policy="sometimes")


def test_status_exit_codes_and_the_plan(toy):
    scope, folder, parts = toy
    path = folder / "esoi.lock.json"
    lock.write(parts, path)
    code, plan = lock.status(parts, path, environ={})
    assert code == lock.EXIT_CURRENT == 0 and plan["state"] == "up-to-date" and plan["updates"] == [] and plan["schema"] == lock.STATUS_SCHEMA
    newer(toy, {"seat": "old", "other": "y"})
    code, plan = lock.status(parts, path, environ={}, package=scope, file=str(path))
    assert code == lock.EXIT_SAFE == 3 and plan["state"] == "safe-updates" and plan["apply_safe"].startswith("esoi lock --update --safe")
    newer(toy, {"seat": "keyed", "other": "y"})
    code, plan = lock.status(parts, path, environ={}, package=scope, file=str(path))
    assert code == lock.EXIT_BLOCKED == 4 and plan["state"] == "blocked"
    blocked = next(u for u in plan["updates"] if u["solution"] == "seat")
    assert blocked["blocked"] and [u["label"] for u in blocked["unmet"]] == ["env LOCKTOY_KEY"]
    assert [s["action"] for s in blocked["steps"]] == ["set-environment", "apply", "verify"]
    assert [s["order"] for s in blocked["steps"]] == [1, 2, 3] and blocked["steps"][0]["human"] is True
    assert blocked["apply"] == f"esoi lock --update --package {scope} --file {path} --solution seat"
    assert json.loads(json.dumps(plan)) == plan
    newer(toy, {"seat": "needsmod", "other": "x"})
    code, plan = lock.status(parts, path, environ={}, package=scope, file=str(path))
    steps = next(u for u in plan["updates"] if u["solution"] == "seat")["steps"]
    assert code == 4 and steps[0]["action"] == "install-packages" and steps[0]["command"] == f"esoi install --package {scope} --solution seat --yes"
    with pytest.raises(LockError):
        lock.status(parts, folder / "nothing.json")


def test_the_command_line_has_stable_exit_codes(toy, monkeypatch, capsys, tmp_path):
    scope, folder, parts = toy
    path = str(folder / "esoi.lock.json")
    (folder / "esoi.toml").write_text('package = "' + scope + '"\n')
    monkeypatch.chdir(folder)
    monkeypatch.delenv("LOCKTOY_KEY", raising=False)
    base = ["--config", str(folder), "lock", "--package", scope, "--file", path]
    assert cli.main(base) == 0 and "wrote" in capsys.readouterr().out
    assert cli.main(base + ["--status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "up-to-date"
    release(folder, scope, {"seat": "old", "other": "y"})   # the CLI asks the package for a fresh assembler, which reads the new snapshot
    assert cli.main(base + ["--status", "--json"]) == 3
    assert json.loads(capsys.readouterr().out)["state"] == "safe-updates"
    release(folder, scope, {"seat": "keyed", "other": "y"})
    assert cli.main(base + ["--status", "--json"]) == 4
    assert json.loads(capsys.readouterr().out)["updates"][1]["blocked"] is True
    assert cli.main(base + ["--diff"]) == 0 and "old -> keyed" in capsys.readouterr().out
    assert cli.main(base + ["--update", "--safe"]) == 0
    out = capsys.readouterr().out
    assert "moved other" in out and "left locked seat" in out and "1. set-environment" in out
    monkeypatch.setenv("LOCKTOY_KEY", "k")
    assert cli.main(base + ["--update", "--solution", "seat"]) == 0
    assert cli.main(base + ["--status"]) == 0
    capsys.readouterr()
    assert cli.main(["--config", str(folder), "lock", "--package", scope, "--file", str(tmp_path / "nowhere.json"), "--status"]) == 2
    assert cli.main(["--config", str(folder), "lock", "--package", "no_such_package_here", "--file", path]) == 2


def test_a_checkout_with_records_records_the_leaderboard_verdict_and_the_snapshot_carries_it(repo, monkeypatch):
    import os
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        for impl in ("live", "shout"):
            assert cli.main(["run", "greet_a_person", "--impl", impl, "--record"]) == 0
    finally:
        os.chdir(cwd)
    monkeypatch.syspath_prepend(str(repo))
    for name in [m for m in sys.modules if m == "demo" or m.startswith("demo.")]:
        sys.modules.pop(name)
    parts = Assembler("demo", repo / "demo", modules=("demo.greet",), records=repo)
    try:
        data = lock.write(parts, repo / "esoi.lock.json")
        entry = data["solutions"]["greet-a-person"]
        assert entry["verdict"] in ("WIN", "TIE", "LOSS") and entry["evidence"] and "no results recorded" not in entry["evidence"]
        from esoi.structure.intent_registry import config as config_module
        shipped = intent_map.snapshot(config_module.load(repo / "esoi.toml"))
        assert shipped["greet-a-person"]["evidence"]["verdict"] == entry["verdict"]
    finally:
        for name in [m for m in sys.modules if m == "demo" or m.startswith("demo.")]:
            sys.modules.pop(name)
        for key in [k for k in selection_registry.REGISTRY if k[0] == "demo"]:
            selection_registry.REGISTRY.pop(key)
        selection_registry.PROJECTS.clear()
