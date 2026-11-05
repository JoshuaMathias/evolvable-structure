"""esoi.runtime.assemble_by_name.environment_needs and esoi.runtime.assemble_by_name.installation: declarations, checks, closure, outputs, install safety and the resolution ladder.

Everything runs against a toy package written to a temporary folder. Pip, scripts and the resolver are stubbed; nothing touches
the network, the real environment or a real virtualenv.
"""
import json
import os
import stat
import sys
import textwrap
from dataclasses import replace
from pathlib import Path

import pytest

from esoi.runtime.assemble_by_name.installation import assembly_plan, command_running, conflicts, execution, install_lock, plan, resolution_ladder
from esoi.runtime.implementation_selection import declare
from esoi.runtime.implementation_selection import selection_registry
from esoi.runtime.assemble_by_name.environment_needs import checking, closure, declarations, generated_files, report
from esoi.runtime.assemble_by_name.assemble import Assembler
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig

SOLUTIONS = '''
import typing
from typing import runtime_checkable
from esoi import solution

@solution("seat-a")
@runtime_checkable
class SeatA(typing.Protocol):
    def a(self) -> str: ...

@solution("seat-b")
@runtime_checkable
class SeatB(typing.Protocol):
    def b(self) -> str: ...
'''
HELPERS = '''
from esoi.runtime.assemble_by_name.environment_needs.declarations import env
REQUIRES = (env("TOY_HELPER_TOKEN", secret=True),)
'''
ARMS = '''
import importlib
from esoi import implementation
from esoi.runtime.assemble_by_name.environment_needs.declarations import api, binary, download, env, isolatable, python, resource, service
from . import helpers
from .solutions import SeatA

@implementation("seat-a", "alpha")
class Alpha:
    REQUIRES = (python("toypkg_mod", "toypkg>=2", alternatives=("toypkg2>=1",)),)
    ENVIRON = {"token": ("TOY_TOKEN", "TOY_TOKEN_ALT")}
    ENVIRON_REQUIRED = ("token",)
    def __init__(self, token: str): self.token = token
    def a(self): return "a"

@implementation("seat-a", "beta")
class Beta:
    REQUIRES = (python("toypkg_mod", "toypkg<2"),)
    def a(self): return "b"

@implementation("seat-a", "delta")
class Delta:
    REQUIRES = (python("otherpkg_mod", "otherpkg>=1"),)
    def a(self): return "d"

@implementation("seat-b", "gamma")
class Gamma:
    REQUIRES = (python("toypkg_mod", "toypkg<2"), isolatable("cli"))
    def __init__(self, a: SeatA): self.a_ = a
    def b(self): return "g"

def lazy():
    importlib.import_module(NAME)
    from . import cyc_one
    from . import broken
'''
CYC_ONE = "from . import cyc_two\n"
CYC_TWO = "from . import cyc_one\n"
BROKEN = "def (:\n"


@pytest.fixture(scope="module")
def toy(tmp_path_factory):
    site = tmp_path_factory.mktemp("reqsite")
    package = site / "esoireq"
    package.mkdir()
    for name, text in (("__init__.py", ""), ("solutions.py", SOLUTIONS), ("helpers.py", HELPERS), ("arms.py", ARMS),
                       ("cyc_one.py", CYC_ONE), ("cyc_two.py", CYC_TWO), ("broken.py", BROKEN)):
        (package / name).write_text(textwrap.dedent(text), encoding="utf-8")
    (package / "arms.install.sh").write_text("echo hi\n", encoding="utf-8")
    (package / "arms.requirements.txt").write_text("somepkg\n", encoding="utf-8")
    sys.path.insert(0, str(site))
    import esoireq.arms  # noqa: F401
    assembler = Assembler("esoireq", package, modules=("esoireq.solutions", "esoireq.arms"))
    assembler.prepare()
    yield assembler, package
    sys.path.remove(str(site))
    for name in [m for m in sys.modules if m.split(".")[0] == "esoireq"]:
        sys.modules.pop(name)
    for key in [k for k in selection_registry.REGISTRY if k[0] == "esoireq"]:
        selection_registry.REGISTRY.pop(key)


