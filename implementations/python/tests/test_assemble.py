"""esoi.assemble: names only, safe loading, the cascade, needs from typed parameters, build order, startup failures.

The tests run against a small package written to a temporary folder (``esoitoy``: three seats and one default arm with a
packaged snapshot) and a consumer module (``esoitoyconsumer``) that registers arms of its own. Nothing is read from this
repository's records, the process environment or the network.
"""
import ast
import json
import shutil
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

import esoi
from esoi import assemble, runtime
from esoi.assemble import Assembler, AssemblyConfig, AssemblyError

SEATS = '''
import typing
from typing import runtime_checkable
from esoi import solution


@solution("toy-store")
@runtime_checkable
class Store(typing.Protocol):
    def put(self, key: str, value: str) -> None: ...
    def get(self, key: str) -> str: ...


@solution("toy-index")
@runtime_checkable
class Index(typing.Protocol):
    def find(self, key: str) -> str: ...


@solution("toy-report")
@runtime_checkable
class Report(typing.Protocol):
    def render(self) -> str: ...
'''
ARMS = '''
from esoi import implementation


@implementation("toy-store", "memory")
class Memory:
    def __init__(self):
        self.rows = {}

    def put(self, key, value):
        self.rows[key] = value

    def get(self, key):
        return self.rows[key]
'''
CONSUMER = '''
from esoitoy.seats import Index, Report, Store


class Mine:
    def __init__(self):
        self.rows = {}

    def put(self, key, value):
        self.rows[key] = value

    def get(self, key):
        return self.rows[key]


class StoreIndex:
    def __init__(self, store: Store, prefix: str = ""):
        self.store, self.prefix = store, prefix

    def find(self, key):
        return self.store.get(self.prefix + key)


class IndexReport:
    def __init__(self, index: Index):
        self.index = index

    def render(self):
        return "report:" + self.index.find("k")


class LoopA:
    def __init__(self, other: Report):
        self.other = other


class LoopB:
    def __init__(self, other: Index):
        self.other = other


class ReportNeedsStore:
    def __init__(self, store: Store):
        self.store = store


class StoreNeedsIndex:
    def __init__(self, index: Index):
        self.index = index


class IndexNeedsReport:
    def __init__(self, report: Report):
        self.report = report
'''
SNAPSHOT = {"toy-store": {"default": "memory", "modules": {"memory": "esoitoy.arms"}}}
STORE, INDEX, REPORT = "toy-store", "toy-index", "toy-report"


def write_package(site: Path) -> None:
    package = site / "esoitoy"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "seats.py").write_text(textwrap.dedent(SEATS))
    (package / "arms.py").write_text(textwrap.dedent(ARMS))
    (package / "esoi_selection.json").write_text(json.dumps(SNAPSHOT))


@pytest.fixture(scope="session")
def toy(tmp_path_factory):
    """The toy package and its consumer, imported once so their seats are declared before any test snapshots the registry."""
    site = tmp_path_factory.mktemp("site")
    write_package(site)
    (site / "esoitoyconsumer.py").write_text(textwrap.dedent(CONSUMER))
    sys.path.insert(0, str(site))
    import esoitoy.arms  # noqa: F401
    import esoitoyconsumer
    parts = Assembler("esoitoy", site / "esoitoy", seats_module="esoitoy.seats", noun="toy")
    parts.prepare()
    yield parts, esoitoyconsumer, site
    sys.path.remove(str(site))
    for name in [m for m in sys.modules if m.split(".")[0] in ("esoitoy", "esoitoyconsumer")]:
        sys.modules.pop(name)
    for key in [k for k in runtime.REGISTRY if k[0] == "esoitoy"]:
        runtime.REGISTRY.pop(key)


