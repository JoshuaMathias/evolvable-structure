"""``esoi init``: write a small repository as a starting point, passing every rule except the two cells only you can write.

The example is a top intent plus one solution, ``greet-a-person``, with two implementations (the package function and a
shouting baseline), one ideal, one problem, a metric (``esoi run greet_a_person --impl live``), the component rows that
own every file and a recorded run. The top intent is why your project exists, in your own words, so ``intent.csv`` is
written with its name and vision statement empty and ``esoi check`` reports both until you fill them; it is never filled
with text about ESOI. The evolvable structure the project applies is a solution inside that top intent
(``project-structure``), whose implementation uses esoi (``@esoi/structure-check`` names a solution of another project).
There is no sub-intent: one needs an opportunity that a person names. Rename the parts, replace the example text with
your own, and keep running ``esoi check``.

The records carry every field of the shipped intent template. A field the template has that this module has no
sample text for is written empty, so ``esoi check`` names it instead of passing a placeholder.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from . import check as check_module
from . import leaderboard
from .config import DEFAULT_STRUCTURE_DIR, Config, from_mapping
from .records import FILES, TEMPLATE_DATA, fields, load_template
from .tables import render_csv

SOLUTION = "greet-a-person"
COMPONENT = "greet_a_person"

SAMPLE: Dict[str, Dict[str, str]] = {
    "problem": {
        "problem": "People are greeted by hand, so greetings come out inconsistent and sometimes use the wrong name.",
        "who_has_it": "Anyone who sends a greeting to many people.",
        "why_it_matters": "A greeting that gets the name wrong or reads differently each time makes the sender look careless.",
        "why_hard": "Names arrive in many shapes, and a quick fix for one shape breaks another.",
        "existing_attempts": "Typing each greeting by hand, and copy and paste from the last one."},
    "ideal": {
        "name": "Consistent greeting",
        "principle": "Every person is greeted the same way, by their own name.",
        "state_description": "Anyone reading a greeting sees their name, spelled as given, in the same warm form.",
        "hints_of_measurement": "Every sample name comes back inside the greeting, and the form never varies."},
    "solution": {
        "name": "Greeting function",
        "scoped_purpose": "Greet one person by name in plain text. It does not translate or personalise beyond the name.",
        "goals": "Each sample name appears in a greeting of the standard form.",
        "knowledge": "The house style for greetings.",
        "measures_of_success": "Every example case passes.",
        "parameters": "None.",
        "inputs": "A name as text.",
        "outputs": "A greeting as text.",
        "effects": "None.",
        "usage_notes": "Call it wherever a greeting is needed instead of building the text inline."},
    "implementation": {
        "name": "",
        "description": "",
        "advantages": "",
        "disadvantages": ""},
    "metric": {
        "name": "Greeting pass rate",
        "scoped_purpose": "Measures whether the greeting keeps the name and the standard form.",
        "record": "Cases passed out of cases run, per implementation, on the same cases."},
}
IMPLEMENTATIONS = {
    "greet": ("Package function", "Formats the name into the standard greeting.", "Simple and matches the house style.",
              "Only one language."),
    "live": ("Live arm", "Calls the package function through the harness so the measured code is the shipped code.",
             "Measures what ships.", "Adds nothing of its own."),
    "shout": ("Shouting baseline", "Upper-cases the whole greeting, a floor someone might plausibly ship.",
              "Trivial to write.", "Breaks the standard form."),
}
# The top intent is why THIS project exists, in its own words, so the scaffold leaves it empty: `esoi check` reports the
# name and the vision statement until the project fills them. The sample below is a stand-in project (greetings) only to
# show the shape; replace it with your own.
SAMPLE["intent"] = {"name": "", "vision_statement": ""}
# The starter solution for the project's own structure: how its intent is recorded, measured and selected. Its
# implementation uses the generic esoi solutions; whatever is specific to this project belongs here in its top intent.
OVERALL = {
    "problem": {
        "problem": "What this project is for has no single written statement, so its parts drift from any shared intent.",
        "who_has_it": "People and AI agents who change the project.",
        "why_it_matters": "Without a stated purpose nobody can say whether a change helps.",
        "why_hard": "Intent is held in people's heads and changes over time.",
        "existing_attempts": "A README and chat history."},
    "ideal": {
        "name": "Explicit purpose",
        "principle": "Every part of the project traces up to a stated problem and ideal.",
        "state_description": "Opening any record, you can follow it up to the project's purpose.",
        "hints_of_measurement": "Every solution is built on, or builds, the project's structure."},
    "solution": {
        "name": "Project structure",
        "scoped_purpose": "How this project records its intent, measures alternatives and selects the best by metric; "
                          "its implementation uses the esoi solutions and holds whatever is specific to this project.",
        "goals": "Each building block of the structure has a metric and a recorded run.",
        "knowledge": "The project's own history and goals, and the esoi documentation.",
        "measures_of_success": "Every solution of the project links up to it."},
    "metric": {
        "name": "Coverage by measured solutions",
        "scoped_purpose": "Measures whether the structure's building blocks each have a recorded run.",
        "record": "The share of solutions the structure's implementation builds on that have a recorded run."},
}

CONFIG = '''# esoi configuration for this repository. Every key is optional; see the esoi documentation.
package = "{package}"
layers = ["core"]
code_paths = ["{package}"]
'''
GREET = '''"""The example solution: greet a person by name."""


def greet(name: str) -> str:
    """The greeting for ``name`` in the standard form."""
    return f"Hello, {name}!"
'''
INIT = '"""{package}: replace this docstring with what the package is for."""\n'
SCORE = '''"""Score one greeting case against its declarative ``expect``."""
from esoi import expect


def score_case(fn, case):
    return expect.score_kind_case(fn, case)
'''
LIVE = '''"""CURRENT: the live greeting function, called through the harness."""
from {package}.greet import greet


def build(meter):
    def run(kind, args):
        return {{"text": greet(args["name"])}}
    return run
'''
SHOUT = '''"""BASELINE: shouts the greeting in capitals, a floor the live function is measured against."""


def build(meter):
    def run(kind, args):
        return {"text": f"HELLO, {args['name'].upper()}!"}
    return run
'''
CASES = ('[{"id": "G-1", "kind": "greet", "area": "form", "args": {"name": "Ada"}, "expect": {"max_len": 20}},\n'
         ' {"id": "G-2", "kind": "greet", "area": "form", "args": {"name": "Grace"}, "expect": {"eq": {"text": "Hello, Grace!"}}}]\n')
TEST = '''"""Pins the example greeting."""
from {package}.greet import greet


def test_greet_uses_the_name():
    assert greet("Ada") == "Hello, Ada!"
'''
RESULT_COLUMNS = ["date", "component", "impl", "cases", "passed", "dev", "heldout", "model_calls", "tokens_in",
                  "tokens_out", "cost_usd", "seconds", "git_sha", "cases_sha", "model", "details"]


def python_name(text: str) -> str:
    name = re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower() or "mypackage"
    return name if not name[0].isdigit() else "pkg_" + name


def record(entity: str, template, sample: Dict[str, str], **fixed: str) -> Dict[str, str]:
    row = {key: sample.get(key, "") for key in fields(template, entity, True)}
    row.update(fixed)
    return row


def files_for(package: str, template) -> Dict[str, str]:
    """Every file of the example repository, by relative path."""
    greet_paths = [f"{package}/greet.py", f"evaluation/components/{COMPONENT}/impls/live.py",
                   f"evaluation/components/{COMPONENT}/impls/shout.py"]
    command = f"esoi run {COMPONENT} --impl live"
    structure = DEFAULT_STRUCTURE_DIR

    def sol_cols(extra: List[str]) -> List[str]:
        return ["solution_id"] + fields(template, "solution", True) + extra

    solution = record("solution", template, SAMPLE["solution"], solution_id=SOLUTION, problem_ids="greeting-by-hand",
                      ideal_ids="consistent-greeting", metric_ids="greeting-pass-rate", port="",
                      implementations=";".join(greet_paths), selected=greet_paths[0], selected_by="measured on the example cases",
                      metric_kind="eval", invariant_reason="", gap="", action="")
    top = record("solution", template, OVERALL["solution"], solution_id="project-structure", problem_ids="purpose-unrecorded",
                 ideal_ids="explicit-purpose", metric_ids="structure-coverage", implementations="esoi-records",
                 selected="esoi-records", selected_by="the only way to carry it out so far", metric_kind="specification")
    impl_rows = []
    for path in greet_paths:
        stem = path.rsplit("/", 1)[-1][:-3]
        name, description, advantages, disadvantages = IMPLEMENTATIONS[stem]
        impl_rows.append(record("implementation", template, dict(name=name, description=description, advantages=advantages,
                                disadvantages=disadvantages), implementation_id=f"{SOLUTION}:{stem}", solution_id=SOLUTION, path=path))
    impl_rows.append(record("implementation", template, dict(name="Records and checks with esoi", description="The project's intent records, checked and selected by metric with esoi, plus the solutions of this project.",
                                                             advantages="Reuses the generic esoi solutions instead of building them again.",
                                                             disadvantages="Depends on esoi; no rival has been compared yet."),
                            implementation_id="project-structure:esoi-records", solution_id="project-structure",
                            uses_solution_ids=SOLUTION + ";@esoi/structure-check"))
    out: Dict[str, str] = {}
    out[f"{structure}/intent.csv"] = render_csv(
        ["intent_id"] + fields(template, "intent", True) + ["implements", "opportunity"],
        [record("intent", template, SAMPLE["intent"], intent_id=package.replace("_", "-"))])
    out[f"{structure}/problems.csv"] = render_csv(
        ["problem_id"] + fields(template, "problem", True) + ["solution_ids", "ideal_ids", "parent_problem_ids", "parent_ideal_ids"],
        [record("problem", template, SAMPLE["problem"], problem_id="greeting-by-hand", solution_ids=SOLUTION,
                ideal_ids="consistent-greeting"),
         record("problem", template, OVERALL["problem"], problem_id="purpose-unrecorded", solution_ids="project-structure",
                ideal_ids="explicit-purpose")])
    out[f"{structure}/ideals.csv"] = render_csv(
        ["ideal_id"] + fields(template, "ideal", True) + ["problem_ids", "parent_ideal_ids"],
        [record("ideal", template, SAMPLE["ideal"], ideal_id="consistent-greeting", problem_ids="greeting-by-hand"),
         record("ideal", template, OVERALL["ideal"], ideal_id="explicit-purpose", problem_ids="purpose-unrecorded")])
    out[f"{structure}/solutions.csv"] = render_csv(
        sol_cols(["problem_ids", "ideal_ids", "metric_ids", "port", "implementations", "selected", "selected_by", "metric_kind",
                  "invariant_reason", "gap", "action", "parent_problem_ids", "parent_ideal_ids"]), [solution, top])
    out[f"{structure}/implementations.csv"] = render_csv(
        ["implementation_id", "solution_id", "path"] + fields(template, "implementation", True)
        + ["sub_intent", "uses_solution_ids"], impl_rows)
    out[f"{structure}/metrics.csv"] = render_csv(
        ["metric_id"] + fields(template, "metric", True) + ["solution_ids", "command", "parent_metric_ids"],
        [record("metric", template, SAMPLE["metric"], metric_id="greeting-pass-rate", solution_ids=SOLUTION, command=command),
         record("metric", template, OVERALL["metric"], metric_id="structure-coverage", solution_ids="project-structure")])
    components = [
        ("package", "core", f"{package}/**", "The package's code.", SOLUTION),
        ("evaluation", "evaluation", "evaluation/**", "Cases, scorers and implementations the harness runs.", SOLUTION),
        ("tests", "tests", "tests/**", "Tests that pin the package.", SOLUTION),
        ("structure-registry", "docs", f"{structure}/**", "The intent records and the placement map.", SOLUTION),
        ("project-files", "docs", "*", "Files at the repository root.", SOLUTION)]
    out[f"{structure}/components.csv"] = render_csv(
        ["component_id", "layer", "path", "role", "solutions"],
        [dict(zip(["component_id", "layer", "path", "role", "solutions"], c)) for c in components])
    out[f"{structure}/waivers.csv"] = render_csv(["rule", "path", "reason"], [])
    out[f"{structure}/esoi_template.csv"] = TEMPLATE_DATA.read_text(encoding="utf-8")
    out["esoi.toml"] = CONFIG.format(package=package)
    out[".gitignore"] = "__pycache__/\n.esoi_cache/\n"
    out[f"{package}/__init__.py"] = INIT.format(package=package)
    out[f"{package}/greet.py"] = GREET
    out["tests/test_greet.py"] = TEST.format(package=package)
    base = f"evaluation/components/{COMPONENT}"
    out[f"{base}/__init__.py"] = ""
    out[f"{base}/score.py"] = SCORE
    out[f"{base}/cases.json"] = CASES
    out[f"{base}/impls/__init__.py"] = ""
    out[f"{base}/impls/live.py"] = LIVE.format(package=package)
    out[f"{base}/impls/shout.py"] = SHOUT
    return out


def result_rows(root: Path) -> str:
    sha = leaderboard.cases_digest(COMPONENT, root / "evaluation" / "components")
    base = dict(date="2026-01-01", component=COMPONENT, heldout="0/0", model_calls="0", tokens_in="0", tokens_out="0",
                cost_usd="0.0", seconds="0.0", git_sha="scaffold", cases_sha=sha, model="none", details="", cases="2")
    return render_csv(RESULT_COLUMNS, [dict(base, impl="live", passed="2", dev="2/2"), dict(base, impl="shout", passed="1", dev="1/2")])


def init(root: Path, package: str = "", force: bool = False, say=print) -> List[str]:
    """Write the example repository under ``root``; returns the files written. Existing files are never overwritten
    unless ``force`` is set."""
    root = Path(root).resolve()
    package = python_name(package or root.name)
    template = load_template()
    contents = files_for(package, template)
    written, skipped = [], []
    for rel, text in contents.items():
        path = root / rel
        if path.exists() and not force:
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(rel)
    results = root / "evaluation" / "components" / "results.csv"
    if not results.exists() or force:
        results.write_text(result_rows(root), encoding="utf-8")
        written.append("evaluation/components/results.csv")
    config = from_mapping({"package": package, "layers": ["core"], "structure_dir": DEFAULT_STRUCTURE_DIR}, root)
    check_module.write_docs(config, say=lambda text: None)
    for rel in skipped:
        say(f"kept existing {rel}")
    say(f"wrote {len(written)} file(s) under {root}")
    return written
