"""esoi.assemble: names only, safe loading, the cascade, needs from typed parameters, build order, startup failures.

The tests run against a small package written to a temporary folder (``esoitoy``: three solutions and one default arm with a
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation" / "components"))
import assemble_fixture  # noqa: E402
from assemble_fixture import ESOI_PATH, INDEX, REPORT, STORE, write_package  # noqa: E402


@pytest.fixture(scope="session")
def toy(tmp_path_factory):
    """The toy package and its consumer, imported once so their solutions are declared before any test snapshots the registry."""
    site = tmp_path_factory.mktemp("site")
    write_package(site)
    sys.path.insert(0, str(site))
    import esoitoy.arms  # noqa: F401
    import esoitoyconsumer
    parts = Assembler("esoitoy", site / "esoitoy", modules=("esoitoy.solutions",))
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
    parts, consumer = toy[:2]
    parts.register(INDEX, "acme-index", consumer.StoreIndex)
    parts.register(REPORT, "acme-report", consumer.IndexReport)
    return AssemblyConfig(solutions=(REPORT,), selections={INDEX: "acme-index", REPORT: "acme-report"})


# names

def test_name_pattern():
    for good in ("a", "tier_selector", "x-1", "0abc"):
        assert assemble.check_name(good) == good
    for bad in ("", "-a", "_a", "a.b", "a:b", "A", "a b", "a\n", "../x", None, 3):
        with pytest.raises(AssemblyError):
            assemble.check_name(bad)


def test_a_consumer_registers_a_name_it_owns_and_selects_it_on_its_own_config(toy):
    parts, consumer = toy[:2]
    parts.register(STORE, "acme-memory", consumer.Mine)
    assert parts.names(STORE) == ["acme-memory", "memory"]
    assert parts.resolve(STORE, "acme-memory") is consumer.Mine
    assert parts.choice(STORE, config=AssemblyConfig(selections={STORE: "acme-memory"})).layer == "consumer selections"


def test_replacing_or_shadowing_a_package_declared_name_raises_but_a_consumer_may_replace_its_own(toy):
    parts, consumer = toy[:2]
    for replace in (False, True):
        with pytest.raises(AssemblyError, match="declared by the esoitoy"):
            parts.register(STORE, "memory", consumer.Mine, replace=replace)
    assert parts.resolve(STORE).__name__ == "Memory"
    parts.register(STORE, "acme-memory", consumer.Mine)
    parts.register(STORE, "acme-memory", consumer.StoreIndex, replace=True)
    assert parts.resolve(STORE, "acme-memory") is consumer.StoreIndex


def test_register_validates_the_solution_and_the_name(toy):
    parts, consumer = toy[:2]
    for sid, name in (("no-such-solution", "ok"), (STORE, "has.dot"), (STORE, "os:system"), (STORE, "Upper")):
        with pytest.raises(AssemblyError):
            parts.register(sid, name, consumer.Mine)


def test_a_name_that_is_not_listed_is_an_error_naming_the_choices(toy):
    parts, consumer = toy[:2]
    parts.register(STORE, "acme-memory", consumer.Mine)
    with pytest.raises(AssemblyError) as caught:
        parts.resolve(STORE, "other")
    message = str(caught.value)
    assert STORE in message and "esoitoy" in message and "explicit name" in message and "acme-memory" in message
    with pytest.raises(AssemblyError, match="consumer selections"):
        parts.choice(STORE, config=AssemblyConfig(selections={STORE: "other"}))


def test_the_cascade_is_explicit_then_selections_then_the_package_default(toy):
    parts, consumer = toy[:2]
    parts.register(STORE, "acme-memory", consumer.Mine)
    assert (parts.choice(STORE).name, parts.choice(STORE).layer) == ("memory", "esoitoy default")
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
            parts.assemble(AssemblyConfig(solutions=(STORE,), names=config.names, selections=config.selections,
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
    elsewhere = Assembler("esoitoy", tmp_path)
    with pytest.raises(AssemblyError, match="not inside the installed esoitoy package"):
        elsewhere.safe_module("esoitoy.arms")


ATTEMPT = """
import json, os, sys
sys.path[:] = [{site!r}, {esoi_path!r}] + [p for p in sys.path if 'site-packages' not in p and p]
marker, attacker = {marker!r}, {attacker!r}
{setup}
from pathlib import Path
from esoi.assemble import Assembler, AssemblyError
parts = Assembler("esoitoy", Path({site!r}) / "esoitoy", ("esoitoy.solutions",))
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
    parts, consumer = toy[:2]
    assert parts.needs_of(consumer.StoreIndex) == {"store": STORE}
    assert parts.needs_of(consumer.IndexReport) == {"index": INDEX}
    assert parts.needs_of(consumer.Mine) == {} and parts.needs_of(object()) == {}


