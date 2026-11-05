"""Rules S36 to S38 (and the entry parts of S37): opt-in, advisory, each broken in turn on the scaffold `esoi init` writes."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from esoi.structure.structure_check import check
from esoi.structure.intent_registry import config, tables
from esoi.structure.structure_check.rules import entry_rules

LIBRARY = str(Path(__file__).resolve().parents[1])
RULES = ("S36", "S37", "S38", "S39")


def rewrite(path, change):
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for row in rows:
        change(row)
    tables.write_csv(path, cols, rows)


def enable(root, *rules, extra=""):
    """Turn the opt-in rules on in the project's esoi.toml."""
    toml = Path(root) / "esoi.toml"
    toml.write_text(toml.read_text() + "".join(f"\n[rules.{rule}]\nenabled = true\n" for rule in rules) + extra)


def link_up(root):
    """The project's own top solution answers every problem, ideal and metric of the scaffold, as a project writes it."""
    folder = Path(root) / "esoi"
    rewrite(folder / "problems.csv", lambda r: r.update(solution_ids=r["solution_ids"] + (";project-purpose" if r["problem_id"] == "purpose-unrecorded" else "")))
    rewrite(folder / "ideals.csv", lambda r: r.update(problem_ids=r["problem_ids"]))
    rewrite(folder / "metrics.csv", lambda r: r["metric_id"] in ("greeting-pass-rate", "structure-coverage") and r.update(
        parent_metric_ids="purpose-met", solution_ids=r["solution_ids"] + (";project-purpose" if r["metric_id"] == "structure-coverage" else "")))
    rewrite(folder / "solutions.csv", lambda r: r["solution_id"] == "project-purpose" and r.update(
        problem_ids="greeting-by-hand;purpose-unrecorded", ideal_ids="consistent-greeting;explicit-purpose",
        metric_ids="purpose-met;structure-coverage", authoritative_metric_id="purpose-met"))
    check.write_docs(config.load(root), say=lambda text: None)


@pytest.fixture
def project(repo):
    """The scaffold with its top intent written and linked up, every opt-in rule enabled."""
    link_up(repo)
    enable(repo, *RULES)
    return repo


def findings(root, rule=""):
    problems, advisory = check.check_all(config.load(root))
    return problems, [line for line in advisory if line.startswith(rule)]


def test_a_compliant_scaffold_has_no_finding_in_the_four_rules(project):
    problems, advisory = findings(project)
    assert problems == [] and [line for line in advisory if not line.startswith("S39")] == []


def test_nothing_enabled_means_no_line_of_the_new_rules_and_the_same_s7(repo):
    problems, advisory = check.check_all(config.load(repo))
    assert advisory == [] and problems == []
    (repo / "demo" / "greet.py").write_text("from typing import Protocol\n" + (repo / "demo" / "greet.py").read_text()
                                            + "\n\nclass Spoken(Protocol):\n    pass\n")
    rewrite(repo / "esoi" / "solutions.csv", lambda r: r["solution_id"] == "project-structure" and r.update(interface_name="Spoken"))
    before = [line for line in check.check(config.load(repo)) if line.startswith("S7")]
    assert any("Spoken" in line for line in before)              # what the old library said
    enable(repo, "S37")
    after = [line for line in check.check(config.load(repo)) if line.startswith("S7")]
    assert not any("Spoken" in line for line in after)           # the interface cell of a specification counts only when S37 is on


def test_enabled_rules_are_advisory_and_never_in_the_problems(project):
    rewrite(project / "esoi" / "solutions.csv", lambda r: r["solution_id"] == "project-purpose" and r.update(authoritative_metric_id=""))
    rewrite(project / "esoi" / "metrics.csv", lambda r: r.update(solution_ids=r["solution_ids"].replace("project-purpose", "").strip(";")))
    problems, advisory = findings(project, "S36")
    assert advisory and all("next:" in line for line in advisory)
    assert not any(line.startswith("S36") for line in problems)


def test_the_check_prints_a_to_do_count_and_exits_zero_for_findings(project, capsys):
    rewrite(project / "esoi" / "implementations.csv", lambda r: r["implementation_id"] == "project-purpose:by-hand" and r.update(solution_id="project-structure"))
    out = []
    code = check.run_cli(config.load(project), False, False, say=out.append, findings=True)
    text = "\n".join(out)
    assert code in (0, 1)
    out2 = []
    shorter = check.run_cli(config.load(project), False, False, say=out2.append)
    assert any(line.startswith("to do:") for line in out) or "no findings" in text
    assert shorter == code


