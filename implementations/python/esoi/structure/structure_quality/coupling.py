"""Dimension 3, coupling: solutions connect through declared entry points, in one direction, without cycles.

Parts: the share of cross-unit imports that land on a unit's declared entry point (its ``interface.py``, its ``__init__.py`` or a file an
``implementations.csv`` names); the share of units outside an import cycle; the share of units that never name a consumer the project declares
(a library never names or imports its consumers); and, at stage 2, the share of files that change together across units with an import
edge to explain it (see ``cochange``). Co-change is the history's evidence of the same thing the imports show.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.structure_quality.balance import Budgets, Dimension, combine, share
from esoi.structure.structure_quality.project import Project

ENTRY_NAMES = {"interface.py", "__init__.py"}


def declared_entries(project: Project) -> Set[str]:
    """The files that implementations.csv records name as the code of an arm: a unit's declared way in."""
    found: Set[str] = set()
    for relative in project.named["implementations.csv"]:
        with (project.root / relative).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                target = (row.get("filepath") or "").partition("::")[0].strip()
                if target:
                    found.add(target)
    return found


def targets(project: Project, base: str, names: Tuple[str, ...]) -> List[str]:
    """The project files an import names: each imported submodule, else the module itself."""
    hits = [project.index[f"{base}.{n}"] for n in names if f"{base}.{n}" in project.index]
    if hits:
        return hits
    return [project.index[base]] if base in project.index else []


def cross_edges(project: Project) -> List[Tuple[str, str, str, str, Tuple[str, ...]]]:
    """``(from unit, to unit, from file, to file, names)`` for every import that crosses from one unit into another."""
    edges = []
    for module in project.modules.values():
        for base, names in module.imports:
            for target in targets(project, base, names):
                other = project.modules.get(target)
                if other is not None and other.unit != module.unit:
                    edges.append((module.unit, other.unit, module.path, target, names))
    return edges


def components(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Strongly connected components of size above one (Tarjan, iterative)."""
    index: Dict[str, int] = {}
    low: Dict[str, int] = {}
    stack: List[str] = []
    on: Set[str] = set()
    out: List[List[str]] = []
    counter = 0
    for start in list(graph):
        if start in index:
            continue
        work = [(start, iter(sorted(graph.get(start, ()))))]
        index[start] = low[start] = counter
        counter += 1
        stack.append(start)
        on.add(start)
        while work:
            node, children = work[-1]
            advanced = False
            for child in children:
                if child not in index:
                    index[child] = low[child] = counter
                    counter += 1
                    stack.append(child)
                    on.add(child)
                    work.append((child, iter(sorted(graph.get(child, ())))))
                    advanced = True
                    break
                if child in on:
                    low[node] = min(low[node], index[child])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                group = []
                while True:
                    member = stack.pop()
                    on.discard(member)
                    group.append(member)
                    if member == node:
                        break
                if len(group) > 1:
                    out.append(sorted(group))
    return out


def names_consumer(project: Project, unit: str, consumers: Tuple[str, ...]) -> List[str]:
    hits = []
    for module in project.modules.values():
        if module.unit != unit:
            continue
        for name in consumers:
            if name in module.names or any(name in part.split(".") for base, _ in module.imports for part in [base]):
                hits.append(f"{module.path} names {name}")
    return hits


def measure(project: Project, budgets: Budgets, cochange: Optional[Dict[str, object]] = None) -> Dimension:
    edges = cross_edges(project)
    entries = declared_entries(project)
    through = [e for e in edges if PurePosixPath(e[3]).name in ENTRY_NAMES or e[3] in entries]
    reach_in: Dict[Tuple[str, str], int] = defaultdict(int)
    allowed = set(through)
    for e in edges:
        if e not in allowed:
            reach_in[(e[2], e[3])] += 1
    units = {m.unit for m in project.modules.values()}
    graph: Dict[str, Set[str]] = {u: set() for u in units}
    for e in edges:
        graph[e[0]].add(e[1])
    cycles = components(graph)
    cyclic = {u for group in cycles for u in group}
    named: List[str] = []
    named_units: Set[str] = set()
    if budgets.consumers:
        for unit in sorted(units):
            found = names_consumer(project, unit, budgets.consumers)
            if found:
                named_units.add(unit)
                named += found
    parts = {"cross_calls_through_entry_points": share(len(through), len(edges)), "units_outside_cycles": share(len(units) - len(cyclic), len(units)),
             "units_not_naming_consumers": share(len(units) - len(named_units), len(units)) if budgets.consumers else None}
    offenders = [f"{a} imports {b}, inside another unit and not its entry point" for (a, b), _ in sorted(reach_in.items())[:200]]
    offenders += [f"cycle between units: {', '.join(g)}" for g in cycles]
    offenders += [f"a library names its consumer: {line}" for line in named]
    note = ""
    if cochange is not None:
        parts["changes_explained_by_imports"] = cochange.get("explained_share")
        offenders += [f"changes together without an import: {a} and {b} ({n} commits)" for a, b, n in cochange.get("hidden", [])]
        note = f"stage 2: {cochange.get('commits', 0)} commits read"
    return Dimension("coupling", combine(list(parts.values())), {k: v for k, v in parts.items() if v is not None}, offenders, note)