def test_objects_are_built_in_dependency_order_and_the_needs_are_injected(toy):
    parts = toy[0]
    system = parts.assemble(wire(toy))
    assert system.solutions() == [STORE, INDEX, REPORT]
    system[STORE].put("k", "v")
    assert system[REPORT].render() == "report:v" and system[INDEX].store is system[STORE]


def test_a_provided_object_wins_for_its_solution_and_must_satisfy_it(toy):
    parts, consumer = toy[:2]
    mine = consumer.Mine()
    mine.put("k", "mine")
    system = parts.assemble(wire(toy), provided={STORE: mine})
    assert system[STORE] is mine and system[REPORT].render() == "report:mine"
    assert "layer: consumer provided" in system.reason_by_solution[STORE]
    with pytest.raises(AssemblyError, match="does not satisfy Store"):
        parts.assemble(wire(toy), provided={STORE: object()})
    with pytest.raises(AssemblyError, match="unknown solution"):
        parts.assemble(wire(toy), provided={"no-such-solution": object()})


def test_an_unmet_need_fails_at_startup_naming_the_chain(toy):
    parts, consumer = toy[:2]
    parts.register(REPORT, "acme-report", consumer.IndexReport)
    with pytest.raises(AssemblyError) as caught:
        parts.assemble(AssemblyConfig(solutions=(REPORT,), selections={REPORT: "acme-report"}))
    assert "toy-report (acme-report) needs toy-index: no arm, not provided" in str(caught.value)
    assert "toy-report -> toy-index" in str(caught.value)
    with pytest.raises(AssemblyError, match="toy-index: no arm, not provided"):
        parts.assemble(AssemblyConfig(solutions=(INDEX,)))


def test_a_cycle_fails_at_startup_naming_the_ring(toy):
    parts, consumer = toy[:2]
    parts.register(INDEX, "loop-a", consumer.LoopA)
    parts.register(REPORT, "loop-b", consumer.LoopB)
    with pytest.raises(AssemblyError, match="dependency cycle: toy-index -> toy-report -> toy-index"):
        parts.assemble(AssemblyConfig(solutions=(INDEX,), selections={INDEX: "loop-a", REPORT: "loop-b"}))


def test_a_longer_cycle_names_every_solution(toy):
    parts, consumer = toy[:2]
    parts.register(REPORT, "r2", consumer.ReportNeedsStore)
    parts.register(STORE, "s2", consumer.StoreNeedsIndex)
    parts.register(INDEX, "i2", consumer.IndexNeedsReport)
    config = AssemblyConfig(solutions=(REPORT,), selections={REPORT: "r2", STORE: "s2", INDEX: "i2"})
    with pytest.raises(AssemblyError, match="toy-report -> toy-store -> toy-index -> toy-report"):
        parts.assemble(config)


def test_options_reach_the_constructor_and_unknown_options_fail(toy):
    parts = toy[0]
    base = wire(toy)
    system = parts.assemble(AssemblyConfig(solutions=base.solutions, selections=base.selections, options={INDEX: {"prefix": "p-"}}))
    assert system[INDEX].prefix == "p-"
    with pytest.raises(AssemblyError, match="no option"):
        parts.assemble(AssemblyConfig(solutions=base.solutions, selections=base.selections, options={INDEX: {"nope": 1}}))


def test_the_reason_line_names_solution_arm_layer_version_and_hash(toy):
    system = toy[0].assemble(wire(toy))
    assert system.reason_by_solution[INDEX].startswith("toy-index -> acme-index (layer: consumer selections, package version ")
    assert "config hash " in system.reason_by_solution[INDEX] and len(system.reasons) == 3


def test_the_package_default_builds_without_a_consumer(toy):
    system = toy[0].assemble(AssemblyConfig())
    assert system.solutions() == [STORE] and type(system[STORE]).__name__ == "Memory"
    assert "layer: esoitoy default" in system.reasons[0]


