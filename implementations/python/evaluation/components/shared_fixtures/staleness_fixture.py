"""A tiny git repository for the staleness evaluations, built in a temp directory from ``staleness_precision/datasets/fixture.json``.

``decide(rule, step, component)`` builds the repository (once per step), records a result for each component at the first
commit, applies the step (a commit, an uncommitted edit, a rename) and asks the live ``esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_reasons.stale_reason`` under the
named staleness rule whether that component's result still counts. No model, no network, nothing outside the temp directory.
"""
from __future__ import annotations

import atexit
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

from esoi.structure.intent_registry import config
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reason
from esoi.optimization.leaderboard.case_identity import cases_digest

RECIPE = Path(__file__).resolve().parent.parent / "staleness_precision" / "datasets" / "fixture.json"
BUILT: Dict[str, "Built"] = {}
FOLDERS: list = []


class Built:
    """One built step: the repository, the commit the results were recorded at, and each component's recorded row."""

    def __init__(self, root: Path, sha: str, rows: Dict[str, Dict[str, str]]):
        self.root, self.sha, self.rows = root, sha, rows


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def build(step: str) -> Built:
    if step in BUILT:
        return BUILT[step]
    recipe = json.loads(RECIPE.read_text())
    root = Path(tempfile.mkdtemp(prefix="staleness-"))
    FOLDERS.append(root)
    git(root, "init", "-q", ".")
    git(root, "config", "user.email", "fixture@example.com")
    git(root, "config", "user.name", "fixture")
    git(root, "config", "commit.gpgsign", "false")
    for rel, text in recipe["files"].items():
        write(root, rel, text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    sha = git(root, "rev-parse", "--short", "HEAD")
    cfg = config.load(root / "esoi.toml")
    rows = {comp: dict(component=comp, impl="live", git_sha=sha, cases_sha=cases_digest(f"{comp}_eval", cfg.evaluation), date="2026-01-01",
                       sample="", code_shas="")
            for comp in recipe["components"]}
    for op in recipe["steps"][step]:
        if op[0] == "write":
            write(root, op[1], op[2])
        elif op[0] == "rename":
            git(root, "mv", op[1], op[2])
        elif op[0] == "commit":
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", step)
    BUILT[step] = Built(root, sha, rows)
    return BUILT[step]


def decide(rule: str, step: str, component: str) -> Dict[str, object]:
    """Whether the live check calls ``component``'s recorded result stale at ``step`` under the rule, and its reason."""
    built = build(step)
    cfg = config.load(built.root / "esoi.toml")
    cfg.staleness_rule = rule
    why = stale_reason(cfg, f"{component}_eval", built.rows[component])
    return {"stale": bool(why), "why": why}


def cleanup() -> None:
    for folder in FOLDERS:
        shutil.rmtree(folder, ignore_errors=True)


atexit.register(cleanup)
