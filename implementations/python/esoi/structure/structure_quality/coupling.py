"""Dimension 3, coupling: solutions connect through declared entry points, in one direction, without cycles.

Parts: the share of cross-unit imports that land on a unit's declared entry (its ``interface.py``, its ``__init__.py``, a file an
``implementations.csv`` names or one that declares a ``@solution`` or ``@implementation``) or on the project's shared kernel with names two or more
units take (``foundation.py``: configuration, error types and registries are imported by many units by design, and the history shows such imports
ripple about as rarely as imports through entries); the share of units outside an import cycle (an import of a kernel is left out of the cycle graph,
since a kernel's own imports reach only other kernels, so no file-level cycle can pass through it); the share of
units that never name a consumer the project declares (a library never names or imports its consumers); and, at stage 2, the share of files that
change together across units with an import edge to explain it (see ``cochange``). Co-change is the history's evidence of the same thing the imports show.

A project's front door (``api.py``, the top package's ``__init__.py``) exists to expose the parts: what it imports is not a cross-solution call and is
left out of the cycle graph. A name another unit takes from a front door counts as an entry only when it resolves, through the re-exports, to a declared
entry; otherwise it is a reach-in on the module that defines it, so moving imports behind a re-export hides nothing. A unit's own ``__init__.py`` that
names a re-export declares it (PEP 8 counts a package's ``__init__`` as its public interface); a name it only passes on through ``import *`` is
followed to the module that defines it.
"""
from __future__ import annotations

import ast
import csv
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.structure_quality import foundation
from esoi.structure.structure_quality.balance import Budgets, Dimension, combine, share
from esoi.structure.structure_quality.project import Project

ENTRY_NAMES = {"interface.py", "__init__.py"}
FRONT_DOOR_NAMES = {"api.py", "__main__.py"}
DECLARING = {"solution", "implementation"}
RE_EXPORT_DEPTH = 6


def declares_entry(tree: object) -> bool:
    """Whether a module decorates a function or class with ``solution`` or ``implementation``: the declaration of an entry in code."""
    for node in ast.walk(tree) if tree is not None else ():
        for decorator in getattr(node, "decorator_list", ()):
            call = decorator.func if isinstance(decorator, ast.Call) else decorator
            if (call.id if isinstance(call, ast.Name) else getattr(call, "attr", "")) in DECLARING:
                return True
    return False


def declared_entries(project: Project) -> Set[str]:
    """The files that name a unit's declared way in: those implementations.csv records name as the code of an arm, and those that declare one in code."""
    found: Set[str] = {path for path, module in project.modules.items() if declares_entry(module.tree)}
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


def is_front_door(project: Project, path: str) -> bool:
    """A project's front door: an ``api.py`` (its public API), a ``__main__.py`` (its command line), or the ``__init__.py`` of a top package (one whose parent folder is not itself a package)."""
    pure = PurePosixPath(path)
    if pure.name in FRONT_DOOR_NAMES:
        return True
    # a solution folder's own __init__.py is that unit's entry even when no package __init__.py sits above it
    return pure.name == "__init__.py" and str(pure.parent.parent / "__init__.py") not in project.modules and str(pure.parent) not in project.markers


def is_entry(project: Project, path: str, entries: Set[str]) -> bool:
    return PurePosixPath(path).name in ENTRY_NAMES or path in entries or is_front_door(project, path)


def through_front_door(project: Project, door: str, names: Tuple[str, ...], depth: int = RE_EXPORT_DEPTH) -> List[str]:
    """The files the names taken from a front door come from: each name followed through the door's own imports, else the door itself (it defines the name)."""
    if not names or depth == 0:
        return [door]
    found: List[str] = []
    for name in names:
        origin = [door]
        for base, taken in project.modules[door].imports:
            if name in taken:
                hits = targets(project, base, (name,))
                origin = []
                for hit in hits:
                    origin += through_front_door(project, hit, (name,), depth - 1) if is_front_door(project, hit) and hit != door else [hit]
                break
        found += origin if origin and origin != [door] else through_star(project, door, name)
    return found