def test_two_consumers_with_different_selections_do_not_affect_each_other(toy):
    parts, consumer = toy[:2]
    parts.register(STORE, "first", type("First", (), {"put": lambda s, k, v: None, "get": lambda s, k: k}))
    parts.register(STORE, "second", type("Second", (), {"put": lambda s, k, v: None, "get": lambda s, k: k}))
    one = parts.assemble(AssemblyConfig(solutions=(STORE,), selections={STORE: "first"}))
    two = parts.assemble(AssemblyConfig(solutions=(STORE,), selections={STORE: "second"}))
    default = parts.assemble(AssemblyConfig(solutions=(STORE,)))
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


def test_a_need_on_a_solution_with_no_arm_is_reported_unless_consumer_provided():
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


def test_a_need_on_an_unknown_solution_is_reported():
    solutions, impls = planted(uses="zzz")
    assert any("zzz, which is no solution" in line for line in assemble.problems(solutions, impls, {"a:x": {"zzz"}, "b:y": set()}))


def test_sync_uses_writes_the_column_from_the_parameters_and_uses_problems_then_finds_none(toy, tmp_path):
    parts, consumer = toy[:2]
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


# the risks of docs/resolution-design.md, one test each: R1 importing does nothing, R2 a hostile parent esoi.toml, R3 nothing
# routes around shadowing, R4 sys.path is unchanged, R8 the examples run, R12 errors are raised, R13 a public API, R14
# a Protocol that is not runtime checkable is still checked