def cfg(**names):
    return AssemblyConfig(names=names, consumer_environ={})


# declaration

def test_declared_reads_requires_and_environ_shorthand():
    class Arm:
        REQUIRES = (declarations.python("m", "d"),)
        ENVIRON = {"api_key": ("A_KEY", "B_KEY"), "url": "U"}
        ENVIRON_REQUIRED = ("api_key",)
    items = declarations.declared(Arm)
    envs = [i for i in items if isinstance(i, declarations.Env)]
    assert [e.name for e in envs] == ["A_KEY", "U"] and envs[0].also == ("B_KEY",)
    assert envs[0].required and not envs[1].required and envs[0].option == "api_key"


def test_requires_rejects_a_non_requirement():
    class Arm:
        REQUIRES = ("OPENALEX_API_KEY",)
    with pytest.raises(TypeError, match="not a requirement"):
        declarations.declared(Arm)


def test_api_key_owns_its_variable_so_environ_does_not_repeat_it():
    class Arm:
        REQUIRES = (declarations.api("S", key=declarations.env("S_KEY", option="api_key", secret=True), keyless=True),)
        ENVIRON = {"api_key": "S_KEY"}
    kinds = [type(i).__name__ for i in declarations.declared(Arm)]
    assert kinds == ["Api"]


# check results and remedies

def test_env_empty_or_whitespace_counts_as_unset():
    item = declarations.env("K")
    assert checking.check([item], {"K": ""})[0].status == checking.UNMET
    assert checking.check([item], {"K": "   \t"})[0].status == checking.UNMET
    assert checking.check([item], {"K": "x"})[0].status == checking.MET


def test_api_keyless_is_met_with_a_remedy_naming_the_key():
    item = declarations.api("OpenAlex", key=declarations.env("OPENALEX_API_KEY"), keyless=True, signup_url="https://example.org/key")
    one = checking.check([item], {})[0]
    assert one.status == checking.MET and "OPENALEX_API_KEY" in one.remedy and "keyless" in one.remedy and "https://example.org/key" in one.remedy


def test_api_requiring_a_key_is_unmet_with_signup_link():
    item = declarations.api("Gem", key=declarations.env("GEM_KEY"), signup_url="https://example.org/s")
    one = checking.check([item], {})[0]
    assert one.status == checking.UNMET and "https://example.org/s" in one.remedy
    assert checking.check([item], {"GEM_KEY": "v"})[0].status == checking.MET


def test_group_of_variables_any_one_is_enough():
    items = [declarations.env("A", group="g"), declarations.env("B", group="g")]
    assert [c.status for c in checking.check(items, {"B": "1"})] == [checking.MET, checking.MET]
    assert all(c.status == checking.UNMET and "A or B" in c.remedy for c in checking.check(items, {}))


def test_python_version_specifier_and_marker():
    assert checking.check([declarations.python("json", "nonexistent-dist-zz>=1; python_version<'3'")], {})[0].status == checking.MET   # marker false here
    one = checking.check([declarations.python("pytest", "pytest>=9999")], {})[0]
    assert one.status == checking.UNMET and "does not satisfy" in one.remedy
    assert checking.check([declarations.python("no_such_module_zz", "zz")], {})[0].remedy.startswith("pip install")