def top_level_names(module) -> Set[str]:
    """The names a module defines or imports by name at its top level (what ``from it import name`` finds without a star)."""
    found: Set[str] = set()
    for node in getattr(module.tree, "body", ()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            found |= {t.id for t in (node.targets if isinstance(node, ast.Assign) else [node.target]) if isinstance(t, ast.Name)}
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            found |= {(alias.asname or alias.name).split(".")[0] for alias in node.names if alias.name != "*"}
    return found


def through_star(project: Project, package: str, name: str) -> List[str]:
    """Where a name taken from a unit's own ``__init__.py`` comes from: the package itself when it names the name, else the module of an ``import *``
    in it that defines the name (the star passes the module's inside on without declaring any of it)."""
    module = project.modules[package]
    if name in top_level_names(module):
        return [package]
    for base, taken in module.imports:
        if "*" in taken:
            for hit in targets(project, base, ()):
                if hit in project.modules and name in top_level_names(project.modules[hit]):
                    return [hit]
    return [package]


def landings(project: Project, target: str, names: Tuple[str, ...]) -> List[Tuple[str, Tuple[str, ...]]]:
    """``(file, names)`` for an import of ``target``: a front door and a unit's own ``__init__.py`` are followed name by name, any other file is itself."""
    if names and is_front_door(project, target):
        return [(final, (name,)) for name in names for final in through_front_door(project, target, (name,))]
    if names and PurePosixPath(target).name == "__init__.py":
        return [(final, (name,)) for name in names for final in through_star(project, target, name)]
    return [(target, names)]


def entry_edges(project: Project) -> List[Tuple[str, str, str, str, Tuple[str, ...]]]:
    """``cross_edges`` as coupling reads them: a front door is not a source, and a name taken from a front door or passed on by an ``import *`` lands on
    the file that defines it."""
    edges = []
    for module in project.modules.values():
        if is_front_door(project, module.path):
            continue
        for base, names in module.imports:
            for target in targets(project, base, names):
                for final, taken in landings(project, target, names):
                    other = project.modules.get(final)
                    if other is not None and other.unit != module.unit:
                        edges.append((module.unit, other.unit, module.path, final, taken))
    return edges


def classified(project: Project, budgets: Budgets) -> Tuple[List[Tuple[Tuple[str, str, str, str, Tuple[str, ...]], str]], Set[str], Set[str]]:
    """Each entry edge with its verdict (``entry``, ``kernel``, ``kernel_one_unit``, ``reach_in``), the declared entries and the kernel modules."""
    edges = entry_edges(project)
    entries = declared_entries(project)
    entry = lambda path: is_entry(project, path, entries)
    kernel = foundation.kernels(project, edges, entry, budgets, targets)
    takers = foundation.shared_names(edges)
    out = []
    for edge in edges:
        if entry(edge[3]):
            out.append((edge, "entry"))
        elif edge[3] in kernel:
            out.append((edge, "kernel_one_unit" if foundation.single_unit_names(edge, takers) else "kernel"))
        else:
            out.append((edge, "reach_in"))
    return out, entries, kernel


def entry_point_of(project: Project, unit: str, entries: Set[str]) -> str:
    """The unit's declared way in, named for an offender: its ``interface.py``, else its ``__init__.py``, else a declared file inside it."""
    for name in ("interface.py", "__init__.py"):
        if f"{unit}/{name}" in project.modules:
            return f"{unit}/{name}"
    inside = sorted(p for p in entries if p in project.modules and project.modules[p].unit == unit)
    return inside[0] if inside else "none declared (add an interface.py)"


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


def offending_imports(project: Project, verdicts, entries: Set[str]) -> List[str]:
    """One line per file pair that reaches into another unit, then one per file that takes a name from the shared kernel that only its unit uses."""
    reach_in = sorted({(e[2], e[3]) for e, verdict in verdicts if verdict == "reach_in"})
    one_unit: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    for e, verdict in verdicts:
        if verdict == "kernel_one_unit":
            one_unit[(e[2], e[3])] |= set(e[4])
    lines = [f"{a} imports {b} inside another unit; its entry point is {entry_point_of(project, project.modules[b].unit, entries)}" for a, b in reach_in[:200]]
    return lines + [f"{a} takes {', '.join(sorted(n))} from the shared kernel module {b}, and no other unit uses it: move it into the unit that does"
                    for (a, b), n in sorted(one_unit.items())[:100]]


def unit_cycles(units: Set[str], edges, kernel: Set[str]) -> List[List[str]]:
    """Import cycles between units, with imports of the shared kernel left out (a kernel imports only kernels, so no file-level cycle passes through it)."""
    graph: Dict[str, Set[str]] = {u: set() for u in units}
    for e in edges:
        if e[3] not in kernel:
            graph[e[0]].add(e[1])
    return components(graph)


def consumer_mentions(project: Project, units: Set[str], consumers: Tuple[str, ...]) -> Dict[str, List[str]]:
    """Per unit that names a consumer the project declares, the lines that do."""
    found = {unit: names_consumer(project, unit, consumers) for unit in sorted(units)} if consumers else {}
    return {unit: lines for unit, lines in found.items() if lines}


def kernel_note(kernel: Set[str], edges, budgets: Budgets) -> str:
    """The shared kernel named for the reader, the most imported modules first, so what was counted as clean is visible."""
    if not kernel:
        return ""
    landed: Dict[str, int] = defaultdict(int)
    for e in edges:
        landed[e[3]] += 1
    shared = sorted(kernel, key=lambda path: (-landed[path], path))
    return (f"shared kernel: {len(kernel)} modules imported by {budgets.min_kernel_importers} or more units that depend on no solution "
            f"({', '.join(PurePosixPath(p).name for p in shared[:5])}{', ...' if len(shared) > 5 else ''})")


def measure(project: Project, budgets: Budgets, cochange: Optional[Dict[str, object]] = None) -> Dimension:
    verdicts, entries, kernel = classified(project, budgets)
    edges = [e for e, _ in verdicts]
    through = [e for e, verdict in verdicts if verdict in ("entry", "kernel")]
    units = {m.unit for m in project.modules.values()}
    cycles = unit_cycles(units, edges, kernel)
    cyclic = {u for group in cycles for u in group}
    named = consumer_mentions(project, units, budgets.consumers)
    parts = {"cross_calls_through_entries_or_kernel": share(len(through), len(edges)), "units_outside_cycles": share(len(units) - len(cyclic), len(units)),
             "units_not_naming_consumers": share(len(units) - len(named), len(units)) if budgets.consumers else None}
    offenders = offending_imports(project, verdicts, entries)
    offenders += [f"cycle between units: {', '.join(g)}" for g in cycles]
    offenders += [f"a library names its consumer: {line}" for lines in named.values() for line in lines]
    note = kernel_note(kernel, edges, budgets)
    if cochange is not None:
        parts["changes_explained_by_imports"] = cochange.get("explained_share")
        offenders += [f"changes together without an import: {a} and {b} ({n} commits)" for a, b, n in cochange.get("hidden", [])]
        note = "; ".join(filter(None, [note, f"stage 2: {cochange.get('commits', 0)} commits read"]))
    return Dimension("coupling", combine(list(parts.values())), {k: v for k, v in parts.items() if v is not None}, offenders, note)
