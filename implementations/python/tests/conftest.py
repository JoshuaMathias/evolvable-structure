"""Shared test fixtures: a scaffolded repository that passes every rule."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from esoi import config, scaffold  # noqa: E402

TEMPLATE_REPO = {}


@pytest.fixture
def repo(tmp_path_factory):
    """A fresh copy of the scaffolded example repository (built once per session)."""
    if "root" not in TEMPLATE_REPO:
        root = tmp_path_factory.mktemp("scaffold") / "demo"
        root.mkdir()
        scaffold.init(root, "demo", say=lambda text: None)
        TEMPLATE_REPO["root"] = root
    copy = tmp_path_factory.mktemp("case") / "demo"
    shutil.copytree(TEMPLATE_REPO["root"], copy)
    return copy


@pytest.fixture
def cfg(repo):
    return config.load(repo)
