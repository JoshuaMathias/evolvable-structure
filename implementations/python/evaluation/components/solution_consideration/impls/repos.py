"""Shared by the arms: the two repositories the cases read, each loaded once (the synthetic one written to a temporary folder)."""
import atexit
import shutil
import tempfile
from pathlib import Path

from esoi.structure.intent_registry import config as config_module
from esoi.understanding.solution_consideration import solution_prompt
from shared_fixtures.consideration_fixture import write_repo

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "esoi.toml").is_file())
LOADED = {}


def network(repo):
    """The network of ``fixture`` or ``live`` (results staleness is not judged: the cases ask what reaches the pass)."""
    if repo not in LOADED:
        if repo == "fixture":
            folder = Path(tempfile.mkdtemp(prefix="esoi-consider-"))
            atexit.register(shutil.rmtree, folder, True)
            root = write_repo(folder)
        else:
            root = ROOT
        LOADED[repo] = solution_prompt.load(config_module.load(root), stale=False)
    return LOADED[repo]
