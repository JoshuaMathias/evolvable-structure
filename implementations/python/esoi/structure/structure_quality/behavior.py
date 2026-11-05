"""Dimension 7, behavior preserved: a shared contract that runs against every arm of one solution, so a refactor cannot delete behavior production uses.

A solution with two or more arms has a contract when one of two things reads all its arms at once: a test file that names the solution (its id
or its Protocol class) and either names each arm or loops over them, or an evaluation folder whose ``cases.json`` is named by the solution's metric
command and runs every arm on the same cases. The part is the share of multi-arm solutions that have a contract; a solution with one arm has nothing
to hold the same across and is not counted.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from esoi.structure.structure_quality.balance import Budgets, Dimension, share
from esoi.structure.structure_quality.project import Project
from esoi.structure.structure_quality.scope import classes, decorator_id, is_protocol

LOOPS = re.compile(r"parametrize|for\s+\w+\s+in\s+[\w.]*(arms|implementations|impls|variants)|contract", re.I)


def arms_by_solution(project: Project) -> Dict[str, List[str]]:
    found: Dict[str, List[str]] = defaultdict(list)
    for _, node in classes(project):
        sid = decorator_id(node, "implementation")
        if sid:
            found[sid].append(node.name)
    return found


def protocol_names(project: Project) -> Dict[str, str]:
    return {decorator_id(node, "solution"): node.name for _, node in classes(project) if decorator_id(node, "solution") and is_protocol(node)}


def metric_cases(root: Path) -> Dict[str, bool]:
    """Solution ids whose metric command names an evaluation component that has a ``cases.json``."""
    out: Dict[str, bool] = {}
    for path in root.rglob("metrics.csv"):
        if {".git", "node_modules", "build"} & set(path.relative_to(root).parts):
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                names = re.findall(r"esoi run (\w+)", row.get("command", ""))
                if any(next(root.rglob(f"{n}/cases.json"), None) for n in names):
                    for sid in re.split(r"[;,]\s*", row.get("solution_ids", "")):
                        if sid.strip():
                            out[sid.strip()] = True
    return out


def measure(project: Project, budgets: Budgets) -> Dimension:
    arms = {sid: names for sid, names in arms_by_solution(project).items() if len(names) >= 2}
    protocols = protocol_names(project)
    cases = metric_cases(project.root)
    missing = []
    for sid, names in sorted(arms.items()):
        keys = [sid, protocols.get(sid, sid)]
        held = cases.get(sid, False) or any(
            any(k in text for k in keys) and (all(n in text for n in names) or LOOPS.search(text)) for text in project.tests.values())
        if not held:
            missing.append(f"{sid}: {len(names)} arms and no contract test or shared cases that run them all")
    value = share(len(arms) - len(missing), len(arms))
    return Dimension("behavior", value, {"solutions_with_a_contract": value} if value is not None else {}, missing)
