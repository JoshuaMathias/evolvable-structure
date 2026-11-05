"""Dimension 6, public surface: what a unit exports against what other units use.

A unit has a declared surface when it holds an ``interface.py`` (its public top-level names) or an ``__init__.py`` with ``__all__``. The part is
the share of those exported names that some module of another unit imports by name: an exported name nobody uses widens the surface and
the cost of every change to it. Units with no surface, or no outside consumer, add nothing, so a project with no declared surfaces is not measured.
Reaching into a path inside a library is counted under coupling, not here, so one mistake is not charged twice.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Dict, Set

from esoi.structure.structure_quality.balance import Budgets, Dimension, mean, share
from esoi.structure.structure_quality.coupling import cross_edges
from esoi.structure.structure_quality.project import Project


def exported(project: Project) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        name = PurePosixPath(module.path).name
        if module.tree is None or name not in ("interface.py", "__init__.py"):
            continue
        listed = None
        for node in module.tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "__all__" for t in node.targets) and isinstance(node.value, (ast.List, ast.Tuple)):
                listed = {e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        if listed is not None:
            out[module.unit] |= listed
        elif name == "interface.py":
            for node in module.tree.body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                    out[module.unit].add(node.name)
    return out


def measure(project: Project, budgets: Budgets) -> Dimension:
    surface = exported(project)
    used: Dict[str, Set[str]] = defaultdict(set)
    for from_unit, to_unit, _, _, names in cross_edges(project):
        used[to_unit] |= set(names)
    scored = {u: names for u, names in surface.items() if names and used.get(u)}
    shares = {u: len(names & used[u]) / len(names) for u, names in scored.items()}
    offenders = [f"{u}: exports {len(scored[u])} names, other units use {len(scored[u] & used[u])} ({', '.join(sorted(scored[u] - used[u])[:5])} unused)"
                 for u, v in sorted(shares.items(), key=lambda kv: kv[1]) if v < 1.0]
    value = mean([round(v, 4) for v in shares.values()])
    return Dimension("surface", value, {"exported_names_used": value} if value is not None else {}, offenders)
