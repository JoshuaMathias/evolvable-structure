"""Dimension 6, public surface: what a unit exports against what other units use.

A unit has a declared surface when it holds an ``interface.py`` (its public top-level names) or an ``__init__.py`` (its ``__all__``, or without one
the names it re-exports from its own modules). The first part is the share of those exported names that some module of another unit imports by
name: an exported name nobody uses widens the surface and the cost of every change to it. The second is the share of each used Protocol's members
that another unit mentions: a member no caller uses still has to be written by every arm (the interface segregation principle), so a fat interface
costs here even when its arms implement it. Units with no surface, or no outside consumer, add nothing, so a project with no declared surfaces is not measured.
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
from typing import Dict, Optional, Set

from esoi.structure.intent_registry.parsed_source import nodes_of
from esoi.structure.structure_quality.conformance import decorator_id, is_protocol, protocol_members
from esoi.structure.structure_quality.balance import Budgets, Dimension, combine, mean
from esoi.structure.structure_quality.coupling import cross_edges
from esoi.structure.structure_quality.project import Project


def declared_all(module) -> Optional[Set[str]]:
    """The names a module lists in ``__all__``, or None when it has none."""
    listed = None
    for node in module.tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "__all__" for t in node.targets) and isinstance(node.value, (ast.List, ast.Tuple)):
            listed = {e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return listed


def named_re_exports(project: Project, module) -> Set[str]:
    """The names an ``__init__.py`` imports by name from its own unit's modules: what it re-exports without ``__all__`` (PEP 8: the package's interface)."""
    names: Set[str] = set()
    for base, taken in module.imports:
        origin = project.index.get(base)
        if origin in project.modules and project.modules[origin].unit == module.unit and origin != module.path:
            names |= {n for n in taken if n != "*"}
    return names


def exported(project: Project) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        name = PurePosixPath(module.path).name
        if module.tree is None or name not in ("interface.py", "__init__.py"):
            continue
        listed = declared_all(module)
        if listed is not None:
            out[module.unit] |= listed
        elif name == "__init__.py":
            out[module.unit] |= named_re_exports(project, module)
        else:
            out[module.unit] |= {node.name for node in module.tree.body
                                 if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")}
    return out


def called_ids(project: Project) -> Dict[str, Set[str]]:
    """Per string written as the first argument of a call, the units whose modules write it."""
    out: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        for node in nodes_of(module.tree) if module.tree is not None else ():
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                out[node.args[0].value].add(module.unit)
    return out


def mentions_by_unit(project: Project) -> Dict[str, Set[str]]:
    """Per identifier or attribute name, the units whose code mentions it."""
    mentions: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        for name in module.names:
            mentions[name].add(module.unit)
    return mentions


def served_names(project: Project) -> Dict[str, Set[str]]:
    """Per unit, the names it exports that another unit uses through the front door: by the solution id in a call, or by the Protocol name mentioned
    without an import (a type annotation or ``isinstance``)."""
    ids = called_ids(project)
    mentions = mentions_by_unit(project)
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


def entry_member(node: ast.ClassDef) -> str:
    """The member a ``@solution(..., entry="name")`` decorator names: the one the front door calls when a caller runs the solution by its id."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and getattr(dec.func, "id", getattr(dec.func, "attr", "")) == "solution":
            for keyword in dec.keywords:
                if keyword.arg == "entry" and isinstance(keyword.value, ast.Constant):
                    return str(keyword.value.value)
    return ""


def members_used(project: Project, used: Dict[str, Set[str]]) -> Dict[str, tuple]:
    """Per Protocol that another unit uses: ``(members, members another unit mentions or the front door calls)``."""
    mentions = mentions_by_unit(project)
    out: Dict[str, tuple] = {}
    for module in project.modules.values():
        for node in nodes_of(module.tree) if module.tree is not None else ():
            if isinstance(node, ast.ClassDef) and is_protocol(node) and decorator_id(node, "solution") and node.name in used.get(module.unit, ()):
                members = set(protocol_members(node))
                called = {m for m in members if mentions.get(m, set()) - {module.unit}} | ({entry_member(node)} & members)
                if members:
                    out[f"{module.path}::{node.name}"] = (members, called)
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
    protocols = members_used(project, used)
    member_shares = {k: len(called) / len(members) for k, (members, called) in protocols.items()}
    offenders += [f"{k.split('::')[0]}: Protocol {k.split('::')[1]} declares {len(protocols[k][0])} members, callers use {len(protocols[k][1])} "
                  f"({', '.join(sorted(protocols[k][0] - protocols[k][1])[:5])} unused), so every arm writes members nobody calls"
                  for k, v in sorted(member_shares.items(), key=lambda kv: kv[1]) if v < 1.0]
    parts = {"exported_names_used": mean([round(v, 4) for v in shares.values()]), "protocol_members_used": mean([round(v, 4) for v in member_shares.values()])}
    return Dimension("surface", combine(list(parts.values())), {k: v for k, v in parts.items() if v is not None}, offenders)
