"""Dimension 6, public surface: what a unit exports against what other units use.

A unit has a declared surface when it holds an ``interface.py`` (its public top-level names) or an ``__init__.py`` with ``__all__``. The part is
the share of those exported names that some module of another unit imports by name: an exported name nobody uses widens the surface and
the cost of every change to it. Units with no surface, or no outside consumer, add nothing, so a project with no declared surfaces is not measured.
Reaching into a path inside a library is counted under coupling, not here, so one mistake is not charged twice.

A name is used when another unit imports it by name, and also when it is used through the library's front door: a Protocol declared with
``@solution("id", ...)`` that another unit reaches by writing the id as the first argument of a call (``run("id")``, ``resolve("id")``), or whose
Protocol name another unit mentions in a type annotation or ``isinstance``, is a typed handle and intended, so an interface module is not
punished for exporting what the entry point serves.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Dict, Set

from esoi.structure.intent_registry.parsed_source import nodes_of
from esoi.structure.structure_quality.conformance import decorator_id
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


def called_ids(project: Project) -> Dict[str, Set[str]]:
    """Per string written as the first argument of a call, the units whose modules write it."""
    out: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        for node in nodes_of(module.tree) if module.tree is not None else ():
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                out[node.args[0].value].add(module.unit)
    return out


def served_names(project: Project) -> Dict[str, Set[str]]:
    """Per unit, the names it exports that another unit uses through the front door: by the solution id in a call, or by the Protocol name mentioned
    without an import (a type annotation or ``isinstance``)."""
    ids = called_ids(project)
    mentions: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        for name in module.names:
            mentions[name].add(module.unit)
    out: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        if module.tree is None or PurePosixPath(module.path).name != "interface.py":
            continue
        for node in module.tree.body:
            if isinstance(node, ast.ClassDef):
                sid = decorator_id(node, "solution")
                if sid and (ids.get(sid, set()) - {module.unit} or mentions.get(node.name, set()) - {module.unit}):
                    out[module.unit].add(node.name)
    return out


def measure(project: Project, budgets: Budgets) -> Dimension:
    surface = exported(project)
    used: Dict[str, Set[str]] = defaultdict(set)
    for from_unit, to_unit, _, _, names in cross_edges(project):
        used[to_unit] |= set(names)
    for unit, names in served_names(project).items():
        used[unit] |= names
    scored = {u: names for u, names in surface.items() if names and used.get(u)}
    shares = {u: len(names & used[u]) / len(names) for u, names in scored.items()}
    offenders = [f"{u}: exports {len(scored[u])} names, other units use {len(scored[u] & used[u])} ({', '.join(sorted(scored[u] - used[u])[:5])} unused)"
                 for u, v in sorted(shares.items(), key=lambda kv: kv[1]) if v < 1.0]
    value = mean([round(v, 4) for v in shares.values()])
    return Dimension("surface", value, {"exported_names_used": value} if value is not None else {}, offenders)
