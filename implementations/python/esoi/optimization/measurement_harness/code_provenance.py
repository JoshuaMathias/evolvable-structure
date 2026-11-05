"""Say which commit the measured code is at, and whether it has uncommitted changes, in this repository and in the others it names."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import ownership_index, staleness
from esoi.structure.intent_registry.config import Config


def git(config: Config, *args: str) -> str:
    return git_at(config.root, *args)


def git_at(folder: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=folder, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def is_external(config: Config, entry: str) -> bool:
    """Whether a ``code_paths`` entry points outside this repository (``../sibling/pkg``): it is diffed in its own
    repository's git."""
    return not (config.root / entry).resolve().is_relative_to(config.root)


def own_code_paths(config: Config) -> List[str]:
    return [p for p in config.code_paths if not is_external(config, p)]


def external_code_paths(config: Config) -> List[Tuple[str, Path, str]]:
    """``(entry, repository folder, path inside it)`` for each external ``code_paths`` entry that exists and sits in a
    git checkout; one that is not there (a sibling not checked out in CI) is left out, as a commit that cannot be
    looked up is for the repository's own code."""
    found = []
    for entry in config.code_paths:
        if not is_external(config, entry):
            continue
        full = (config.root / entry).resolve()
        folder = full if full.is_dir() else full.parent
        top = git_at(folder, "rev-parse", "--show-toplevel") if folder.is_dir() else ""
        if top:
            found.append((entry, Path(top), str(full.relative_to(Path(top).resolve())) or "."))
    return found


def code_shas(config: Config) -> str:
    """The recorded commit of each external code path, ``entry@sha`` joined by ``;`` (``-dirty`` when that path has
    uncommitted changes): the ``code_shas`` cell of a results row. Blank when the repository has none."""
    parts = []
    for entry, repo, inside in external_code_paths(config):
        sha = git_at(repo, "rev-parse", "--short", "HEAD")
        if sha and git_at(repo, "status", "--porcelain", "--untracked-files=no", "--", inside):
            sha += "-dirty"
        if sha:
            parts.append(f"{entry}@{sha}")
    return ";".join(parts)


def parse_code_shas(cell: str) -> Dict[str, str]:
    return {entry: sha for entry, _, sha in (part.rpartition("@") for part in (cell or "").split(";") if "@" in part)}


def current_sha(config: Config, component: str = "", impl: str = "") -> str:
    """The short commit, suffixed ``-dirty`` when the measured code has uncommitted changes (the results log itself is not the
    code under test). With a component and arm, only uncommitted changes to what that arm measures under the repository's
    staleness rule count (``esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness``)."""
    sha = git(config, "rev-parse", "--short", "HEAD")
    if not sha:
        return sha
    if component and impl and ownership_index.rule_for(config) != "repo_wide":
        return sha + ("-dirty" if staleness.dirty_counts(config, component, impl) else "")
    if git(config, "status", "--porcelain", "--untracked-files=no", "--", *own_code_paths(config),
           config.evaluation_dir, f":(exclude){config.results}", f":(exclude){config.per_case}", f":(exclude){config.runs_log}"):
        sha += "-dirty"
    return sha


def changed_since(config: Config, sha: str) -> Optional[List[str]]:
    """Tracked files of the measured code (and the evaluation folder, except the results log) that differ from the
    working tree since the commit a result was recorded at; ``None`` when that commit is not known here."""
    base = sha.removesuffix("-dirty")
    done = subprocess.run(["git", "diff", "--name-only", base, "--", *own_code_paths(config), config.evaluation_dir,
                           f":(exclude){config.results}", f":(exclude){config.per_case}", f":(exclude){config.runs_log}"], cwd=config.root, capture_output=True, text=True)
    return done.stdout.split() if done.returncode == 0 else None
