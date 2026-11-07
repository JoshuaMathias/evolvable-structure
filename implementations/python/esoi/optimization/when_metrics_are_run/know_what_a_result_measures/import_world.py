"""The import graph of every implementation of a repository, built once and shared by every arm: its own code, its helpers and the helpers nobody owns alone."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.import_scan import STATS, closure_of, is_test_file
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.ownership_index import Index, normal, signature


def foreign_files(config: Config, index: Index, own: Set[str]) -> Set[str]:
    """Files that belong to another implementation: every file an implementation record names (any solution), and every module in
    an ``impls`` folder of the evaluation folder, except the arm's own."""
    found: Set[str] = set()
    for row in index.implementations:
        path = (row.get("filepath") or "").partition("::")[0].strip()
        if path and not path.startswith("@"):
            found.add(path)
    root = config.root.resolve()
    for path in config.evaluation.glob("*/impls/*.py"):
        found.add(path.resolve().relative_to(root).as_posix())
    return found - own


def evaluation_prefix(config: Config) -> str:
    """The evaluation folder from the repository root, with a trailing slash (computed once per call that needs it)."""
    root = config.root.resolve()
    evaluation = config.evaluation.resolve()
    return (evaluation.relative_to(root).as_posix() if evaluation.is_relative_to(root) else config.evaluation_dir) + "/"


def not_own_code(config: Config, rel: str, foreign: Set[str], own: Set[str], prefix: str = "") -> bool:
    """Whether a file the scan reaches is left out of an arm's closure: a test or fixture, a package ``__init__``, anything else in
    the evaluation folder (scorer, datasets, shared fixtures), or a file another implementation owns."""
    if rel in own:
        return False
    prefix = prefix or evaluation_prefix(config)
    return (is_test_file(rel) or rel.endswith("/__init__.py") or rel == "__init__.py" or rel.startswith(prefix)
            or rel in foreign)


@dataclass
class World:
    """The import graph of every implementation of a repository, built once and shared by every arm and every result row.

    ``closures[f]`` is what implementation file ``f`` imports (transitively, from the source) up to the next implementation, test,
    fixture or ``__init__``: its own code and plain helpers. ``importers[h]`` is the implementation files whose closure holds the helper
    ``h``; a helper that another implementation imports is shared, so it is nobody's own code."""
    stamp: tuple = ()
    implementations: Set[str] = field(default_factory=set)
    closures: Dict[str, Tuple[Set[str], bool]] = field(default_factory=dict)
    importers: Dict[str, Set[str]] = field(default_factory=dict)
    seen: Set[str] = field(default_factory=set)


WORLDS: Dict[str, World] = {}


def all_implementation_files(config: Config, index: Index) -> Set[str]:
    found: Set[str] = set()
    for row in index.implementations:
        path = (row.get("filepath") or "").partition("::")[0].strip()
        if path and not path.startswith("@"):
            found.add(path)
    root = config.root.resolve()
    for path in config.evaluation.glob("*/impls/*.py"):
        found.add(path.resolve().relative_to(root).as_posix())
    return found


def file_stats(config: Config, files) -> tuple:
    """``(path, modification time, size)`` of each of the repository-relative ``files``, in path order; a file that cannot be read counts as ``(path, 0, 0)``."""
    root = config.root.resolve()
    found = []
    for rel in sorted(files):
        try:
            info = (root / rel).stat()
            found.append((rel, info.st_mtime_ns, info.st_size))
        except OSError:
            found.append((rel, 0, 0))
    return tuple(found)


def world_stamp(config: Config, world: World) -> tuple:
    stats = file_stats(config, world.seen)
    folders = []
    for path in sorted(config.evaluation.glob("*/impls")):   # a new or removed arm changes its folder's time
        info = path.stat()
        folders.append((path.name, info.st_mtime_ns))
    return (signature(config), tuple(folders), stats)


def world_of(config: Config, index: Index) -> World:
    """The shared import graph, rebuilt only when the records or a file it read changed."""
    kept = WORLDS.get(str(config.root))
    if kept is not None and kept.stamp == world_stamp(config, kept):
        return kept
    STATS["worlds"] += 1
    root = config.root.resolve()
    prefix = evaluation_prefix(config)
    world = World(implementations=all_implementation_files(config, index))
    for rel in sorted(world.implementations):
        start = root / rel
        if not start.is_file() or start.suffix != ".py":
            continue
        found, whole = closure_of(config, [start], lambda other, mine=rel: not_own_code(config, other, world.implementations, {mine}, prefix))
        world.closures[rel] = (found, whole)
        world.seen |= found
        for helper in found - world.implementations:
            world.importers.setdefault(helper, set()).add(rel)
    world.stamp = world_stamp(config, world)
    WORLDS[str(config.root)] = world
    return world


def recorded_files(index: Index, impl: str, solutions: List[str]) -> List[str]:
    """The files the records name for the implementation (else for the solution's implementations), without references to other records."""
    named = [r for r in index.implementations if r.get("solution_id") in solutions]
    mine = [r for r in named if normal(r.get("implementation_id", "")) == normal(impl)] or named
    files = [(r.get("filepath") or "").partition("::")[0].strip() for r in mine]
    return [f for f in files if f and not f.startswith("@")]


def start_files(config: Config, index: Index, component: str, impl: str, solutions: List[str]) -> Optional[List[Path]]:
    """The arm's own implementation files: the wrapper in ``impls/`` when there is one, and the files its records name (those of the
    implementation of that name, else of the solution's implementations). None when it has neither, or a record names a file that is
    not Python and there is no wrapper."""
    wrapper = config.evaluation / component / "impls" / f"{impl}.py"
    files = recorded_files(index, impl, solutions)
    if wrapper.is_file():
        return [wrapper] + [config.root / f for f in files if f.endswith(".py")]
    if not files or any(not f.endswith(".py") for f in files):
        return None
    return [config.root / f for f in files]