def test_binary_missing_not_executable_and_present(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    file = tmp_path / "tool"
    file.write_text("#!/bin/sh\nexit 0\n")
    one = checking.check([declarations.binary("tool", "apt install tool")], {})[0]
    assert one.status == checking.UNMET and "not executable" in one.remedy
    file.chmod(file.stat().st_mode | stat.S_IXUSR)
    assert checking.check([declarations.binary("tool")], {})[0].status == checking.MET
    assert "apt install nothere" in checking.check([declarations.binary("nothere", "apt install nothere")], {})[0].remedy


def test_binary_version_probe_timeout_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    file = tmp_path / "slow"
    file.write_text("#!/bin/sh\nexec /bin/sleep 5\n")
    file.chmod(0o755)
    monkeypatch.setattr(checking, "PROBE_SECONDS", 0.2)
    one = checking.check([declarations.binary("slow", version_args=["--version"])], {}, probe=True)[0]
    assert one.status == checking.UNMET and "timed out" in one.remedy


def test_service_default_is_unknown_and_configured_is_met():
    item = declarations.service("Qdrant", "QDRANT_URL", "http://localhost:6333", "/healthz")
    assert checking.check([item], {})[0].status == checking.UNKNOWN
    assert checking.check([item], {"QDRANT_URL": "http://x"})[0].status == checking.MET
    assert checking.check([declarations.service("S", "S_URL")], {})[0].status == checking.UNMET


def test_probes_are_opt_in_and_offline_disables_them(monkeypatch):
    calls = []
    monkeypatch.setattr(checking, "reach", lambda url: calls.append(url) or False)
    item = declarations.service("Q", "Q_URL", "http://h", "/health")
    checking.check([item], {})
    assert calls == []
    checking.check([item], {}, probe=True, offline=True)
    assert calls == []
    assert checking.check([item], {}, probe=True)[0].status == checking.UNMET and calls


def test_download_checks_free_disk_space(monkeypatch):
    monkeypatch.setattr(checking, "disk_free_mb", lambda where: 10.0)
    one = checking.check([declarations.download("weights", 500, "~/.cache/w")], {})[0]
    assert one.status == checking.UNMET and one.failing and "free disk space" in one.remedy
    monkeypatch.setattr(checking, "disk_free_mb", lambda where: 99999.0)
    assert checking.check([declarations.download("weights", 500)], {})[0].status == checking.UNKNOWN


# closure

def test_closure_follows_needs_and_helper_modules(toy):
    assembler, package = toy
    members = assembler.closure(cfg(**{"seat-a": "alpha", "seat-b": "gamma"}), None, ("seat-b",))
    assert [(m.label, m.reason) for m in members] == [("seat-b:gamma", "selected"), ("seat-a:alpha", "needed by seat-b:gamma")]
    entries = declarations.gather(closure.members_pairs(members))
    names = {getattr(e.requirement, "name", None) for e in entries}
    assert "TOY_HELPER_TOKEN" in names   # declared on helpers.py, imported by arms.py
    helper = next(e for e in entries if getattr(e.requirement, "name", "") == "TOY_HELPER_TOKEN")
    assert any(" via esoireq.helpers" in u for u in helper.used_by)


def test_closure_notes_dynamic_cycle_and_unparsable_imports(toy):
    assembler, package = toy
    notes = []
    members = assembler.closure(cfg(**{"seat-a": "alpha"}), None, ("seat-a",))
    closure.members_pairs(members, notes)
    text = "\n".join(notes)
    assert "dynamic import not followed" in text
    assert "import cycle" in text and "cyc_one" in text
    assert "unknown, cannot import" in text and "broken" in text


def test_closure_order_is_deterministic(toy):
    assembler, package = toy
    config = cfg(**{"seat-a": "alpha", "seat-b": "gamma"})
    first = [e.requirement for e in declarations.gather(closure.members_pairs(assembler.closure(config)))]
    again = [e.requirement for e in declarations.gather(closure.members_pairs(assembler.closure(config)))]
    assert first == again


def test_folder_files_are_discovered_in_run_order(toy):
    files = declarations.script_files(sys.modules["esoireq.arms"])
    assert [f.role for f in files] == ["shell", "requirements"]


def test_closure_only_includes_what_is_used(toy):
    assembler, _ = toy
    entries = assembler.requirements(cfg(**{"seat-a": "delta"}), solutions=("seat-a",))
    assert any(isinstance(e.requirement, declarations.Python) and e.requirement.module == "otherpkg_mod" for e in entries)
    assert not any(isinstance(e.requirement, declarations.Python) and e.requirement.module == "toypkg_mod" for e in entries)


# assembly pending integration

def test_pending_needs_names_unmet_requirements_and_assembly_reports(toy):
    assembler, _ = toy
    pending = assembler.pending_needs(replace(cfg(**{"seat-a": "alpha"}), solutions=("seat-a",)), {})
    assert "TOY_TOKEN" in pending["seat-a"]
    ok = replace(cfg(**{"seat-a": "alpha"}), consumer_environ={"TOY_TOKEN": "t", "TOY_HELPER_TOKEN": "h"})
    assert "seat-a" in assembler.pending_needs(ok, {})   # the python requirement is still unmet
    assert "toypkg" in assembler.pending_needs(ok, {})["seat-a"]


def test_environ_still_fills_options_without_requires(toy):
    assembler, _ = toy
    ok = replace(cfg(**{"seat-a": "alpha"}), consumer_environ={"TOY_TOKEN_ALT": "t"})
    from esoi.runtime.assemble_by_name.environ_options import environ_fill
    assert environ_fill(selection_registry.REGISTRY[("esoireq", "seat-a")].implementations["alpha"], {}, ok.consumer_environ) == {"token": "TOY_TOKEN_ALT"}


# outputs

def sample_entries():
    class Arm:
        REQUIRES = (declarations.api("OpenAlex", key=declarations.env("OPENALEX_API_KEY", secret=True), keyless=True, signup_url="https://example.org/k",
                          pricing_url="https://example.org/p", free_tier="free key", as_of="2026-10"),
                    declarations.python("hubmod", "hubofhubs", extra="web"), declarations.python("hubmod2", "hubofhubs", extra="science"),
                    declarations.binary("nosuchbin", "apt install nosuchbin"), declarations.download("w", 5, "~/.cache/w"), declarations.resource("2 GB RAM"),
                    declarations.service("Q", "Q_URL", "http://localhost:6333"), declarations.env("PLAIN"))
    return declarations.gather([("s:a", Arm)])


def test_env_template_has_no_values_and_comments_the_api(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "supersecretvalue")
    text = generated_files.env_template(sample_entries())
    assert "supersecretvalue" not in text
    assert "OPENALEX_API_KEY=\n" in text and "https://example.org/k" in text and "keyless" in text and "(as of 2026-10)" in text


def test_install_script_merges_extras_and_lists_binaries():
    text = generated_files.install_script(sample_entries(), {})
    assert 'python -m pip install "hubofhubs[science,web]"' in text
    assert "apt install nosuchbin" in text and "download on first use: w" in text


def test_json_is_versioned_and_never_holds_a_value(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "supersecretvalue")
    entries = sample_entries()
    out = report.as_json(entries, checking.check(entries, dict(os.environ)), ["a note"])
    assert out["schema"] == "esoi.requirements/1" and out["notes"] == ["a note"]
    assert "supersecretvalue" not in json.dumps(out)
    assert {"status", "remedy", "used_by"} <= set(out["requirements"][0])


def test_report_names_a_remedy_for_every_unmet():
    entries = sample_entries()
    for entry, one in zip(entries, checking.check(entries, {})):
        if one.status == checking.UNMET:
            assert one.remedy, entry


def test_write_env_file_never_overwrites_and_is_mode_600(tmp_path):
    entries = sample_entries()
    path = tmp_path / ".env"
    path.write_text("PLAIN=keepme\nOTHER=1", encoding="utf-8")
    message = generated_files.write_env_file(path, entries)
    text = path.read_text()
    assert "PLAIN=keepme" in text and "OTHER=1" in text and "# OPENALEX_API_KEY=" in text and "PLAIN=\n" not in text
    assert "existing values untouched" in message
    generated_files.write_env_file(path, entries)
    assert path.read_text() == text   # a second run adds nothing
    fresh = tmp_path / "sub.env"
    generated_files.write_env_file(fresh, entries)
    assert stat.S_IMODE(fresh.stat().st_mode) == 0o600


def test_write_env_file_refuses_a_git_tracked_file_but_not_a_template(tmp_path, monkeypatch):
    entries = sample_entries()
    monkeypatch.setattr(generated_files, "git_tracked", lambda path: True)
    tracked = tmp_path / ".env"
    tracked.write_text("A=1\n")
    with pytest.raises(ValueError, match="tracked by git"):
        generated_files.write_env_file(tracked, entries)
    generated_files.write_env_file(tmp_path / ".env.example", entries)
    assert "OPENALEX_API_KEY=" in (tmp_path / ".env.example").read_text()


# install: planning and the ladder

def py(module, dist, used="s:a", alternatives=()):
    return declarations.Entry(declarations.python(module, dist, alternatives=alternatives), (used,))


def test_plan_merges_duplicates_into_one_pip_set(monkeypatch):
    entries = [py("m1", "zzpkg>=1,<3", "s:a"), py("m2", "zzpkg>=2", "s:b"), py("m3", "zzother", "s:b")]
    chosen = resolution_ladder.make_plan(entries, {})
    assert chosen.pip == ("zzother", "zzpkg>=1,<3,>=2") and chosen.coherent


def test_plan_skips_what_is_already_satisfied():
    assert resolution_ladder.make_plan([py("json", "stdlib-json")], {}).empty


def test_conflict_is_found_with_pullers():
    found = conflicts.find_conflicts([py("m", "zzpkg>=2", "x:a"), py("m", "zzpkg<2", "y:b")])
    assert len(found) == 1 and "x:a" in found[0].text() and "y:b" in found[0].text()
    assert conflicts.find_conflicts([py("m", "zzpkg==1", "x:a"), py("m", "zzpkg==2", "y:b")])


def test_ladder_step1_resolver_failure_retries_without_constraints():
    seen = []

    def resolver(specs, constraints):
        seen.append(bool(constraints))
        return command_running.Outcome(0 if not constraints else 1, "")
    entries = [py("json_zz", "pytest>=1")]   # pytest is installed, so constraints are non-empty
    chosen = resolution_ladder.make_plan(entries, {}, resolver)
    assert seen == [True, False] and chosen.coherent and any("retrying without" in s for s in chosen.steps)


def test_ladder_step2_declared_alternative_resolves():
    entries = [py("m", "zzpkg>=2", "x:a", alternatives=("zzpkg2>=1",)), py("m", "zzpkg<2", "y:b")]
    chosen = resolution_ladder.make_plan(entries, {})
    assert chosen.coherent and any("instead of" in s for s in chosen.steps) and "zzpkg2>=1" in chosen.pip


def test_ladder_step3_falls_back_to_the_next_arm(toy):
    assembler, _ = toy
    config = cfg(**{"seat-a": "alpha", "seat-b": "gamma"})
    chosen, members = assembly_plan.assembly_plan(assembler, config, {}, rank=lambda sid, name: ["delta", "beta"] if sid == "seat-a" else [])
    # alpha (toypkg>=2, alternatives off for this test) and gamma (toypkg<2) conflict; seat-a gives way to delta
    assert chosen.substitutions or chosen.isolated or chosen.coherent
    sub = assembly_plan.assembly_plan(assembler, config, {}, rank=lambda sid, name: ["delta"] if sid == "seat-a" else [])[0]
    assert not sub.conflicts


def test_ladder_step3_label_and_step4_isolation(toy):
    assembler, _ = toy
    # remove the declared alternative so step 2 cannot help: use a config where alpha conflicts with gamma
    alpha = selection_registry.REGISTRY[("esoireq", "seat-a")].implementations["alpha"]
    saved = alpha.REQUIRES
    alpha.REQUIRES = (declarations.python("toypkg_mod", "toypkg>=2"),)
    try:
        config = cfg(**{"seat-a": "alpha", "seat-b": "gamma"})
        chosen, members = assembly_plan.assembly_plan(assembler, config, {}, rank=lambda sid, name: ["delta"] if sid == "seat-a" else [])
        assert [s.text() for s in chosen.substitutions] == [
            "seat-a: selected alpha; using delta here because alpha conflicts with seat-b:gamma (no version satisfies >=2,<2 for toypkg)"] or \
            chosen.substitutions[0].using == "delta"
        assert chosen.substitutions[0].selected == "alpha" and "conflicts with" in chosen.substitutions[0].because
        # no alternative arm: gamma declares isolatable("cli"), so it moves to its own environment
        none, _ = assembly_plan.assembly_plan(assembler, config, {}, rank=lambda sid, name: [], project=Path("/proj"))
        assert none.isolated and none.isolated[0].arm == "seat-b:gamma" and "/proj/.esoi/venvs/" in none.isolated[0].folder
        assert none.coherent
    finally:
        alpha.REQUIRES = saved


def test_ladder_step5_stops_with_options_and_installs_nothing():
    entries = [py("m", "zzpkg>=2", "x:a"), py("m", "zzpkg<2", "y:b")]
    chosen = resolution_ladder.make_plan(entries, {})
    assert not chosen.coherent and chosen.pip == () and any("deselect" in o and "widen" in o for o in chosen.options)
    assert "5. stop" in chosen.steps[-1]
    calls = []
    out = execution.execute(chosen, [], {}, run=lambda c, d, t: calls.append(c) or command_running.Outcome(0))
    assert out.code == 1 and calls == []


def test_coherence_flags_selected_arms_that_conflict(toy):
    assembler, _ = toy
    clash = assembly_plan.assembly_plan(assembler, cfg(**{"seat-a": "alpha", "seat-b": "gamma"}), {}, rank=lambda s, n: [])[0]
    assert clash.adjusted
    fine = assembly_plan.assembly_plan(assembler, cfg(**{"seat-a": "beta", "seat-b": "gamma"}), {})[0]
    assert not fine.adjusted and fine.pip == ("toypkg<2",)


# install: execution safety

class Recorder:
    def __init__(self, code=0, output=""):
        self.calls, self.code, self.output = [], code, output

    def __call__(self, command, cwd, timeout):
        self.calls.append((list(command), cwd, timeout))
        return command_running.Outcome(self.code, self.output)


def test_execute_uses_sys_executable_one_pip_call_then_pip_check(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    run = Recorder()
    chosen = plan.Plan(pip=("a", "b>=1"))
    result = execution.execute(chosen, [], {}, run, tmp_path)
    assert result.code == 0
    assert run.calls[0][0] == [sys.executable, "-m", "pip", "install", "a", "b>=1"]
    assert run.calls[1][0] == [sys.executable, "-m", "pip", "check"] and len(run.calls) == 2


def test_execute_refuses_an_externally_managed_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: True)
    run = Recorder()
    result = execution.execute(plan.Plan(pip=("a",)), [], {}, run, tmp_path)
    assert result.code == 1 and "virtualenv" in result.reports[0] and "never used" in result.reports[0] and run.calls == []


def test_execute_warns_outside_a_virtualenv(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    monkeypatch.setattr(execution, "in_virtualenv", lambda: False)
    assert execution.execute(plan.Plan(pip=("a",)), [], {}, Recorder(), tmp_path).warnings


def test_failure_reports_step_and_scrubbed_tail_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    run = Recorder(1, "boom\nthe token is s3cretvalue here")
    result = execution.execute(plan.Plan(pip=("a",)), [], {"K": "s3cretvalue"}, run, tmp_path)
    text = "\n".join(result.reports)
    assert result.code == 1 and "FAILED python -m pip install a" in text and "resumable" in text
    assert "s3cretvalue" not in text and "***" in text and len(run.calls) == 1


def test_pip_check_conflicts_are_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)

    def run(command, cwd, timeout):
        return command_running.Outcome(1 if command[-1] == "check" else 0, "x 1 requires y")
    result = execution.execute(plan.Plan(pip=("a",)), [], {}, run, tmp_path)
    assert result.code == 1 and "pip check found conflicts" in result.reports[-1]


def test_timeout_is_a_failure_with_its_own_wording(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    result = execution.execute(plan.Plan(pip=("a",)), [], {}, lambda c, d, t: command_running.Outcome(124, "", True), tmp_path)
    assert "timed out" in result.reports[0]


def test_lock_blocks_a_second_install(tmp_path):
    with install_lock.InstallLock(tmp_path):
        with pytest.raises(install_lock.InstallLocked, match="another esoi install"):
            with install_lock.InstallLock(tmp_path):
                pass
    with install_lock.InstallLock(tmp_path):
        pass


def test_script_refusals_traversal_and_symlink_escape(tmp_path):
    root = tmp_path / "pkg"
    root.mkdir()
    inside = root / "install.sh"
    inside.write_text("echo ok\n")
    outside = tmp_path / "evil.sh"
    outside.write_text("echo bad\n")
    (root / "link.sh").symlink_to(outside)
    assert execution.script_refusal(str(inside), [root]) == ""
    assert "outside the package directory" in execution.script_refusal(str(root / "link.sh"), [root])
    assert "outside the package directory" in execution.script_refusal(str(root / ".." / "evil.sh"), [root])
    assert "missing" in execution.script_refusal(str(root / "nope.sh"), [root])


def test_scripts_run_in_their_folder_with_the_right_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    root = tmp_path / "pkg"
    root.mkdir()
    for name in ("install.sh", "requirements.txt", "install.py"):
        (root / name).write_text("x\n")
    run = Recorder()
    chosen = plan.Plan(scripts=(("shell", str(root / "install.sh")), ("requirements", str(root / "requirements.txt")),
                                     ("python", str(root / "install.py"))))
    result = execution.execute(chosen, [root], {}, run, tmp_path)
    assert result.code == 0
    commands = [c for c, d, t in run.calls]
    assert commands[0] == ["sh", str(root / "install.sh")] and commands[1][:5] == [sys.executable, "-m", "pip", "install", "-r"]
    assert commands[2] == [sys.executable, str(root / "install.py")]
    assert {d for c, d, t in run.calls} == {str(root.resolve())}


def test_missing_sh_is_reported_clearly(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    monkeypatch.setattr(execution, "shutil_which", lambda name: None)
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "install.sh").write_text("x\n")
    result = execution.execute(plan.Plan(scripts=(("shell", str(root / "install.sh")),)), [root], {}, Recorder(), tmp_path)
    assert result.code == 1 and "no sh on this system" in result.reports[0]


def test_nonzero_script_stops_the_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "a.py").write_text("x\n")
    (root / "b.py").write_text("x\n")
    run = Recorder(3, "bad")
    result = execution.execute(plan.Plan(scripts=(("python", str(root / "a.py")), ("python", str(root / "b.py")))), [root], {}, run, tmp_path)
    assert result.code == 1 and len(run.calls) == 1


def test_isolated_install_uses_its_own_python(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "externally_managed", lambda: False)
    run = Recorder()
    folder = str(tmp_path / "venv")
    chosen = plan.Plan(isolated=(plan.Isolated("s:g", "cli", folder, ("zzpkg<2",)),))
    assert execution.execute(chosen, [], {}, run, tmp_path).code == 0
    assert run.calls[0][0][:3] == [sys.executable, "-m", "venv"] and run.calls[1][0][0].startswith(folder)


def test_plan_is_dry_by_default_through_the_cli(toy, capsys, monkeypatch):
    from esoi import __main__ as cli
    assembler, package = toy
    module = type(sys)("esoireq_cli")
    module.assembler = lambda: assembler
    monkeypatch.setitem(sys.modules, "esoireq_cli", module)
    called = []
    monkeypatch.setattr(execution, "execute", lambda *a, **k: called.append(1))
    code = cli.main(["install", "--package", "esoireq_cli", "--solution", "seat-a", "--arm", "seat-a=alpha"])
    out = capsys.readouterr()
    assert called == [] and code == 1 and "dry run" in out.err and "closure:" in out.out


def test_requirements_cli_exit_codes_and_json(toy, capsys, monkeypatch):
    from esoi import __main__ as cli
    assembler, _ = toy
    module = type(sys)("esoireq_cli2")
    module.assembler = lambda: assembler
    monkeypatch.setitem(sys.modules, "esoireq_cli2", module)
    assert cli.main(["requirements", "--package", "esoireq_cli2", "--solution", "seat-a", "--arm", "seat-a=alpha", "--check", "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["schema"] == "esoi.requirements/1"
    assert cli.main(["requirements", "--package", "no_such_package_zz"]) == 2
    assert cli.main(["requirements", "--package", "esoireq_cli2", "--coherence", "--arm", "seat-a=alpha", "--arm", "seat-b=gamma"]) == 1


# ladder step 3 reads the scope's own leaderboard

def project_assembler(repo, monkeypatch):
    """The scaffolded demo project as an Assembler with records, after recording a run of each arm so results exist."""
    from esoi import __main__ as cli
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        for impl in ("live", "shout"):
            assert cli.main(["run", "greet_a_person", "--impl", impl]) == 0
    finally:
        os.chdir(cwd)
    monkeypatch.syspath_prepend(str(repo))
    for name in [m for m in sys.modules if m == "demo" or m.startswith("demo.")]:
        sys.modules.pop(name)
    parts = Assembler("demo", repo / "demo", modules=("demo.greet",), records=repo)
    parts.prepare()
    for name in ("live", "shout"):   # arms named as the results name them
        declare.register("greet-a-person", name, lambda person: person, scope="demo")
    return parts


@pytest.fixture
def demo_cleanup():
    yield
    for name in [m for m in sys.modules if m == "demo" or m.startswith("demo.")]:
        sys.modules.pop(name)
    for key in [k for k in selection_registry.REGISTRY if k[0] == "demo"]:
        selection_registry.REGISTRY.pop(key)
    selection_registry.PROJECTS.clear()


def test_metric_order_ranks_arms_from_the_scopes_own_results(repo, monkeypatch, demo_cleanup):
    parts = project_assembler(repo, monkeypatch)
    order, lead, note = parts.metric_order("greet-a-person", "shout")
    assert order == ["shout", "live", "greet"]   # the selected arm first, then the leaderboard's order (live 2/2, shout 1/2), then unrun arms
    again, lead_again, _ = parts.metric_order("greet-a-person", "live")
    assert again[:2] == ["live", "shout"] and "ranked by the leaderboard" in note
    assert lead == 0.0 and lead_again == 0.0   # two cases are not a significant lead


def test_metric_order_falls_back_to_snapshot_order_and_says_so(toy):
    parts, _ = toy
    order, lead, note = parts.metric_order("seat-a", "")
    assert lead is None and "no records packaged" in note and "snapshot" in note


def test_a_results_file_without_the_arms_falls_back_to_record_order(repo, monkeypatch, demo_cleanup):
    monkeypatch.syspath_prepend(str(repo))
    parts = Assembler("demo", repo / "demo", modules=("demo.greet",), records=repo)
    parts.prepare()
    order, lead, note = parts.metric_order("greet-a-person", "greet")
    assert lead is None and "record order" in note and order[0] == "greet"


def test_the_ladder_uses_the_leaderboard_by_default_and_hooks_override(toy, monkeypatch):
    assembler, _ = toy
    calls = []
    monkeypatch.setattr(Assembler, "metric_order", lambda self, sid, name="": (calls.append((sid, name)) or ([name, "delta"], 0.0, f"{sid}: ranked")))
    alpha = selection_registry.REGISTRY[("esoireq", "seat-a")].implementations["alpha"]
    saved = alpha.REQUIRES
    alpha.REQUIRES = (declarations.python("toypkg_mod", "toypkg>=2"),)
    try:
        config = cfg(**{"seat-a": "alpha", "seat-b": "gamma"})
        chosen, _ = assembly_plan.assembly_plan(assembler, config, {})
        assert chosen.substitutions and chosen.substitutions[0].using == "delta" and calls
        assert any("ranked" in note for note in chosen.notes)
        calls.clear()
        assembly_plan.assembly_plan(assembler, config, {}, rank=lambda sid, name: ["delta"], lead=lambda sid: 0.0)
        assert calls == []   # explicit hooks win, the leaderboard is not consulted
    finally:
        alpha.REQUIRES = saved
