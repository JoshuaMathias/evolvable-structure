"""Dimension 1, scope: one job per solution.

Three parts, each a share of items in good order: every arm (a class decorated ``@implementation``) implements every member of the Protocol its
solution declares (scored by the share of members lacking, on a cubic curve) with matching parameters and a body that is more than a stub, under a solution id that exists, and does work of its own instead
of passing each call on to another object unchanged (``conformance.py``; a merge once left a whole family of arms off their interface, and a solution
split finer than its job is a chain of pass-through arms); a unit declares no more groups of Protocols than its budget (several unrelated Protocols in one
folder signal that it holds more than one job; layers that wrap one another count once, ``protocol_groups.py``); and the arms of one solution share one purpose, by the word-overlap measure that rules S48 and S49
read. The records are read for the last part only where an ``implementations.csv`` sits beside the code. The arm checks are one part on purpose:
the dimension is a geometric mean of its parts, so a new part that most projects pass would dilute the others.
"""
from __future__ import annotations

import ast
import csv
from collections import defaultdict
from typing import Dict, List, Optional

from esoi.structure.intent_registry.parsed_source import nodes_of
from esoi.structure.structure_quality.adopted import adopted_projects, installed_classes
from esoi.structure.structure_quality.conformance import (arm_problems, declared_solutions, decorator_id, inherited_members, is_protocol, passes_through,
                                                         protocol_members, protocol_problems)
from esoi.structure.structure_quality.balance import Budgets, Dimension, combine, share
from esoi.structure.structure_quality.overlap import ARMS_SHARE_LITTLE, mean_overlap
from esoi.structure.structure_quality.protocol_groups import collect, group_protocols
from esoi.structure.structure_quality.project import Project, resolve_import


INTERFACE_SEVERITY = 3   # the exponent of the share of arms on their interface; stated and justified in docs/explanation/code-quality-is-structure-quality.md


def classes(project: Project):
    for module in project.modules.values():
        if module.tree is None:
            continue
        for node in nodes_of(module.tree):
            if isinstance(node, ast.ClassDef):
                yield module, node


def arm_rows(project: Project) -> List[tuple]:
    """Each arm with what it lacks of its solution's Protocol: ``(path, class, solution id, problems, members)``, where ``members`` is how many members the
    Protocol it was measured against declares, or 0 when the arm has none to be measured against (see ``conformance.arm_problems``). The Protocols and
    base classes of the libraries the project adopts from and of installed packages count (``adopted.py``), and a Protocol counts the members of the
    Protocols it extends; an arm whose solution id names no solution, or whose solution declares no Protocol, has that as its one problem. An arm that
    does not implement its solution's Protocol but does implement a plain Protocol (one with no ``@solution``) in its own folder is told so: the
    solution's interface was demoted beside it, the way a merge once stripped the declaration from 22 Protocols and left their arms registered."""
    libraries = adopted_projects(project)
    protocols: Dict[str, List[ast.ClassDef]] = {}
    plain: Dict[str, List[ast.ClassDef]] = defaultdict(list)
    arms = []
    index: Dict[str, object] = {}
    adopted_index: Dict[str, object] = {}
    for source in [*libraries, project]:
        for module, node in classes(source):
            index[node.name] = node
            if source is not project:
                adopted_index[node.name] = node
            sid = decorator_id(node, "solution")
            if is_protocol(node):
                if sid:
                    protocols.setdefault(sid, []).append(node)
                elif source is project:
                    plain[module.unit].append(node)
            arm = decorator_id(node, "implementation")
            if arm and source is project:
                arms.append((module, node, arm))
    wanted = {getattr(b, "id", getattr(b, "attr", "")) for _, node, _ in arms for b in node.bases} - set(index)
    index.update(installed_classes(project, wanted))
    known = declared_solutions([project, *libraries], set(protocols))
    rows = []
    for module, node, sid in arms:
        if sid in protocols:
            arm_index = base_index(node, index, adopted_index)
            problems, members = arm_problems(node, [protocol_members(p, arm_index) for p in protocols[sid]], arm_index)
            if problems:
                problems = problems + beside_statements(node, plain[module.unit], index)
        else:
            problems, members = ["its solution declares no Protocol" if sid in known else "its solution id names no solution the project declares"], 0
        rows.append((module.path, node.name, sid, problems, members))
    return rows


def base_index(arm: ast.ClassDef, index: Dict[str, object], adopted_index: Dict[str, object]) -> Dict[str, object]:
    """The class index an arm is read against. An arm that extends a library class of its own name (``class Serper(hub.Serper)``, the way an adopter
    re-declares a library arm under its own solution) takes that base from the library, not from itself."""
    same = any(getattr(b, "id", getattr(b, "attr", "")) == arm.name for b in arm.bases)
    return {**index, arm.name: adopted_index[arm.name]} if same and arm.name in adopted_index else index


def beside_statements(arm: ast.ClassDef, plain: List[ast.ClassDef], index: Dict[str, object]) -> List[str]:
    """For an arm off its solution's interface: the plain Protocols of its folder that it implements in full (they declare at least one member)."""
    methods, attributes = inherited_members(arm, index, {arm.name})
    found = [p.name for p in plain if (m := protocol_members(p, index)) and not protocol_problems(m, methods, attributes)]
    return [f"implements {', '.join(found)} beside it, a plain Protocol without the solution declaration, and not its solution's interface"] if found else []


def arms_on_interface(project: Project):
    """``(path, class, solution id, problems)`` for each arm (``arm_rows`` without the member count)."""
    return [row[:4] for row in arm_rows(project)]


