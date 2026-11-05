"""Stage 2: co-change mined from git history, the same coupling the imports show, measured on what actually changed together.

``git log --name-only`` over a bounded window gives the files of each commit. Commits that touch more files than ``BULK`` are sweeps (a rename, a
format) and say nothing, so they are skipped. A pair of files in different units that changed together in at least ``min_cochange_support``
commits, and in at least ``min_cochange_confidence`` of the commits of the less often changed of the two, is a hidden coupling unless an import
joins their units. This measures what esoi's problem R3 (a change missed) predicts instead of guessing it. A project that is not a git repository
or has too few commits is not measured at this stage.
"""
from __future__ import annotations

import subprocess
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.structure_quality.balance import Budgets
from esoi.structure.structure_quality.coupling import cross_edges
from esoi.structure.structure_quality.project import Project

BULK = 40


def commits(root: Path, limit: int) -> List[List[str]]:
    """The Python files of each of the last ``limit`` commits, newest first."""
    try:
        out = subprocess.run(["git", "-C", str(root), "log", f"-{limit}", "--name-only", "--pretty=format:@@@", "--no-renames", "--", "*.py"],
                             capture_output=True, text=True, timeout=120, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    groups: List[List[str]] = []
    for block in out.split("@@@"):
        files = [line.strip() for line in block.splitlines() if line.strip()]
        if files:
            groups.append(files)
    return groups


def mine(project: Project, budgets: Budgets) -> Optional[Dict[str, object]]:
    """``{commits, pairs, hidden, explained_share}``, or None when there is no history to read."""
    history = commits(project.root, budgets.history_commits)
    if len(history) < budgets.min_cochange_support:
        return None
    changed: Counter = Counter()
    together: Counter = Counter()
    for files in history:
        known = sorted({f for f in files if f in project.modules})
        if len(known) > BULK:
            continue
        changed.update(known)
        together.update(combinations(known, 2))
    joined: Set[Tuple[str, str]] = set()
    for a, b, _, _, _ in cross_edges(project):
        joined.add((a, b))
        joined.add((b, a))
    linked: List[Tuple[str, str, int]] = []
    hidden: List[Tuple[str, str, int]] = []
    for (a, b), n in together.items():
        ua, ub = project.modules[a].unit, project.modules[b].unit
        if ua == ub or n < budgets.min_cochange_support or n / min(changed[a], changed[b]) < budgets.min_cochange_confidence:
            continue
        (linked if (ua, ub) in joined else hidden).append((a, b, n))
    pairs = len(linked) + len(hidden)
    hidden.sort(key=lambda t: -t[2])
    return {"commits": len(history), "pairs": pairs, "hidden": hidden[:50], "hidden_count": len(hidden),
            "explained_share": round(len(linked) / pairs, 4) if pairs else None}