def fresh(tmp_path, code, files=None, marker_arm=False):
    """Run ``code`` in a new interpreter on a copy of the toy package (``SITE`` and ``MARKER`` are defined for it); it prints
    one JSON object. ``files`` adds or replaces files under the site."""
    site, marker = tmp_path / "site", tmp_path / "marker"
    write_package(site, marker=str(marker) if marker_arm else "")
    for relative, text in (files or {}).items():
        (site / relative).parent.mkdir(parents=True, exist_ok=True)
        (site / relative).write_text(textwrap.dedent(text))
    head = (f"import sys; sys.path[:] = [{str(site)!r}, {ESOI_PATH!r}] + [p for p in sys.path if 'site-packages' not in p and p]\n"
            f"SITE, MARKER = {str(site)!r}, {str(marker)!r}\n")
    done = subprocess.run([sys.executable, "-c", head + textwrap.dedent(code)], cwd=tmp_path, capture_output=True, text=True,
                          timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_r1_constructing_and_preparing_import_no_arm_and_run_nothing(tmp_path):
    out = fresh(tmp_path, """
        import json, os
        from pathlib import Path
        from esoi.assemble import Assembler
        parts = Assembler("esoitoy", Path(SITE) / "esoitoy", ("esoitoy.solutions",))
        built = "esoitoy" in sys.modules
        parts.prepare()
        print(json.dumps(dict(built=built, solutions="esoitoy.solutions" in sys.modules, arm="esoitoy.arms" in sys.modules,
                              ran=os.path.exists(MARKER), names=parts.names("toy-store"))))
    """, marker_arm=True)
    assert out == dict(built=False, solutions=True, arm=False, ran=False, names=["memory"])


def test_concurrent_assembles_share_one_import_and_agree(tmp_path):
    out = fresh(tmp_path, """
        import json, threading
        from pathlib import Path
        from esoi.assemble import Assembler, AssemblyConfig
        parts = Assembler("esoitoy", Path(SITE) / "esoitoy", ("esoitoy.solutions",))
        barrier, kinds, errors = threading.Barrier(12), [], []
        def work():
            barrier.wait()
            try:
                kinds.append(type(parts.assemble(AssemblyConfig(solutions=("toy-store",)))["toy-store"]).__name__)
            except Exception as error:
                errors.append(repr(error))
        threads = [threading.Thread(target=work) for _ in range(12)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        print(json.dumps(dict(kinds=sorted(set(kinds)), count=len(kinds), errors=errors, runs=len(open(MARKER).read()))))
    """, marker_arm=True)
    assert out == dict(kinds=["Memory"], count=12, errors=[], runs=1)


HOSTILE_PARENT = {
    "esoi.toml": 'structure_dir = "specs"\npython_path = ["."]\n\n[selection]\ntoy-store = "pwn"\n',
    "specs/solutions.csv": "solution_id,selected,implementations\ntoy-store,pwn,\n",
    "specs/implementations.csv": "implementation_id,solution_id,filepath\ntoy-store:pwn,toy-store,evil.py\n",
    "evil.py": "open(__import__('os').environ.get('X', MARKER_PATH), 'w').write('x')\n",
}


def test_r2_r4_a_hostile_parent_esoi_toml_is_never_read_and_sys_path_is_unchanged(tmp_path):
    files = dict(HOSTILE_PARENT)
    files["evil.py"] = f"open({str(tmp_path / 'marker')!r}, 'w').write('x')\n"
    out = fresh(tmp_path, """
        import json, os
        from pathlib import Path
        from esoi import runtime
        from esoi.assemble import Assembler, AssemblyConfig
        parts = Assembler("esoitoy", Path(SITE) / "esoitoy", ("esoitoy.solutions",))
        path = list(sys.path)
        names, chosen = parts.names("toy-store"), parts.choice("toy-store").name
        built = type(parts.assemble(AssemblyConfig())["toy-store"]).__name__
        safe = dict(names=names, chosen=chosen, built=built, ran=os.path.exists(MARKER), path_same=path == sys.path)
        control = runtime.choose("toy-store", scope="esoitoy").name   # plain esoi.runtime does walk up and obey it
        try:
            runtime.resolve("toy-store", scope="esoitoy")
        except runtime.SelectionError:
            pass   # the parent's module ran (that is the point); it declares nothing
        print(json.dumps(dict(safe=safe, control=control, control_ran=os.path.exists(MARKER))))
    """, files)
    assert out["safe"] == dict(names=["memory"], chosen="memory", built="Memory", ran=False, path_same=True)
    assert out["control"] == "pwn" and out["control_ran"], "the control must show the parent file would have been obeyed"


def test_r3_nothing_routes_around_shadowing(tmp_path):
    out = fresh(tmp_path, """
        import json
        from pathlib import Path
        from esoi import runtime
        from esoi.assemble import Assembler, AssemblyError
        import esoitoy
        class Mine:
            put = get = lambda *a: None
        parts = Assembler("esoitoy", Path(SITE) / "esoitoy", ("esoitoy.solutions",))
        def refused(call):
            try:
                call()
                return ""
            except AssemblyError as error:
                return str(error)
        before = refused(lambda: runtime.register("toy-store", "memory", Mine, scope="esoitoy", replace=True))   # before any import
        replaced_before_import = refused(lambda: parts.resolve("toy-store"))
        runtime.forget("toy-store", "esoitoy"); parts.sealed.clear(); parts.memo.clear()
        import esoitoy.solutions, esoitoy.arms
        parts.prepare(); parts.seal()
        runtime.register("toy-store", "memory", Mine, scope="esoitoy", replace=True)
        replaced_after_seal = refused(lambda: parts.resolve("toy-store"))
        print(json.dumps(dict(a=replaced_before_import, b=replaced_after_seal)))
    """)
    assert "registered under it" in out["a"] and "registered under it" in out["b"]


def test_declared_sees_arms_defined_in_the_package_init_and_refuses_to_shadow_or_replace_them(tmp_path):
    files = {"esoitoy/__init__.py": '''
        from esoi import solution, implementation
        @solution("toy-init")
        class Init:
            pass
        @implementation("toy-init", "inline")
        class Inline:
            pass
    ''', "esoitoy/solutions.py": "", "esoitoy/esoi_selection.json": "{}"}
    out = fresh(tmp_path, """
        import json
        from pathlib import Path
        from esoi import runtime
        from esoi.assemble import Assembler, AssemblyError
        import esoitoy
        parts = Assembler("esoitoy", Path(SITE) / "esoitoy")
        found = parts.declared("toy-init")
        errors = []
        for replace in (False, True):
            try:
                parts.register("toy-init", "inline", object, replace=replace)
            except AssemblyError as error:
                errors.append(str(error))
        runtime.register("toy-init", "inline", object, scope="esoitoy", replace=True)
        try:
            parts.resolve("toy-init", "inline")
            direct = ""
        except AssemblyError as error:
            direct = str(error)
        print(json.dumps(dict(found=found, errors=errors, direct=direct)))
    """, files)
    assert out["found"] == ["inline"] and len(out["errors"]) == 2 and all("declared by the esoitoy" in e for e in out["errors"])
    assert "registered under it" in out["direct"]


def test_the_deployment_and_override_layers_are_not_consulted(toy):
    parts, consumer = toy[:2]
    parts.register(STORE, "acme-memory", consumer.Mine)
    with runtime.override(STORE, "acme-memory", scope="esoitoy"):
        assert parts.choice(STORE).name == "memory"
        assert type(parts.assemble(AssemblyConfig(solutions=(STORE,)))[STORE]).__name__ == "Memory"


def test_an_env_variable_of_another_scope_or_solution_is_refused(toy):
    for variable in ("ESOI_SELECT_TOY_STORE", "ESOI_SELECT_OTHER_TOY_STORE", "PATH"):
        with pytest.raises(AssemblyError, match="may not set"):
            toy[0].choice(STORE, config=AssemblyConfig(selection_environ={variable: "memory"}))


def records_for(tmp_path, name="rec-arm", selected=None, filepath=None, extra_toml=""):
    """Records (an esoi.toml, solutions and implementations) whose one arm ``name`` lives in ``esoitoy/<name>.py``."""
    root = tmp_path / "records"
    (root / "specs").mkdir(parents=True)
    (root / "esoi.toml").write_text('structure_dir = "specs"\npython_path = ["."]\n' + extra_toml)
    chosen = name if selected is None else selected
    (root / "specs" / "solutions.csv").write_text(f"solution_id,selected,implementations\n{STORE},{chosen},\n")
    (root / "specs" / "implementations.csv").write_text(
        f"implementation_id,solution_id,filepath\n{STORE}:{name},{STORE},{filepath or 'esoitoy/' + name.replace('-', '_') + '.py'}\n")
    return root


def write_arm(toy, name, body=None):
    """An arm module in the toy package, new for each test, because an imported module is not imported twice."""
    text = body or f'from esoi import implementation\n\n\n@implementation("{STORE}", "{name}")\nclass Arm:\n    pass\n'
    (toy[2] / "esoitoy" / (name.replace("-", "_") + ".py")).write_text(text)


def test_r4_records_mode_reads_one_explicit_folder_and_leaves_sys_path_alone(toy, tmp_path):
    write_arm(toy, "rec-arm")
    parts = Assembler("esoitoy", toy[2] / "esoitoy", ("esoitoy.solutions",), records=records_for(tmp_path))
    before = list(sys.path)
    assert parts.choice(STORE).name == "rec-arm" and parts.choice(STORE).layer == "esoitoy default"
    assert type(parts.assemble(AssemblyConfig(solutions=(STORE,)))[STORE]).__name__ == "Arm"
    assert sys.path == before


def test_records_mode_never_looks_in_a_parent_folder(toy, tmp_path):
    (tmp_path / "esoi.toml").write_text('structure_dir = "specs"\n')
    empty = tmp_path / "records"
    empty.mkdir()
    with pytest.raises(AssemblyError, match="has no esoi.toml"):
        Assembler("esoitoy", toy[2] / "esoitoy", ("esoitoy.solutions",), records=empty).choice(STORE)


def test_a_record_filepath_that_leaves_the_package_is_rejected_and_never_run(toy, tmp_path):
    (tmp_path / "x.py").write_text(f"open({str(tmp_path / 'marker')!r}, 'w').write('x')\n")
    parts = Assembler("esoitoy", toy[2] / "esoitoy", ("esoitoy.solutions",), records=records_for(tmp_path, "rec-escape", filepath="../x.py"))
    with pytest.raises(AssemblyError, match="rejected"):
        parts.load(STORE, "rec-escape")
    assert not (tmp_path / "marker").exists()


def test_r12_errors_are_raised_not_swallowed(toy, tmp_path):
    site = toy[2]
    bad = tmp_path / "pkg"
    bad.mkdir()
    (bad / "esoi_selection.json").write_text("{not json")
    with pytest.raises(AssemblyError, match="cannot be read"):
        Assembler("esoitoy", bad, ()).names(STORE)
    with pytest.raises(AssemblyError, match="cannot be loaded"):
        Assembler("esoitoy", site / "esoitoy", (), records=records_for(tmp_path / "one", extra_toml="unknown_key = 1\n")).names(STORE)
    write_arm(toy, "rec-needs", "raise ImportError('optional extra missing')\n")
    parts = Assembler("esoitoy", site / "esoitoy", ("esoitoy.solutions",), records=records_for(tmp_path / "two", "rec-needs"))
    with pytest.raises(AssemblyError, match="cannot import 'esoitoy.rec_needs'.*optional extra missing"):
        parts.load(STORE, "rec-needs")
    with pytest.raises(AssemblyError, match="not an implementation that can be chosen"):
        Assembler("esoitoy", site / "esoitoy", ("esoitoy.solutions",), records=records_for(tmp_path / "three", "rec-ghost", selected="ghost")) \
            .assemble(AssemblyConfig())


def test_a_broken_selection_is_not_silently_dropped_when_the_manifest_is_empty(toy):
    with pytest.raises(AssemblyError, match="unknown implementation 'nope'"):
        toy[0].assemble(AssemblyConfig(selections={STORE: "nope"}))


def test_an_arm_that_cannot_be_imported_is_a_finding_for_the_records_check_not_a_crash(toy, tmp_path):
    site = toy[2]
    write_arm(toy, "rec-needs-two", "raise ImportError('optional extra missing')\n")
    root = records_for(tmp_path, "rec-needs-two")
    parts = Assembler("esoitoy", site / "esoitoy", ("esoitoy.solutions",), records=root)
    found = parts.uses_problems(root / "specs")
    assert len(found) == 1 and found[0].startswith(f"{STORE}:rec-needs-two: cannot be loaded") and "optional extra missing" in found[0]
    before = (root / "specs" / "implementations.csv").read_text()
    assert len(parts.sync_uses(root / "specs")) == 1
    assert (root / "specs" / "implementations.csv").read_text().splitlines()[1].startswith(f"{STORE}:rec-needs-two,{STORE},esoitoy/")
    assert before.splitlines()[0] in (root / "specs" / "implementations.csv").read_text()


def test_r13_the_public_api_is_explicit():
    namespace = {}
    exec("from esoi.assemble import *", namespace)
    exported = {name for name in namespace if name != "__builtins__"}
    assert exported == set(assemble.__all__) == {"Assembler", "Assembly", "AssemblyConfig", "AssemblyError", "CONSUMER_PROVIDED",
                                                  "NAME_PATTERN", "check_name", "cycle_of", "problems"}


def test_r14_a_protocol_that_is_not_runtime_checkable_is_still_checked(toy):
    parts = toy[0]
    with pytest.raises(AssemblyError, match="does not satisfy Plain: missing ping"):
        parts.assemble(AssemblyConfig(), provided={"toy-plain": object()})
    ok = type("Ping", (), {"ping": lambda self: "pong"})()
    assert parts.assemble(AssemblyConfig(), provided={"toy-plain": ok})["toy-plain"] is ok
    with pytest.raises(AssemblyError, match="cannot check the object provided for 'toy-fn'"):
        parts.assemble(AssemblyConfig(), provided={"toy-fn": object()})


def test_a_name_with_a_dot_is_refused_and_the_message_says_why(toy):
    with pytest.raises(AssemblyError, match=r"'\.' and ':' are refused"):
        assemble.check_name("gpt-4.1")
    assert assemble.check_name("gpt-4-1") == "gpt-4-1"


def test_the_assembly_is_frozen_to_what_assemble_chose(toy):
    parts, consumer = toy[:2]
    system = parts.assemble(wire(toy))
    assert system.choice(INDEX).name == "acme-index" and system.implementation(INDEX) is consumer.StoreIndex
    parts.register(INDEX, "acme-index", consumer.Mine, replace=True)
    assert system.implementation(INDEX) is consumer.StoreIndex and system.choice(INDEX).layer == "consumer selections"
    with pytest.raises(AssemblyError, match="no recorded choice"):
        parts.assemble(AssemblyConfig(), provided={STORE: consumer.Mine()}).choice(STORE)


# R8: the examples in the module docstring and in the guide are run, so they cannot rot

def test_r8_the_example_in_the_module_docstring_runs(tmp_path):
    assemble_fixture.run_docstring_example(tmp_path)


def test_r8_every_python_block_of_the_guide_runs(tmp_path):
    assemble_fixture.run_guide(tmp_path)
