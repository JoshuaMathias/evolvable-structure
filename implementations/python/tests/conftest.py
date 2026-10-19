"""Shared test fixtures: a scaffolded repository that passes every rule."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from esoi import config, scaffold  # noqa: E402

TEMPLATE_REPO = {}


def fill_top_intent(root):
    """The scaffold leaves the top intent and the top solution to the project; the fixture writes the stand-in project's own."""
    from esoi import tables
    folder = Path(root) / "esoi"

    def edit(name, change):
        rows, cols = tables.read_csv(folder / name), tables.read_header(folder / name)
        for row in rows:
            change(row)
        tables.write_csv(folder / name, cols, rows)

    edit("intent.csv", lambda r: r.update(name="Consistent greetings", vision_statement="Every person is greeted by their own name."))
    edit("solutions.csv", lambda r: r["solution_id"] == "project-purpose" and r.update(
        name="Greetings sent", scoped_purpose="Everything that greets a person for this project.",
        goals="Every greeting is consistent.", knowledge="The house style for greetings.",
        measures_of_success="The greeting cases pass.", problem_ids="greeting-by-hand", ideal_ids="consistent-greeting",
        metric_ids="greeting-pass-rate"))
    edit("implementations.csv", lambda r: r["implementation_id"] == "project-purpose:the-project" and r.update(
        name="The project", description="The greeting function and the structure that records and checks it.",
        advantages="One place to start.", disadvantages="Nothing rival has been compared."))
    edit("problems.csv", lambda r: r["problem_id"] == "greeting-by-hand" and r.update(solution_ids=r["solution_ids"] + ";project-purpose"))
    edit("metrics.csv", lambda r: r["metric_id"] == "greeting-pass-rate" and r.update(solution_ids=r["solution_ids"] + ";project-purpose"))
    from esoi import registry, tracker   # the tracker tabs follow the records
    cfg = config.load(root)
    tracker.write(cfg, registry.load(cfg), say=lambda text: None)


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
    return copy


@pytest.fixture
def cfg(repo):
    return config.load(repo)
