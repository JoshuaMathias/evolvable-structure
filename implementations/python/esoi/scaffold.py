"""``esoi init``: write a small repository that already passes ``esoi check``, as a starting point to edit.

The example is one solution, ``greet-a-person``, with two implementations (the package function and a shouting
baseline), one ideal, one problem, a metric (``esoi run greet_a_person --impl live``), the component rows that
own every file, a recorded run, and an overall solution network the detailed records link up to. Rename the
parts, replace the example text with your own intent, and keep running ``esoi check``.

The records carry every field of the shipped intent template. A field the template has that this module has no
sample text for is written empty, so ``esoi check`` names it instead of passing a placeholder.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from . import check as check_module
from . import leaderboard
from .config import Config, from_mapping
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
OVERALL = {
    "problem": {
        "problem": "What this repository is for has no single written statement, so its parts drift from any shared intent.",
        "who_has_it": "People and AI agents who change the repository.",
        "why_it_matters": "Without a stated purpose nobody can say whether a change helps.",
        "why_hard": "Intent is held in people's heads and changes over time.",
        "existing_attempts": "A README and chat history."},
    "ideal": {
        "name": "Explicit purpose",
        "principle": "Every part of the repository traces up to a stated problem and ideal.",
        "state_description": "Opening any record, you can follow it up to the overall purpose.",
        "hints_of_measurement": "Every detailed solution names the part of the overall solution it serves."},
    "solution": {
        "name": "Overall solution",
        "scoped_purpose": "Frames the repository's purpose; the detailed records implement it.",
        "goals": "Each area of the overall solution has detailed solutions beneath it.",
        "knowledge": "The repository's own history and goals.",
        "measures_of_success": "Every detailed solution links up to it."},
    "metric": {
        "name": "Link completeness",
        "scoped_purpose": "Measures whether detailed records link up to the overall network.",
        "record": "The share of detailed solutions that name a parent."},
}

CONFIG = '''# esoi configuration for this repository. Every key is optional; see the esoi documentation.
package = "{package}"
layers = ["core"]
overall = "docs/structure/overall"
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
    parents = ["parent_problem_ids", "parent_ideal_ids", "overall_solution_ids"]
    links = dict(parent_problem_ids="overall-problem", parent_ideal_ids="overall-ideal", overall_solution_ids="overall-solution")

    def sol_cols(extra: List[str]) -> List[str]:
        return ["solution_id"] + fields(template, "solution", True) + extra

    solution = record("solution", template, SAMPLE["solution"], solution_id=SOLUTION, problem_ids="greeting-by-hand",
                      ideal_ids="consistent-greeting", metric_ids="greeting-pass-rate", port="",
                      implementations=";".join(greet_paths), selected=greet_paths[0], selected_by="measured on the example cases",
                      metric_kind="eval", invariant_reason="", gap="", action="", **links)
    impl_rows = []
    for path in greet_paths:
        stem = path.rsplit("/", 1)[-1][:-3]
        name, description, advantages, disadvantages = IMPLEMENTATIONS[stem]
        impl_rows.append(record("implementation", template, dict(name=name, description=description, advantages=advantages,
                                disadvantages=disadvantages), implementation_id=f"{SOLUTION}:{stem}", solution_id=SOLUTION, path=path))
    out: Dict[str, str] = {}
    structure = "docs/structure"
    out[f"{structure}/problems.csv"] = render_csv(
        ["problem_id"] + fields(template, "problem", True) + ["solution_ids", "ideal_ids"] + parents[:2],
        [record("problem", template, SAMPLE["problem"], problem_id="greeting-by-hand", solution_ids=SOLUTION,
                ideal_ids="consistent-greeting", parent_problem_ids="overall-problem", parent_ideal_ids="overall-ideal")])
    out[f"{structure}/ideals.csv"] = render_csv(
        ["ideal_id"] + fields(template, "ideal", True) + ["problem_ids"] + parents[1:2],
        [record("ideal", template, SAMPLE["ideal"], ideal_id="consistent-greeting", problem_ids="greeting-by-hand",
                parent_ideal_ids="overall-ideal")])
    out[f"{structure}/solutions.csv"] = render_csv(
        sol_cols(["problem_ids", "ideal_ids", "metric_ids", "port", "implementations", "selected", "selected_by", "metric_kind",
                  "invariant_reason", "gap", "action"] + parents), [solution])
    out[f"{structure}/implementations.csv"] = render_csv(
        ["implementation_id", "solution_id", "path"] + fields(template, "implementation", True), impl_rows)
    out[f"{structure}/metrics.csv"] = render_csv(
        ["metric_id"] + fields(template, "metric", True) + ["solution_ids", "command"],
        [record("metric", template, SAMPLE["metric"], metric_id="greeting-pass-rate", solution_ids=SOLUTION, command=command)])
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
    overall = f"{structure}/overall"
    out[f"{overall}/problems.csv"] = render_csv(
        ["problem_id"] + fields(template, "problem", True) + ["solution_ids", "ideal_ids"],
        [record("problem", template, OVERALL["problem"], problem_id="overall-problem", solution_ids="overall-solution",
                ideal_ids="overall-ideal")])
    out[f"{overall}/ideals.csv"] = render_csv(
        ["ideal_id"] + fields(template, "ideal", True) + ["problem_ids"],
        [record("ideal", template, OVERALL["ideal"], ideal_id="overall-ideal", problem_ids="overall-problem")])
    out[f"{overall}/solutions.csv"] = render_csv(
        sol_cols(["problem_ids", "ideal_ids", "metric_ids", "implementations"]),
        [record("solution", template, OVERALL["solution"], solution_id="overall-solution", problem_ids="overall-problem",
                ideal_ids="overall-ideal", metric_ids="overall-link-completeness", implementations="the-package")])
    out[f"{overall}/implementations.csv"] = render_csv(
        ["implementation_id", "solution_id"] + fields(template, "implementation", True),
        [record("implementation", template, dict(name="The package", description="The repository's code and records.",
                                                 advantages="It is the thing itself.", disadvantages="It has no rival yet."),
                implementation_id="overall-solution:the-package", solution_id="overall-solution")])
    out[f"{overall}/metrics.csv"] = render_csv(
        ["metric_id"] + fields(template, "metric", True) + ["solution_ids"],
        [record("metric", template, OVERALL["metric"], metric_id="overall-link-completeness", solution_ids="overall-solution")])
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
    config = from_mapping({"package": package, "layers": ["core"], "overall": "docs/structure/overall"}, root)
    check_module.write_docs(config, say=lambda text: None)
    for rel in skipped:
        say(f"kept existing {rel}")
    say(f"wrote {len(written)} file(s) under {root}")
    return written
