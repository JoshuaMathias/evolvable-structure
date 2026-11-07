"""Which Protocols of one folder are one job and which are several: layered Protocols are not a split signal.

A folder that declares several Protocols may hold one job in layers (a store wraps a cache that wraps a backend, so each layer has its own Protocol
and the arms of each layer are built on the one below), or several unrelated jobs side by side. Counting every Protocol would charge the layered
folder for being layered. So the Protocols of a folder are grouped, and the budget counts groups. Two Protocols are one group when

- the same arms implement them: they are two faces of one object (the arms of the same solution id, or an arm that extends both), or
- one extends the other: a Protocol that refines another adds members to the same job, or
- they form a delegation chain: an arm of one Protocol's solution takes exactly one Protocol of the folder as a constructor need, which is how a layer
  wraps the layer it delegates to.

An arm that takes several Protocols of the folder as needs is a composition root that holds distinct jobs together, not a layer, so it joins none of
them. Protocols that different arms implement, with no layer wrapping another, stay separate groups: different jobs in one folder. A Protocol no arm
implements has no evidence of being part of anything and is a group of its own. Nothing is imported or run.
"""
from __future__ import annotations

import ast
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.structure_quality.conformance import decorator_id, is_protocol


def annotation_names(annotation: ast.AST) -> Set[str]:
    """The class names an annotation mentions, in subscripts such as ``Optional[Cache]`` and in string annotations."""
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            return annotation_names(ast.parse(annotation.value, mode="eval").body)
        except SyntaxError:
            return set()
    return {n.id for n in ast.walk(annotation) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(annotation) if isinstance(n, ast.Attribute)}


def annotation_needs(arm: ast.ClassDef) -> Set[str]:
    """The names an arm takes as constructor parameters, by annotation: what it is built from."""
    names: Set[str] = set()
    for statement in arm.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and statement.name == "__init__":
            for parameter in [*statement.args.posonlyargs, *statement.args.args, *statement.args.kwonlyargs]:
                if parameter.annotation is not None:
                    names |= annotation_names(parameter.annotation)
    return names


class Groups:
    """A union-find over names."""

    def __init__(self, names: List[str]):
        self.parent = {n: n for n in names}

    def find(self, name: str) -> str:
        while self.parent[name] != name:
            self.parent[name] = self.parent[self.parent[name]]
            name = self.parent[name]
        return name

    def join(self, first: str, second: str) -> None:
        self.parent[self.find(first)] = self.find(second)


def join_by_arms(groups: Groups, names: List[str], protocols, arms) -> Dict[str, Set[str]]:
    """Join the Protocols one arm takes as a need to those its own solution declares; returns the arms that implement each Protocol."""
    implementers: Dict[str, Set[str]] = {n: set() for n in names}
    for _, arm, sid in arms:
        extended = {getattr(b, "id", getattr(b, "attr", "")) for b in arm.bases}
        implemented = [n for n in names if protocols[n][1] == sid]
        for name in names:
            if name in extended or name in implemented:
                implementers[name].add(arm.name)
        taken = [n for n in names if n in annotation_needs(arm)]
        if len(taken) == 1:
            for owner in implemented:
                if owner != taken[0]:
                    groups.join(owner, taken[0])
    return implementers


def group_protocols(protocols: Dict[str, List[Tuple[str, str]]], arms: List[Tuple[str, ast.ClassDef, str]],
                    extends: Optional[Dict[str, Set[str]]] = None) -> List[List[str]]:
    """The groups of Protocol names of one folder. ``protocols`` maps each Protocol name of the folder to its ``(path, solution id)`` and ``arms`` are
    ``(path, class, solution id)`` for every arm of the project (an arm anywhere may build on a Protocol of this folder). ``extends`` maps a Protocol
    name to the base class names it lists: one that extends another Protocol of the folder is in its group."""
    names = sorted(protocols)
    groups = Groups(names)
    for name in names:
        for base in (extends or {}).get(name, ()):
            if base in groups.parent and base != name:
                groups.join(name, base)
    implementers = join_by_arms(groups, names, protocols, arms)
    for position, first in enumerate(names):
        for second in names[position + 1:]:
            if implementers[first] and implementers[first] == implementers[second]:
                groups.join(first, second)
    found: Dict[str, List[str]] = {}
    for name in names:
        found.setdefault(groups.find(name), []).append(name)
    return list(found.values())


def collect(classes_of_project) -> Tuple[Dict[str, Dict[str, Tuple[str, str]]], List[Tuple[str, ast.ClassDef, str]], Dict[str, Set[str]]]:
    """From ``(module, class)`` pairs: the Protocols of each unit (name to ``(path, solution id)``), every arm of the project, and the base class names
    each Protocol lists."""
    protocols: Dict[str, Dict[str, Tuple[str, str]]] = {}
    arms: List[Tuple[str, ast.ClassDef, str]] = []
    extends: Dict[str, Set[str]] = {}
    for module, node in classes_of_project:
        if is_protocol(node):
            protocols.setdefault(module.unit, {})[node.name] = (module.path, decorator_id(node, "solution"))
            extends.setdefault(node.name, set()).update(getattr(b, "id", getattr(b, "attr", "")) for b in node.bases)
        arm = decorator_id(node, "implementation")
        if arm:
            arms.append((module.path, node, arm))
    return protocols, arms, extends
