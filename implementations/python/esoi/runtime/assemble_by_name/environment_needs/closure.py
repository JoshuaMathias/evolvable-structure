"""Walk the imports of an arm's package to find every module whose declarations the arm brings in, with the reason each is in."""

from __future__ import annotations

import ast
import collections
import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from esoi.structure.intent_registry.import_base import import_base
from esoi.runtime.assemble_by_name.environment_needs.source_location import source_path


def imported_names(tree: ast.AST, module: ModuleType, path: Path, notes: List[str]) -> List[str]:
    """The dotted module names ``tree`` imports, sorted (a deterministic walk). Relative imports are resolved against
    ``module``; ``importlib.import_module(x)`` and ``__import__(x)`` with a computed argument are noted as not followed."""
    package = module.__name__ if path.name == "__init__.py" else module.__name__.rpartition(".")[0]
    names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = import_base(package.split("."), node.level, node.module)
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Call):
            callee = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if callee in ("import_module", "__import__") and node.args:
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    names.add(argument.value)
                else:
                    notes.append(f"{module.__name__} line {node.lineno}: dynamic import not followed; declare what it needs with REQUIRES")
    return sorted(name for name in names if name)


def walk_imports(start: ModuleType, notes: Optional[List[str]] = None) -> List[ModuleType]:
    """``start`` and every module of the same top-level package it imports, recursively and in a deterministic order (an ``ast``
    walk of the source, like a dependency lister: an import inside a function counts). An import cycle terminates and is noted.
    A module that cannot be read, parsed or imported is noted as unknown with the reason, never raised."""
    notes = notes if notes is not None else []
    top = start.__name__.split(".")[0]
    seen: Dict[str, ModuleType] = {start.__name__: start}
    edges: Dict[str, List[str]] = {}
    queue = collections.deque([start])
    while queue:
        module = queue.popleft()
        path = source_path(module)
        if path is None or path.suffix != ".py":
            if module is start and path is not None:
                notes.append(f"{module.__name__}: not Python source, imports not followed")
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError) as error:
            notes.append(f"{module.__name__}: unknown, cannot parse {path.name} ({type(error).__name__}: {error})")
            continue
        edges[module.__name__] = []
        for name in imported_names(tree, module, path, notes):
            if name.split(".")[0] != top:
                continue
            if name in seen:
                edges[module.__name__].append(name)
                continue
            try:
                if importlib.util.find_spec(name) is None:
                    continue
            except (ImportError, ValueError, AttributeError):
                continue   # not a module (for example a name imported from a module): nothing to follow
            try:
                found = importlib.import_module(name)
            except Exception as error:   # reported, never raised: the arm's own load says whether it is fatal
                notes.append(f"{name}: unknown, cannot import ({type(error).__name__}: {error})")
                continue
            seen[name] = found
            edges[module.__name__].append(name)
            queue.append(found)
    cycle = import_cycle(edges)
    if cycle:
        notes.append("import cycle (followed once): " + " -> ".join(cycle))
    return list(seen.values())


def import_cycle(edges: Mapping[str, Sequence[str]]) -> List[str]:
    """One import cycle in the graph as a closed path of names, or []."""
    state: Dict[str, int] = {}

    def visit(node: str, path: List[str]) -> List[str]:
        state[node] = 1
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt] if nxt in path else [node, nxt]
            if state.get(nxt) is None:
                found = visit(nxt, path + [nxt])
                if found:
                    return found
        state[node] = 2
        return []

    for start in sorted(edges):
        if state.get(start) is None:
            found = visit(start, [start])
            if found:
                return found
    return []


@dataclass(frozen=True)
class Member:
    """One item of a closure: an arm (``solution:name``), the object, and why it is in (``selected`` or ``needed by ...``)."""
    label: str
    target: Any
    reason: str = "selected"


def members_pairs(members: Iterable[Member], notes: Optional[List[str]] = None) -> List[Tuple[str, Any]]:
    """``(label, object)`` pairs for ``gather``: each arm, then each module of its package that it imports (labelled
    ``solution:name via module``), so a requirement declared on a helper module is included."""
    pairs: List[Tuple[str, Any]] = []
    for member in members:
        pairs.append((member.label, member.target))
        start = sys.modules.get(getattr(member.target, "__module__", "") or "") if not isinstance(member.target, ModuleType) else member.target
        if start is None:
            continue
        for module in walk_imports(start, notes):
            pairs.append((f"{member.label} via {module.__name__}", module))
    return pairs


def explain_closure(members: Iterable[Member]) -> List[str]:
    """One line per closure member with the reason it is in."""
    return [f"{one.label}  ({one.reason})" for one in members]