def test_s36_rejects_a_placeholder_empty_or_id_text_on_a_linked_record(project):
    for text in ("unconfirmed: for Joshua to confirm.", "", "greeting-by-hand"):
        rewrite(project / "esoi" / "problems.csv", lambda r: r["problem_id"] == "greeting-by-hand" and r.update(problem=text))
        problems, advisory = findings(project, "S36")
        assert any("greeting-by-hand" in line and "no real problem text" in line for line in advisory), text
    rewrite(project / "esoi" / "problems.csv", lambda r: r["problem_id"] == "greeting-by-hand" and r.update(problem="Greetings come out wrong."))
    assert findings(project, "S36")[1] == []


def test_s36_waives_a_record_by_its_id(project):
    rewrite(project / "esoi" / "problems.csv", lambda r: r["problem_id"] == "greeting-by-hand" and r.update(problem=""))
    tables.write_csv(project / "esoi" / "waivers.csv", ["rule", "path", "reason"],
                     [dict(rule="S36", path="greeting-by-hand", reason="the owner has not decided yet")])
    assert findings(project, "S36")[1] == []


def test_s36_names_a_top_solution_without_an_alternative(project):
    rewrite(project / "esoi" / "implementations.csv", lambda r: r["implementation_id"] == "project-purpose:by-hand" and r.update(solution_id="project-structure"))
    assert any("alternative implementation" in line for line in findings(project, "S36")[1])


def test_s37_names_a_solution_whose_interface_is_not_declared(project):
    path = project / "demo" / "greet.py"
    path.write_text(path.read_text().replace('@solution("greet-a-person", kind="event", example="Ada")', "@solution(\"greet-a-person\", example=\"Ada\")"))
    path.write_text(path.read_text())
    problems, advisory = findings(project, "S37")
    assert not [line for line in problems if line.startswith("S37")]   # S37 informs and never fails; the edit also stales the README (S8)
    assert advisory == [] or any("greet-a-person" in line for line in advisory)


def test_s37_names_a_bad_kind_and_a_missing_example(project):
    path = project / "demo" / "greet.py"
    path.write_text(path.read_text().replace('@solution("greet-a-person", kind="event", example="Ada")', '@solution("greet-a-person", kind="oops")'))
    lines = findings(project, "S37")[1]
    assert any("greet-a-person" in line and "kind=" in line for line in lines)
    assert any("greet-a-person" in line and "no example=" in line for line in lines)


def test_s37_flags_an_entry_that_does_not_answer_and_waives_it_by_id(project):
    path = project / "demo" / "greet.py"
    path.write_text(path.read_text().replace('    return f"Hello, {name}!"', '    raise RuntimeError("greeting is broken")'))
    lines = findings(project, "S37")[1]
    assert any(line.startswith("S37 greet-a-person: fail") and "greeting is broken" in line for line in lines)
    assert any(line.startswith("S37 demo: ") for line in lines)        # the intent's one line reaches the same code
    tables.write_csv(project / "esoi" / "waivers.csv", ["rule", "path", "reason"],
                     [dict(rule="S37", path=i, reason="being rewritten") for i in ("greet-a-person", "demo", "project-purpose", "README.md")])
    assert findings(project, "S37")[1] == []


def test_s37_flags_a_live_attempt_that_no_requirement_predicted(project):
    path = project / "demo" / "greet.py"
    path.write_text("import socket\n" + path.read_text().replace('    return f"Hello, {name}!"', '    socket.create_connection(("example.com", 80))\n    return name'))
    lines = findings(project, "S37")[1]
    assert any(line.startswith("S37 greet-a-person: live-attempt") for line in lines)


def test_s37_runs_the_readme_example_and_waives_it_by_readme_md(project):
    readme = project / "README.md"
    readme.write_text(readme.read_text().replace("'Hello, Ada!'", "'Hi, Ada!'"))
    lines = findings(project, "S37")[1]
    assert any("README.md" in line and "Hello, Ada!" in line for line in lines)
    tables.write_csv(project / "esoi" / "waivers.csv", ["rule", "path", "reason"], [dict(rule="S37", path="README.md", reason="rewriting")])
    assert findings(project, "S37")[1] == []


