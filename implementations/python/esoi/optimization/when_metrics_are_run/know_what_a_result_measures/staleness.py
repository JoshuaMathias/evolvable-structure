"""What a recorded result measures, so that it goes stale only when that changed.

A row of the results log is pinned to a commit. The rule that says whether the code changed since then is a choice between
alternatives, measured like any other (the ``staleness_precision`` component):

* ``repo_wide``: any file of ``code_paths`` or of the evaluation folder changed. The baseline: safe, and every component's rows
  go stale on every commit.
* ``component_paths``: only the files the arm's solution and implementation own in the ownership map (``components.csv`` path
  globs mapped to solutions, the implementation records' files, the beside-code folder of a solution whose code is alone in it,
  the component's evaluation folder and the fixtures shared by all of them). A file of ``code_paths`` that no component owns
  counts for every arm (never silently fresh). A component with no ownership entry falls back to ``repo_wide``.
* ``import_closure``: a result goes stale only when the arm's OWN code changes. For a Python arm that is its implementation
  module (the wrapper in ``impls/`` or the file its record names) and the helper code it imports, transitively, found by reading
  the source (no execution), that belongs to no implementation of any solution and that no other implementation's closure imports
  (code shared by two or more arms is nobody's own code). Not in it, whatever the arm imports: test files
  and shared fixtures (``tests/``, ``test_*.py``, ``conftest.py``, everything else in the evaluation folder), the scorer and its
  datasets, a package ``__init__``, and any file another implementation owns (another arm of the component, or another
  solution's code: that solution's own recorded selection answers for it). A changed file that is not Python is judged by
  ``component_paths``, except that anything in the evaluation folder that is not the arm's file is not its code. When the arm
  is not Python, or the scan meets a dynamic import it cannot read, it falls back to ``component_paths`` plus the files the
  scan did find, still without tests, fixtures, scorers and datasets (a module that is loaded only by a computed name and that
  another component owns is not seen: see ``docs/how-to/choose-when-a-result-is-stale.md``).

``rule_for`` picks the rule: ``staleness_rule`` in ``esoi.toml``, else the arm the repository's records select for the
solution ``know-what-a-result-measures``, else ``DEFAULT_RULE`` (the arm the staleness precision metric selected). Standard library only; nothing is run or imported from the
measured code."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from esoi.structure.intent_registry.config import Config
from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_scope import judge, scope_for


def measured_paths(config: Config) -> List[str]:
    from esoi.optimization.measurement_harness.code_provenance import own_code_paths
    return [*own_code_paths(config), config.evaluation_dir, f":(exclude){config.results}", f":(exclude){config.per_case}",
            f":(exclude){config.runs_log}"]


def changed_files(config: Config, sha: str, until: str = "") -> Optional[List[str]]:
    """Tracked files of the measured code folders and the evaluation folder that differ from the working tree since ``sha``, a
    rename listed under both names; ``None`` when the commit is not known here."""
    base = sha.removesuffix("-dirty")
    done = subprocess.run(["git", "diff", "--name-only", "--no-renames", base, *([until] if until else []), "--", *measured_paths(config)],
                          cwd=config.root, capture_output=True, text=True)
    return done.stdout.split("\n") and [p for p in done.stdout.split("\n") if p] if done.returncode == 0 else None


def explain(config: Config, component: str, impl: str, sha: str, rule: Optional[str] = None,
            until: str = "") -> Optional[Dict[str, List[str]]]:
    """``{"counts": [...], "ignored": [...], "rule": [rule in force, fallback note]}``, each file as ``path (why)``, for the files
    changed since ``sha``; ``None`` when the commit is unknown."""
    changed = changed_files(config, sha, until)
    if changed is None:
        return None
    scope = scope_for(config, component, impl, rule)
    out: Dict[str, List[str]] = {"counts": [], "ignored": [], "rule": [scope.rule, scope.note]}
    for path in changed:
        counts, why = judge(config, scope, path)
        out["counts" if counts else "ignored"].append(f"{path}, {why}")
    return out


def dirty_counts(config: Config, component: str, impl: str) -> bool:
    """Whether uncommitted tracked changes touch what the arm measures (the ``-dirty`` mark of a recorded row)."""
    done = subprocess.run(["git", "diff", "--name-only", "--no-renames", "HEAD", "--", *measured_paths(config)],
                          cwd=config.root, capture_output=True, text=True)
    paths = [p for p in done.stdout.split("\n") if p]
    if not paths:
        return False
    scope = scope_for(config, component, impl)
    return any(judge(config, scope, path)[0] for path in paths)


def count_stale(config: Config, rule: str) -> Dict[str, str]:
    """``{component/impl: reason}`` for every latest whole-run row that the rule calls stale because measured code changed (a row
    stale for another reason is left out); how a rule would judge the rows now, whatever the repository configured."""
    from esoi.optimization.leaderboard import results_log
    from esoi.optimization.measurement_harness.stale_reasons import stale_reason
    saved = config.staleness_rule
    config.staleness_rule = rule
    try:
        found: Dict[str, str] = {}
        for comp, arms in results_log.latest_results(config.results_path, whole=True).items():
            for impl, row in arms.items():
                if not stale_reason(config, comp, row, False) and (why := stale_reason(config, comp, row, True)):
                    found[f"{comp}/{impl}"] = why
        return found
    finally:
        config.staleness_rule = saved


@solution("know-what-a-result-measures", kind="evaluate", example=".")
def stale_results(project: str) -> Dict[str, str]:
    """The latest whole-run results of the project at ``project`` that no longer describe the code they measure, as ``{component/impl:
    the changed file and the component that owns it}``; empty when every result is current."""


def stale_by(rule: str, project: str) -> Dict[str, str]:
    from esoi.structure.intent_registry import config as config_module
    return count_stale(config_module.load(Path(project)), rule)


@implementation("know-what-a-result-measures", "repo_wide")
def repo_wide(project: str) -> Dict[str, str]:
    """Stale when any measured file of the repository changed since the result's commit."""
    return stale_by("repo_wide", project)