@pytest.fixture(autouse=True)
def keep_registry(request):
    """Registrations made in a test do not outlive it."""
    if "toy" not in request.fixturenames:
        yield
        return
    request.getfixturevalue("toy")
    before = {k: (dict(e.implementations), set(e.replaced), e.interface, e.origin) for k, e in runtime.REGISTRY.items()}
    yield
    for key in [k for k in runtime.REGISTRY if k not in before]:
        runtime.REGISTRY.pop(key)
    for key, (impls, replaced, interface, origin) in before.items():
        entry = runtime.REGISTRY[key]
        entry.implementations, entry.replaced, entry.interface, entry.origin = dict(impls), set(replaced), interface, origin


def wire(toy):
    parts, consumer, _ = toy
    parts.register(INDEX, "acme-index", consumer.StoreIndex)
    parts.register(REPORT, "acme-report", consumer.IndexReport)
    return AssemblyConfig(seats=(REPORT,), selections={INDEX: "acme-index", REPORT: "acme-report"})


# names

def test_name_pattern():
    for good in ("a", "tier_selector", "x-1", "0abc"):
        assert assemble.check_name(good) == good
    for bad in ("", "-a", "_a", "a.b", "a:b", "A", "a b", "a\n", "../x", None, 3):
        with pytest.raises(AssemblyError):
            assemble.check_name(bad)


def test_a_consumer_registers_a_name_it_owns_and_selects_it_on_its_own_config(toy):
    parts, consumer, _ = toy
    parts.register(STORE, "acme-memory", consumer.Mine)
    assert parts.names(STORE) == ["acme-memory", "memory"]
    assert parts.resolve(STORE, "acme-memory") is consumer.Mine
    assert parts.choice(STORE, config=AssemblyConfig(selections={STORE: "acme-memory"})).layer == "consumer selections"


def test_replacing_or_shadowing_a_package_declared_name_raises_but_a_consumer_may_replace_its_own(toy):
    parts, consumer, _ = toy
    for replace in (False, True):
        with pytest.raises(AssemblyError, match="declared by the toy"):
            parts.register(STORE, "memory", consumer.Mine, replace=replace)
    assert parts.resolve(STORE).__name__ == "Memory"
    parts.register(STORE, "acme-memory", consumer.Mine)
    parts.register(STORE, "acme-memory", consumer.StoreIndex, replace=True)
    assert parts.resolve(STORE, "acme-memory") is consumer.StoreIndex


def test_register_validates_the_solution_and_the_name(toy):
    parts, consumer, _ = toy
    for sid, name in (("no-such-seat", "ok"), (STORE, "has.dot"), (STORE, "os:system"), (STORE, "Upper")):
        with pytest.raises(AssemblyError):
            parts.register(sid, name, consumer.Mine)


def test_a_name_that_is_not_listed_is_an_error_naming_the_choices(toy):
    parts, consumer, _ = toy
    parts.register(STORE, "acme-memory", consumer.Mine)
    with pytest.raises(AssemblyError) as caught:
        parts.resolve(STORE, "other")
    message = str(caught.value)
    assert STORE in message and "esoitoy" in message and "explicit name" in message and "acme-memory" in message
    with pytest.raises(AssemblyError, match="consumer selections"):
        parts.choice(STORE, config=AssemblyConfig(selections={STORE: "other"}))


def test_the_cascade_is_explicit_then_selections_then_the_package_default(toy):
    parts, consumer, _ = toy
    parts.register(STORE, "acme-memory", consumer.Mine)
    assert (parts.choice(STORE).name, parts.choice(STORE).layer) == ("memory", "toy default")
    assert parts.choice(STORE, config=AssemblyConfig(selections={STORE: "acme-memory"})).name == "acme-memory"
    both = AssemblyConfig(selections={STORE: "acme-memory"}, names={STORE: "memory"})
    assert (parts.choice(STORE, config=both).name, parts.choice(STORE, config=both).layer) == ("memory", "explicit name")
    assert parts.choice(STORE, "memory", AssemblyConfig(selections={STORE: "acme-memory"})).layer == "explicit name"