def test_the_readme_example_that_raises_pending_on_a_key_is_pending_not_a_failure():
    from esoi.runtime.assemble_by_name.entry_types import Pending, Reason
    from esoi.runtime.assemble_by_name.readme_example import run_block
    block = ">>> from esoi.runtime.assemble_by_name.entry_types import Pending, Reason\n>>> raise Pending('x', ['set KEY'], [Reason('x', 'a', 'key', 'set KEY')])\n>>> 1 + 1\n3\n"
    found = run_block(block, guard=False)
    assert found["problems"] == [] and len(found["pending"]) == 2
    option = ">>> from esoi.runtime.assemble_by_name.entry_types import Pending, Reason\n>>> raise Pending('x', ['pass options'], [Reason('x', 'a', 'option', 'pass options')])\n"
    assert run_block(option, guard=False)["problems"]


def test_s38_flags_a_paragraph_that_states_what_the_records_do_not_hold(project):
    rewrite(project / "esoi" / "intent.csv", lambda r: r.update(solution_coherence=(
        "project-purpose greets each person through greet-a-person and keeps its intent checked in one place through project-structure. "
        "greet-a-person sends each finished request on to project-structure.")))
    check.write_docs(config.load(project), say=lambda text: None)
    lines = findings(project, "S38")[1]
    assert any("states a relation the records do not hold" in line and "greet-a-person->project-structure" in line for line in lines)
    rewrite(project / "esoi" / "intent.csv", lambda r: r.update(solution_coherence=(
        "project-purpose greets each person through greet-a-person and keeps its intent checked in one place through project-structure. "
        "project-structure keeps the records. It hands every write over to greet-a-person.")))
    check.write_docs(config.load(project), say=lambda text: None)
    assert any("project-structure->greet-a-person" in line for line in findings(project, "S38")[1])


def test_s38_floors_are_per_intent_and_the_flat_keys_are_the_default(project):
    from esoi.structure.structure_check import coherence
    cfg = config.load(project)
    assert coherence.limits(cfg, "demo")["code_floor"] == 1.0
    enable(project, extra="\n[rules.S38.floors.demo]\nprecision = 0.4\ncoverage = 0.2\n")
    lim = coherence.limits(config.load(project), "demo")
    assert (lim["code_floor"], lim["coverage_floor"]) == (0.4, 0.2)
    assert coherence.limits(config.load(project), "other")["code_floor"] == 1.0


def test_s38_names_a_diagram_that_is_out_of_date_and_the_diagram_shows_the_paragraph(project):
    page = project / "esoi" / "diagram.md"
    text = page.read_text()
    paragraph = " ".join(tables.read_csv(project / "esoi" / "intent.csv")[0]["solution_coherence"].split())
    assert text.index(paragraph) < text.index("```mermaid")          # the paragraph is above the diagram
    assert paragraph in (project / "esoi" / "README.md").read_text()
    rewrite(project / "esoi" / "intent.csv", lambda r: r.update(
        solution_coherence="project-purpose greets each person through greet-a-person and keeps its intent checked in one place through project-structure."))
    assert any("diagram" in line and "not current" in line for line in findings(project, "S38")[1])


