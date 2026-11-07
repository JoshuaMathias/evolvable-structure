"""Dimension 7, behavior preserved: a shared contract that runs against every arm of one solution, so a refactor cannot delete behavior production uses.

A solution with two or more arms has a contract when one of two things reads all its arms at once: a test file that names the solution (its id
or its Protocol class) and either names each arm or loops over them, or an evaluation folder whose ``cases.json`` is named by the solution's metric
command and runs every arm on the same cases. The part is the share of multi-arm solutions that have a contract; a solution with one arm has nothing
to hold the same across and is not counted.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Dict, List

from esoi.structure.structure_quality.balance import Budgets, Dimension, share
from esoi.structure.structure_quality.project import Project
from esoi.structure.structure_quality.conformance import decorator_id, is_protocol
from esoi.structure.structure_quality.scope import classes

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


def metric_cases(project: Project) -> Dict[str, bool]:
    """Solution ids whose metric command names an evaluation component that has a ``cases.json``."""
    out: Dict[str, bool] = {}
    case_folders = {PurePosixPath(p).parent.name for p in project.named["cases.json"]}
    for row in project.rows("metrics.csv"):
        names = re.findall(r"esoi run (\w+)", row.get("command", ""))
        if any(n in case_folders for n in names):
            for sid in re.split(r"[;,]\s*", row.get("solution_ids", "")):
                if sid.strip():
                    out[sid.strip()] = True
    return out


def contract_test_held(project: Project, keys: List[str], names: List[str]) -> bool:
    """Whether a test names the solution and either runs all its arms or loops over them."""
    return any(any(k in text for k in keys) and (all(n in text for n in names) or LOOPS.search(text)) for text in project.tests.values())


def measure(project: Project, budgets: Budgets) -> Dimension:
    arms = {sid: names for sid, names in arms_by_solution(project).items() if len(names) >= 2}
    protocols = protocol_names(project)
    cases = metric_cases(project)
    missing = []
    for sid, names in sorted(arms.items()):
        if not (cases.get(sid, False) or contract_test_held(project, [sid, protocols.get(sid, sid)], names)):
            missing.append(f"{sid}: {len(names)} arms and no contract test or shared cases that run them all")
    value = share(len(arms) - len(missing), len(arms))
    return Dimension("behavior", value, {"solutions_with_a_contract": value} if value is not None else {}, missing)
