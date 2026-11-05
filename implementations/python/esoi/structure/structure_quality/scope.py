"""Dimension 1, scope: one job per solution.

Three parts, each a share of items in good order: every arm (a class decorated ``@implementation``) defines the methods of the Protocol its
solution declares (a merge once left a whole family of arms off their interface); a unit declares no more Protocols than its budget (several
unrelated Protocols in one folder signal that it holds more than one job); and the arms of one solution share one purpose, by the word-overlap
measure that rules S48 and S49 read. The records are read for the third part only where an ``implementations.csv`` sits beside the code.
"""
from __future__ import annotations

import ast
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from esoi.structure.structure_quality.balance import Budgets, Dimension, combine, share
from esoi.structure.structure_quality.overlap import ARMS_SHARE_LITTLE, mean_overlap
from esoi.structure.structure_quality.project import Project


def decorator_id(node: ast.ClassDef, name: str) -> str:
    """The solution id a ``@solution("id", ...)`` or ``@implementation("id", ...)`` decorator names, or an empty string."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and getattr(dec.func, "id", getattr(dec.func, "attr", "")) == name and dec.args:
            first = dec.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return first.value
    return ""


def methods(node: ast.ClassDef) -> Set[str]:
    return {n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")}


def is_protocol(node: ast.ClassDef) -> bool:
    return any(getattr(b, "id", getattr(b, "attr", "")) == "Protocol" for b in node.bases)


def classes(project: Project):
    for module in project.modules.values():
        if module.tree is None:
            continue
        for node in ast.walk(module.tree):
            if isinstance(node, ast.ClassDef):
                yield module, node


def arms_on_interface(project: Project):
    """Each arm with the Protocol methods it lacks: ``(path, class, solution id, missing)``; the share of arms that lack none."""
    declared: Dict[str, Set[str]] = {}
    arms = []
    for module, node in classes(project):
        sid = decorator_id(node, "solution")
        if sid and is_protocol(node):
            declared[sid] = methods(node)
        arm = decorator_id(node, "implementation")
        if arm:
            arms.append((module.path, node, arm))
    rows = []
    for path, node, sid in arms:
        have = methods(node)
        missing = sorted(declared[sid] - have) if sid in declared else ["its solution declares no Protocol"]
        rows.append((path, node.name, sid, missing))
    return rows


def protocols_per_unit(project: Project) -> Dict[str, List[str]]:
    found: Dict[str, List[str]] = defaultdict(list)
    for module, node in classes(project):
        if is_protocol(node):
            found[module.unit].append(node.name)
    return found


def arm_purposes(root: Path) -> Dict[str, List[str]]:
    """Per solution id, the name and description of each of its arms, from every implementations.csv under the project."""
    out: Dict[str, List[str]] = defaultdict(list)
    for path in root.rglob("implementations.csv"):
        if any(part in {".git", "node_modules", "build", "__pycache__"} for part in path.relative_to(root).parts):
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                out[row.get("solution_id", "")].append(" ".join([row.get("name", ""), row.get("description", "")]))
    return out


def measure(project: Project, budgets: Budgets) -> Dimension:
    rows = arms_on_interface(project)
    off = [r for r in rows if r[3]]
    unit_protocols = protocols_per_unit(project)
    split = {u: n for u, n in unit_protocols.items() if len(n) > budgets.protocols_per_unit}
    purposes = {sid: texts for sid, texts in arm_purposes(project.root).items() if sid and len(texts) >= 3}
    unfocused = {sid: round(mean_overlap(texts), 3) for sid, texts in purposes.items() if mean_overlap(texts) < ARMS_SHARE_LITTLE}
    parts = {"arms_on_interface": share(len(rows) - len(off), len(rows)), "protocols_within_budget": share(len(unit_protocols) - len(split), len(unit_protocols)),
             "arms_share_one_purpose": share(len(purposes) - len(unfocused), len(purposes))}
    offenders = [f"{p}: arm {c} of {s} lacks {', '.join(m)}" for p, c, s, m in off]
    offenders += [f"{u}: {len(n)} Protocols ({', '.join(n[:4])}) signal more than one job" for u, n in sorted(split.items(), key=lambda kv: -len(kv[1]))]
    offenders += [f"{s}: its arms share little purpose (mean overlap {v})" for s, v in unfocused.items()]
    return Dimension("scope", combine(list(parts.values())), {k: v for k, v in parts.items() if v is not None}, offenders)