def arm_severity(row: tuple) -> float:
    """How far off its interface one arm is, 0 to 1: the share of its solution's Protocol members it lacks (a stub, a missing member and a method with
    parameters that do not match each count as one lacking member). An arm with no Protocol to be measured against is wholly off."""
    problems, members = row[3], row[4]
    lacking = [p for p in problems if " " not in p or ":" in p]
    return 0.0 if not problems else (1.0 if members <= 0 else min(1.0, len(lacking) / members))


def own_module_names(project: Project, path: str) -> set:
    """The local names a module binds, by any import in it, to a module of its own unit: a call through them is the unit's own work."""
    module = project.modules[path]
    out = set()
    for node in nodes_of(module.tree) if module.tree is not None else ():
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            resolved = resolve_import(node, path)
            bases = [b for b, _ in resolved] if isinstance(node, ast.Import) else [resolved[0][0]] * len(node.names)
            for base, alias in zip(bases, node.names):
                full = base if isinstance(node, ast.Import) else f"{base}.{alias.name}"
                target = project.index.get(full) or project.index.get(base)
                if target in project.modules and project.modules[target].unit == module.unit:
                    out.add((alias.asname or alias.name).split(".")[0])
    return out


def pass_through_arms(project: Project) -> List[tuple]:
    """``(path, class, solution id, members)`` for each arm whose every public method passes its call on unchanged (see ``conformance.passes_through``)."""
    index = {node.name: node for _, node in classes(project)}
    out = []
    own: Dict[str, set] = {}
    for module, node in classes(project):
        sid = decorator_id(node, "implementation")
        if not sid:
            continue
        methods, _ = inherited_members(node, index, {node.name})
        if module.path not in own:
            own[module.path] = own_module_names(project, module.path)
        if methods and all(passes_through(fn, own[module.path]) for fn in methods.values()):
            out.append((module.path, node.name, sid, sorted(methods)))
    return out


def interface_score(conformance: Optional[float]) -> Optional[float]:
    """The score of the mean conformance of the arms (1 for an arm that implements every member of its Protocol, 0 for one that lacks them all, the
    share of members it has in between; see ``arm_severity``): ``conformance ** INTERFACE_SEVERITY``, the same cubic curve as the reuse dimension. A mean
    is linear in the arms and members, so a merge that strips the interface from a third of the arms would cost a third of one part of one dimension;
    cubed it costs 70 percent of the part (0.95 scores 0.86, 0.9 scores 0.73, 0.67 scores 0.30), so the failure the metric exists to catch is not
    outweighed by what a merge improves elsewhere."""
    return None if conformance is None else round(conformance ** INTERFACE_SEVERITY, 4)


def protocols_per_unit(project: Project) -> Dict[str, List[str]]:
    """Per folder, one name for each group of Protocols that are one job (see ``protocol_groups.py``): layered Protocols used by the same arms or
    chained by delegation count once, Protocols that different arms implement count apart."""
    protocols, arms = collect(classes(project))
    return {unit: [members[0] for members in group_protocols(found, arms)] for unit, found in protocols.items()}


def arm_purposes(project: Project) -> Dict[str, List[str]]:
    """Per solution id, the name and description of each of its arms, from every implementations.csv under the project."""
    out: Dict[str, List[str]] = defaultdict(list)
    for relative in project.named["implementations.csv"]:
        with (project.root / relative).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                out[row.get("solution_id", "")].append(" ".join([row.get("name", ""), row.get("description", "")]))
    return out


def arm_line(path: str, name: str, sid: str, problems: List[str]) -> str:
    lacking = [p for p in problems if ":" not in p and " " not in p]
    mismatched = [p for p in problems if ":" in p]
    statements = [p for p in problems if p not in lacking and p not in mismatched]
    parts = ([f"lacks {', '.join(lacking)}"] if lacking else []) + ["has " + m.replace(": ", " (", 1) + ")" for m in mismatched] + statements
    return f"{path}: arm {name} of {sid}: " + "; ".join(parts)


def measure(project: Project, budgets: Budgets) -> Dimension:
    full_rows = arm_rows(project)
    rows = [r[:4] for r in full_rows]
    off = [r for r in rows if r[3]]
    unit_protocols = protocols_per_unit(project)
    split = {u: n for u, n in unit_protocols.items() if len(n) > budgets.protocols_per_unit}
    purposes = {sid: texts for sid, texts in arm_purposes(project).items() if sid and len(texts) >= 3}
    unfocused = {sid: round(mean_overlap(texts), 3) for sid, texts in purposes.items() if mean_overlap(texts) < ARMS_SHARE_LITTLE}
    hollow = pass_through_arms(project)
    severity = {(r[0], r[1]): arm_severity(r) for r in full_rows}
    severity.update({(h[0], h[1]): 1.0 for h in hollow})   # one part, so a new check does not dilute the others in the geometric mean; a pass-through arm lacks all of its own work
    parts = {"arms_on_interface": interface_score(None if not rows else round(1 - sum(severity.values()) / len(rows), 4)),
             "protocols_within_budget": share(len(unit_protocols) - len(split), len(unit_protocols)),
             "arms_share_one_purpose": share(len(purposes) - len(unfocused), len(purposes))}
    offenders = [arm_line(p, c, s, m) for p, c, s, m in off]
    offenders += [f"{p}: arm {c} of {s} passes every call on unchanged ({', '.join(m)}): it adds no work of its own, so the solution may be split finer than its job"
                  for p, c, s, m in hollow]
    offenders += [f"{u}: {len(n)} Protocols ({', '.join(n[:4])}) signal more than one job" for u, n in sorted(split.items(), key=lambda kv: -len(kv[1]))]
    offenders += [f"{s}: its arms share little purpose (mean overlap {v})" for s, v in unfocused.items()]
    return Dimension("scope", combine(list(parts.values())), {k: v for k, v in parts.items() if v is not None}, offenders)
