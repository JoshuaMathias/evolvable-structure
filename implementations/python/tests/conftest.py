"""Shared test fixtures: a scaffolded repository that passes every rule."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from esoi.structure.intent_registry import config
from esoi.understanding.the_standard import scaffold

TEMPLATE_REPO = {}


def fill_top_intent(root):
    """The scaffold leaves the top intent and the top solution to the project; the fixture writes the stand-in project's own."""
    from esoi.structure.intent_registry import tables
    folder = Path(root) / "esoi"

    def edit(name, change):
        rows, cols = tables.read_csv(folder / name), tables.read_header(folder / name)
        for row in rows:
            change(row)
        tables.write_csv(folder / name, cols + [k for k in (rows[0] if rows else {}) if k not in cols], rows)   # a column the change adds

    edit("intent.csv", lambda r: r.update(name="Consistent greetings", vision_statement="Every person is greeted by their own name.",
                                         solution_coherence="Greetings sent (project-purpose) is the purpose, greet-a-person does the greeting, and project-structure records how."))
    edit("solutions.csv", lambda r: r["solution_id"] == "project-purpose" and r.update(
        name="Greetings sent", description="Every greeting the project sends is the one it meant to send.",
        purpose="Greet people for this project.", approach="Send each greeting through the one greeting function.",
        out_of_scope="Anything that is not a greeting.", tags='[{"tag": "greetings", "risk_ids": ["greeting-by-hand"]}]',
        milestones="1. Share of greetings in the standard form: 100%.", knowledge="The house style for greetings.",
        measures_of_success="The greeting cases pass.", problem_ids="greeting-by-hand", ideal_ids="consistent-greeting",
        metric_ids="purpose-met"))
    edit("implementations.csv", lambda r: r["implementation_id"] == "project-purpose:the-project" and r.update(
        name="The project", description="The greeting function and the structure that records and checks it.",
        advantages="One place to start.", disadvantages="Nothing rival has been compared."))
    edit("problems.csv", lambda r: r["problem_id"] == "greeting-by-hand" and r.update(solution_ids=r["solution_ids"] + ";project-purpose"))
    path = folder / "metrics.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    if not any(r["metric_id"] == "purpose-met" for r in rows):
        rows.append({**{col: "" for col in cols}, "metric_id": "purpose-met", "name": "Purpose met",
                     "purpose": "Ensure the greetings the project sends are the ones it meant to send.",
                     "disadvantages": "It is reviewed by hand, so it sees only what the reviewer looks at.",
                     "record": "Reviewed by hand; no run measures it yet.", "solution_ids": "project-purpose"})
    tables.write_csv(path, cols, rows)
    from esoi.structure.structure_check import check
    check.write_docs(config.load(root), say=lambda text: None)


@pytest.fixture
def repo(tmp_path_factory):
    """A fresh copy of the scaffolded example repository (built once per session)."""
    if "root" not in TEMPLATE_REPO:
        root = tmp_path_factory.mktemp("scaffold") / "demo"
        root.mkdir()
        scaffold.init(root, "demo", say=lambda text: None)
        fill_top_intent(root)
        TEMPLATE_REPO["root"] = root
    copy = tmp_path_factory.mktemp("case") / "demo"
    shutil.copytree(TEMPLATE_REPO["root"], copy)
    yield copy
    forget_demo_package(copy)


def forget_demo_package(root):
    """Each copy of the example repository is a package named ``demo`` at a different path. A command run in one (``records sync``)
    imports it and registers its solutions; left behind, the next copy would find this copy's ``demo`` modules and registry entries
    instead of its own, and fail with a missing module."""
    from esoi.runtime.implementation_selection import selection_registry
    for name, module in list(sys.modules.items()):
        if (name == "demo" or name.startswith("demo.")) and str(getattr(module, "__file__", "") or "").startswith(str(root)):
            sys.modules.pop(name)
    for key in [k for k in selection_registry.REGISTRY if k[0] == "demo"]:
        selection_registry.REGISTRY.pop(key)
    selection_registry.PROJECTS.clear()


@pytest.fixture
def cfg(repo):
    return config.load(repo)