# safe loading

HOSTILE_NAMES = ("os:system", "os.system", "json.tool", "../x.py", "a/b", "evil;rm", "x:y")


@pytest.mark.parametrize("bad", HOSTILE_NAMES)
def test_a_config_value_that_is_an_import_path_is_rejected_before_esoi(bad, toy, monkeypatch):
    parts = toy[0]

    def esoi_must_not_see_it(*args, **kwargs):
        raise AssertionError("esoi saw the value")
    monkeypatch.setattr(runtime, "choose", esoi_must_not_see_it)
    monkeypatch.setattr(runtime, "resolve", esoi_must_not_see_it)
    for config in (AssemblyConfig(names={STORE: bad}), AssemblyConfig(selections={STORE: bad}),
                   AssemblyConfig(selection_environ={"ESOI_SELECT_ESOITOY_TOY_STORE": bad})):
        with pytest.raises(AssemblyError, match="rejected"):
            parts.choice(STORE, config=config)
        with pytest.raises(AssemblyError, match="rejected"):
            parts.assemble(AssemblyConfig(seats=(STORE,), names=config.names, selections=config.selections,
                                          selection_environ=config.selection_environ))
    with pytest.raises(AssemblyError, match="rejected"):
        parts.resolve(STORE, bad)


def test_a_valid_looking_name_that_is_not_listed_is_refused_not_imported(toy):
    with pytest.raises(AssemblyError, match="unknown implementation"):
        toy[0].resolve(STORE, "os")


@pytest.mark.parametrize("module", ["os", "json", "esoitoy", "esoitoy_evil", "esoitoy..x", ".esoitoy.arms", "", None])
def test_safe_module_rejects_anything_not_inside_the_package(module, toy):
    with pytest.raises(AssemblyError):
        toy[0].safe_module(module)


def test_safe_module_accepts_the_packages_own_modules_and_refuses_one_outside_its_folder(toy, tmp_path):
    parts = toy[0]
    assert parts.safe_module("esoitoy.arms") == "esoitoy.arms"
    elsewhere = Assembler("esoitoy", tmp_path, "esoitoy.seats")
    with pytest.raises(AssemblyError, match="not inside the installed esoitoy package"):
        elsewhere.safe_module("esoitoy.arms")


ATTEMPT = """
import json, os, sys
sys.path[:] = [{site!r}, {esoi_path!r}] + [p for p in sys.path if 'site-packages' not in p and p]
marker, attacker = {marker!r}, {attacker!r}
{setup}
from pathlib import Path
from esoi.assemble import Assembler, AssemblyError
parts = Assembler("esoitoy", Path({site!r}) / "esoitoy", "esoitoy.seats")
{after}
try:
    parts.resolve('toy-store')
    raised = ''
except AssemblyError as error:
    raised = str(error)
print(json.dumps(dict(raised=raised, executed=os.path.exists(marker))))
"""


def attempt(tmp_path, module, setup="", after=""):
    """Run a fresh interpreter on a copy of the package whose packaged snapshot names ``module`` for the default arm."""
    site = tmp_path / "site"
    write_package(site)
    snapshot = {"toy-store": {"default": "memory", "modules": {"memory": module}}}
    (site / "esoitoy" / "esoi_selection.json").write_text(json.dumps(snapshot))
    attacker, marker = tmp_path / "attacker", tmp_path / "executed"
    (attacker / "esoitoy").mkdir(parents=True)
    payload = f"open({str(marker)!r}, 'w').write('x')\n"
    for name in ("evil.py", "esoitoy_evil.py", "unused.py"):
        (attacker / name).write_text(payload)
    (attacker / "esoitoy" / "evil.py").write_text(payload)
    code = ATTEMPT.format(site=str(site), esoi_path=str(Path(esoi.__file__).resolve().parent.parent), marker=str(marker),
                          attacker=str(attacker), setup=setup, after=after)
    done = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_a_snapshot_module_of_the_standard_library_is_rejected(tmp_path):
    out = attempt(tmp_path, "os")
    assert "rejected" in out["raised"] and not out["executed"]