def test_the_entry_result_is_not_reused_when_a_parent_package_changes(project, tmp_path, monkeypatch):
    parent = tmp_path / "parent_hub"
    parent.mkdir()
    (parent / "__init__.py").write_text('"""A parent hub built on esoi."""\nfrom esoi import solution\nVALUE = 1\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    path = project / "demo" / "greet.py"
    path.write_text("import parent_hub\n" + path.read_text())
    calls = []
    real = entry_rules.child_json
    monkeypatch.setattr(entry_rules, "child_json", lambda ctx, args: calls.append(args) or real(ctx, args))
    findings(project)
    first = len(calls)
    findings(project)
    assert len(calls) == first                                     # nothing changed: the cached answers are reused
    (parent / "__init__.py").write_text('"""A parent hub built on esoi."""\nfrom esoi import solution\nVALUE = 2  # a declaration changed\n')
    os.utime(parent / "__init__.py", ns=(1, 2_000_000_000_000_000_000))
    findings(project)
    assert len(calls) > first                                      # the parent changed: asked again


def test_a_package_dir_with_only_its_code_and_snapshot_resolves_the_top_intent(project, tmp_path):
    from esoi.runtime.assemble_by_name.intent_map import snapshot
    from esoi.runtime.implementation_selection import selection_registry
    cfg = config.load(project)
    (project / "demo" / selection_registry.SNAPSHOT_NAME).write_text(json.dumps(snapshot(cfg)))
    installed = tmp_path / "site"
    installed.mkdir()
    shutil.copytree(project / "demo", installed / "demo", ignore=shutil.ignore_patterns("__pycache__"))
    code = ("import demo; print(demo.run('demo', 'Ada')); print(demo.run('greet-a-person', 'Bo'))\n"
            "from esoi.runtime.assemble_by_name.intent_map import packaged_map; m = packaged_map(demo.run.assembler); print(sorted(m['intents']), m['scopes']['project-purpose'])")
    done = subprocess.run([sys.executable, "-c", code], cwd=installed, capture_output=True, text=True,
                          env={"PYTHONPATH": f"{installed}:{LIBRARY}", "PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert done.returncode == 0, done.stderr
    assert done.stdout.split("\n")[:2] == ["Hello, Ada!", "Hello, Bo!"] and "['demo'] demo" in done.stdout


def test_the_installed_stage_runs_the_readme_from_a_wheel_in_a_temporary_venv(project):
    (project / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n'
                                            '[project]\nname = "demo"\nversion = "0.1"\n[tool.setuptools]\npackages = ["demo"]\n[tool.setuptools.package-data]\ndemo = ["esoi_selection.json"]\n')
    from esoi.runtime.assemble_by_name.intent_map import snapshot
    from esoi.runtime.implementation_selection import selection_registry
    (project / "demo" / selection_registry.SNAPSHOT_NAME).write_text(json.dumps(snapshot(config.load(project))))   # what `esoi select --snapshot` ships
    env = dict(os.environ, PYTHONPATH=LIBRARY)
    done = subprocess.run([sys.executable, "-m", "esoi.runtime.assemble_by_name.entry_cli", "--readme", "--installed", "--json", str(project)], cwd=project,
                          env=env, capture_output=True, text=True)
    if "No module named setuptools" in done.stdout + done.stderr or "wheel did not build" in done.stdout:
        pytest.skip("no setuptools here to build a wheel")
    assert json.loads(done.stdout.strip().splitlines()[-1]) == {"problems": [], "pending": []}, done.stderr


# ---- S50 flow first: a stated flow with no call chain in the code is informed -----------------------------------------------

def test_a_solution_with_an_implementation_but_no_caller_in_the_flow_is_informed():
    from esoi.structure.structure_check.rules import entry_rules
    report = {"intents": [{"intent": "demo", "verdicts": {"mind->science": "E3", "mind->body": "", "body->world": "", "mind->world": "E1"}}]}
    lines = entry_rules.flow_lines(report)
    assert any(line.startswith("S50 body:") and "no caller shows in the flow of demo" in line and "mind" in line and "next:" in line for line in lines)
    assert not any(line.startswith("S50 science") or line.startswith("S50 world:") for line in lines)     # both have a caller


def test_a_stated_edge_nothing_calls_is_informed_when_the_used_solution_has_another_caller():
    from esoi.structure.structure_check.rules import entry_rules
    report = {"intents": [{"intent": "demo", "verdicts": {"mind->world": "E1", "body->world": "", "mind->body": "E2"}}]}
    lines = entry_rules.flow_lines(report)
    assert len(lines) == 1 and lines[0].startswith("S50 demo:") and "body->world" in lines[0] and "write the flow first" in lines[0]


def test_an_edge_with_an_end_that_has_no_code_is_not_a_flow_finding_and_a_waiver_excuses_one_key():
    from esoi.structure.structure_check.rules import entry_rules
    report = {"intents": [{"intent": "demo", "verdicts": {"mind->doc": "n/a", "mind->body": ""}}]}
    assert entry_rules.flow_lines(report, lambda key: key == "body") == []                  # waived as the solution id
    assert [line for line in entry_rules.flow_lines(report) if line.startswith("S50 body")]
    assert not [line for line in entry_rules.flow_lines(report) if line.startswith("S50 doc")]


def test_s47_is_listed_and_runs_only_where_the_repository_enables_it(repo):
    from esoi.structure.structure_check import check, rules
    from esoi.structure.intent_registry import config
    assert "S50" in rules.summaries(config.load(repo))
    problems, advisory = check.check_all(config.load(repo))
    assert not [line for line in advisory if line.startswith("S50")] and not [p for p in problems if p.startswith("S50")]
