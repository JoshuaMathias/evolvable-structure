"""Shared test fixtures: a scaffolded repository that passes every rule."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from esoi import config, scaffold  # noqa: E402

TEMPLATE_REPO = {}


def fill_top_intent(root):
    """The scaffold leaves the top intent's name and vision to the project; the fixture writes the stand-in project's own."""
    from esoi import tables
    path = Path(root) / "docs" / "structure" / "intent.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    rows[0].update(name="Consistent greetings", vision_statement="Every person is greeted by their own name.")
    tables.write_csv(path, cols, rows)


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