def test_a_snapshot_module_that_only_looks_like_the_package_is_rejected(tmp_path):
    out = attempt(tmp_path, "esoitoy_evil", setup="sys.path.insert(0, attacker)")
    assert "rejected" in out["raised"] and not out["executed"]


def test_a_module_found_outside_the_package_directory_is_rejected(tmp_path):
    out = attempt(tmp_path, "esoitoy.evil", after="import esoitoy; esoitoy.__path__.append(attacker + '/esoitoy')")
    assert "not inside the installed esoitoy package" in out["raised"] and not out["executed"]


def test_the_packaged_default_resolves_from_a_copy_outside_any_repository(tmp_path):
    out = attempt(tmp_path, "esoitoy.arms")
    assert out["raised"] == "" and not out["executed"]


# the environment

def test_the_process_environment_changes_nothing(toy, monkeypatch, tmp_path):
    parts = toy[0]
    monkeypatch.setenv("ESOI_SELECT_ESOITOY_TOY_STORE", "evil")
    monkeypatch.setenv("ESOI_SELECT_TOY_STORE", "evil")
    monkeypatch.setenv(runtime.ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(runtime.SNAPSHOT_ENV, str(tmp_path / "nope.json"))
    assert parts.choice(STORE).name == "memory" and parts.resolve(STORE).__name__ == "Memory"


def test_selection_environ_is_the_only_control(toy):
    parts = toy[0]
    assert parts.choice(STORE, config=AssemblyConfig(selection_environ={"ESOI_SELECT_ESOITOY_TOY_STORE": "memory"})).layer \
        == "selection environ"
    for bad in ({runtime.ROOT_ENV: "/x"}, {runtime.SNAPSHOT_ENV: "/x"}):
        with pytest.raises(AssemblyError, match="may not set"):
            parts.choice(STORE, config=AssemblyConfig(selection_environ=bad))


def test_the_module_reads_no_environment_and_imports_no_consumer():
    tree = ast.parse(Path(assemble.__file__).read_text())
    allowed = set(sys.stdlib_module_names) | {"esoi"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in ("environ", "getenv", "putenv"), node.lineno
        if isinstance(node, ast.Import):
            assert {a.name.split(".")[0] for a in node.names} <= allowed
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            assert node.module.split(".")[0] in allowed


# needs and assembly

def test_needs_read_from_typed_parameters(toy):
    parts, consumer, _ = toy
    assert parts.needs_of(consumer.StoreIndex) == {"store": STORE}
    assert parts.needs_of(consumer.IndexReport) == {"index": INDEX}
    assert parts.needs_of(consumer.Mine) == {} and parts.needs_of(object()) == {}


def test_objects_are_built_in_dependency_order_and_the_needs_are_injected(toy):
    parts = toy[0]
    system = parts.assemble(wire(toy))
    assert system.seats() == [STORE, INDEX, REPORT]
    system[STORE].put("k", "v")
    assert system[REPORT].render() == "report:v" and system[INDEX].store is system[STORE]


def test_a_provided_object_wins_for_its_seat_and_must_satisfy_it(toy):
    parts, consumer, _ = toy
    mine = consumer.Mine()
    mine.put("k", "mine")
    system = parts.assemble(wire(toy), provided={STORE: mine})
    assert system[STORE] is mine and system[REPORT].render() == "report:mine"
    assert "layer: consumer provided" in system.reason_by_seat[STORE]
    with pytest.raises(AssemblyError, match="does not satisfy Store"):
        parts.assemble(wire(toy), provided={STORE: object()})
    with pytest.raises(AssemblyError, match="unknown solution"):
        parts.assemble(wire(toy), provided={"no-such-seat": object()})


def test_an_unmet_need_fails_at_startup_naming_the_chain(toy):
    parts, consumer, _ = toy
    parts.register(REPORT, "acme-report", consumer.IndexReport)
    with pytest.raises(AssemblyError) as caught:
        parts.assemble(AssemblyConfig(seats=(REPORT,), selections={REPORT: "acme-report"}))
    assert "toy-report (acme-report) needs toy-index: no arm, not provided" in str(caught.value)
    assert "toy-report -> toy-index" in str(caught.value)
    with pytest.raises(AssemblyError, match="toy-index: no arm, not provided"):
        parts.assemble(AssemblyConfig(seats=(INDEX,)))


def test_a_cycle_fails_at_startup_naming_the_ring(toy):
    parts, consumer, _ = toy
    parts.register(INDEX, "loop-a", consumer.LoopA)
    parts.register(REPORT, "loop-b", consumer.LoopB)
    with pytest.raises(AssemblyError, match="dependency cycle: toy-index -> toy-report -> toy-index"):
        parts.assemble(AssemblyConfig(seats=(INDEX,), selections={INDEX: "loop-a", REPORT: "loop-b"}))


def test_a_longer_cycle_names_every_seat(toy):
    parts, consumer, _ = toy
    parts.register(REPORT, "r2", consumer.ReportNeedsStore)
    parts.register(STORE, "s2", consumer.StoreNeedsIndex)
    parts.register(INDEX, "i2", consumer.IndexNeedsReport)
    config = AssemblyConfig(seats=(REPORT,), selections={REPORT: "r2", STORE: "s2", INDEX: "i2"})
    with pytest.raises(AssemblyError, match="toy-report -> toy-store -> toy-index -> toy-report"):
        parts.assemble(config)


def test_options_reach_the_constructor_and_unknown_options_fail(toy):
    parts = toy[0]
    base = wire(toy)
    system = parts.assemble(AssemblyConfig(seats=base.seats, selections=base.selections, options={INDEX: {"prefix": "p-"}}))
    assert system[INDEX].prefix == "p-"
    with pytest.raises(AssemblyError, match="no option"):
        parts.assemble(AssemblyConfig(seats=base.seats, selections=base.selections, options={INDEX: {"nope": 1}}))


def test_the_reason_line_names_seat_arm_layer_version_and_hash(toy):
    system = toy[0].assemble(wire(toy))
    assert system.reason_by_seat[INDEX].startswith("toy-index -> acme-index (layer: consumer selections, package version ")
    assert "config hash " in system.reason_by_seat[INDEX] and len(system.reasons) == 3


def test_the_package_default_builds_without_a_consumer(toy):
    system = toy[0].assemble(AssemblyConfig())
    assert system.seats() == [STORE] and type(system[STORE]).__name__ == "Memory"
    assert "layer: toy default" in system.reasons[0]


def test_two_consumers_with_different_selections_do_not_affect_each_other(toy):
    parts, consumer, _ = toy
    parts.register(STORE, "first", type("First", (), {"put": lambda s, k, v: None, "get": lambda s, k: k}))
    parts.register(STORE, "second", type("Second", (), {"put": lambda s, k, v: None, "get": lambda s, k: k}))
    one = parts.assemble(AssemblyConfig(seats=(STORE,), selections={STORE: "first"}))
    two = parts.assemble(AssemblyConfig(seats=(STORE,), selections={STORE: "second"}))
    default = parts.assemble(AssemblyConfig(seats=(STORE,)))
    assert (type(one[STORE]).__name__, type(two[STORE]).__name__, type(default[STORE]).__name__) == ("First", "Second", "Memory")
    assert one.choice(STORE).name == "first" and two.choice(STORE).name == "second"


def test_the_result_is_frozen_and_threads_can_use_it(toy):
    system = toy[0].assemble(wire(toy))
    with pytest.raises(TypeError):
        system.objects["x"] = 1
    system[STORE].put("k", "v")
    seen = []
    threads = [threading.Thread(target=lambda: seen.append(system[REPORT].render())) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert seen == ["report:v"] * 8
    with pytest.raises(AssemblyError, match="was not assembled"):
        system["nothing"]


# the records: uses_solution_ids against the declared needs

def planted(selected="x", tags="", uses="", sid="a", other_sid="b"):
    solutions = [{"solution_id": sid, "selected": selected, "tags": tags}, {"solution_id": other_sid, "selected": "y", "tags": ""}]
    impls = [{"implementation_id": f"{sid}:x", "solution_id": sid, "uses_solution_ids": uses},
             {"implementation_id": f"{other_sid}:y", "solution_id": other_sid, "uses_solution_ids": ""}]
    return solutions, impls


def test_a_planted_mismatch_between_uses_and_parameters_is_reported():
    solutions, impls = planted()
    bad = assemble.problems(solutions, impls, {"a:x": {"b"}, "b:y": set()})
    assert any("uses_solution_ids is empty but its constructor parameters need ['b']" in line for line in bad)
    solutions, impls = planted(uses="b")
    assert assemble.problems(solutions, impls, {"a:x": {"b"}, "b:y": set()}) == []
    assert any("need nothing" in line for line in assemble.problems(solutions, impls, {"a:x": set(), "b:y": set()}))


def test_a_planted_cycle_is_reported():
    solutions, impls = planted(uses="b")
    impls[1]["uses_solution_ids"] = "a"
    bad = assemble.problems(solutions, impls, {"a:x": {"b"}, "b:y": {"a"}})
    assert any("default arms form a cycle: a -> b -> a" in line for line in bad)


def test_a_need_on_a_seat_with_no_arm_is_reported_unless_consumer_provided():
    needs = {"a:x": {"b"}, "b:y": set()}
    solutions, impls = planted(uses="b")
    solutions[1]["selected"] = ""
    assert any("has no default arm and is not tagged consumer-provided" in line for line in assemble.problems(solutions, impls, needs))
    solutions[1]["tags"] = "external;consumer-provided"
    assert assemble.problems(solutions, impls, needs) == []
    solutions[1]["tags"] = '[{"tag": "consumer-provided", "risk_ids": []}]'   # the JSON form of the cell reads the same
    assert assemble.problems(solutions, impls, needs) == []
    solutions[1]["selected"] = "y"
    assert any("tagged consumer-provided but has a default arm" in line for line in assemble.problems(solutions, impls, needs))


def test_a_need_on_an_unknown_seat_is_reported():
    solutions, impls = planted(uses="zzz")
    assert any("zzz, which is no solution" in line for line in assemble.problems(solutions, impls, {"a:x": {"zzz"}, "b:y": set()}))


def test_sync_uses_writes_the_column_from_the_parameters_and_uses_problems_then_finds_none(toy, tmp_path):
    parts, consumer, _ = toy
    parts.register(INDEX, "acme-index", consumer.StoreIndex)
    folder = tmp_path / "records"
    folder.mkdir()
    (folder / "solutions.csv").write_text(f"solution_id,selected,tags\n{STORE},memory,\n{INDEX},,consumer-provided\n")
    (folder / "implementations.csv").write_text(
        f"implementation_id,solution_id,uses_solution_ids\n{STORE}:memory,{STORE},\n{INDEX}:acme-index,{INDEX},\n")
    # acme-index is registered by the consumer, so it is declared in code; load it through the registry by name
    assert any("constructor parameters need ['toy-store']" in line for line in parts.uses_problems(folder))
    parts.sync_uses(folder)
    assert (folder / "implementations.csv").read_text().splitlines()[-1] == f"{INDEX}:acme-index,{INDEX},{STORE}"
    assert parts.uses_problems(folder) == []