@implementation("know-what-a-result-measures", "component_paths")
def component_paths(project: str) -> Dict[str, str]:
    """Stale when a file the ownership map assigns to the arm's solutions and implementation changed."""
    return stale_by("component_paths", project)


@implementation("know-what-a-result-measures", "import_closure")
def import_closure(project: str) -> Dict[str, str]:
    """Stale when a file the arm's own module imports changed (its own code: never test files, shared fixtures or another arm's code)."""
    return stale_by("import_closure", project)


def explain_cli(config: Config, component: str, say=print, rule: str = "") -> int:
    """``esoi stale --explain COMPONENT [--rule RULE]``: for each recorded arm of the component, the rule in force, the files changed
    since its row's commit that count and who owns them, and the ones that are ignored and who owns those."""
    from esoi.optimization.leaderboard import results_log
    arms = results_log.latest_results(config.results_path, whole=True).get(component)
    if not arms:
        say(f"{component}: no recorded result, so nothing can be stale (a selected arm with no row is advice from esoi check)")
        return 0
    for impl, row in sorted(arms.items()):
        sha = row.get("git_sha", "")
        found = explain(config, component, impl, sha, rule or None) if sha else None
        if found is None:
            say(f"{component}/{impl}: recorded at {sha or 'no commit'}, which is not known here, so no file can be compared")
            continue
        say(f"{component}/{impl}: recorded at {sha}; rule {found['rule'][0]}" + (f" ({found['rule'][1]})" if found["rule"][1] else ""))
        for line in found["counts"]:
            say(f"  counts: {line}")
        for line in found["ignored"]:
            say(f"  ignored: {line}")
        if not found["counts"]:
            say("  nothing it measures changed")
    return 0
