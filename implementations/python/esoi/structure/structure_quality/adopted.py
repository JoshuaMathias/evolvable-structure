"""Interfaces and base classes that live outside the project: in the libraries it adopts from, and in installed packages.

A project that adopts a solution from a library (``[adopts.<library>] repo = ...`` in its ``esoi.toml``) has arms that implement the library's
Protocol, and arms may extend a base class an installed package defines. Reading only the project's own files would call those arms off their
interface, so the Protocols and classes of each adopted library are read as well (the library's files are parsed, never imported), and a base class
named by an import from an installed package is found by locating that package's source without running it.
"""
from __future__ import annotations

import ast
import importlib.machinery
import tomllib
from pathlib import Path
from typing import Dict, List, Optional

from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of
from esoi.structure.structure_quality.project import Project, load

LIBRARIES: Dict[str, Project] = {}


def adopted_projects(project: Project) -> List[Project]:
    """The projects of the libraries named under ``[adopts]`` in the project's ``esoi.toml`` (none when it names none or a path is not a folder)."""
    config = project.root / "esoi.toml"
    if not config.is_file():
        return []
    try:
        adopts = tomllib.loads(config.read_text(encoding="utf-8")).get("adopts", {})
    except (OSError, tomllib.TOMLDecodeError):
        return []
    found = []
    for entry in adopts.values() if isinstance(adopts, dict) else []:
        root = (project.root / str(entry.get("repo", ""))).resolve() if isinstance(entry, dict) and entry.get("repo") else None
        if root is not None and root.is_dir():
            key = str(root)
            if key not in LIBRARIES:
                LIBRARIES[key] = load(root)
            found.append(LIBRARIES[key])
    return found


def installed_source(module: str) -> Optional[Path]:
    """The source file of an installed module, located by its top-level package without importing anything; None when it is not installed or not Python source."""
    top, *rest = module.split(".")
    spec = importlib.machinery.PathFinder.find_spec(top)
    if spec is None:
        return None
    if spec.submodule_search_locations:
        base = Path(next(iter(spec.submodule_search_locations)))
        target = base.joinpath(*rest)
        for candidate in (target.with_suffix(".py"), target / "__init__.py"):
            if candidate.is_file():
                return candidate
        return None
    return Path(spec.origin) if spec.origin and not rest and spec.origin.endswith(".py") else None


def installed_classes(project: Project, wanted: set) -> Dict[str, ast.ClassDef]:
    """Classes in ``wanted`` (base class names the project does not define) that a module of the project imports from an installed package."""
    out: Dict[str, ast.ClassDef] = {}
    for module in project.modules.values():
        for base, names in module.imports:
            if not set(names) & wanted or base in project.index:
                continue
            path = installed_source(base)
            tree = tree_of(path) if path else None
            for node in nodes_of(tree) if tree else ():
                if isinstance(node, ast.ClassDef) and node.name in wanted and node.name not in out:
                    out[node.name] = node
    return out
