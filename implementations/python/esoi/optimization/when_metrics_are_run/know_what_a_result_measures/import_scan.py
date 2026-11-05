"""Read the imports of Python files from their source, without running them: the modules a file imports, transitively, and whether the scan saw every import."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of


DYNAMIC_CALLS = {"import_module", "__import__", "run_module", "spec_from_file_location", "load_source"}
STATS = {"worlds": 0}   # the counter the performance guard test reads: import graphs built (files parsed are counted in ``parsed_source``)

NAMES: Dict[tuple, Optional[Tuple[Set[str], bool]]] = {}   # (path, mtime, size, roots) -> what the file imports


def search_roots(config: Config) -> List[Path]:
    roots = [config.root / p for p in config.python_path] + [config.evaluation, config.root]
    return [r.resolve() for r in roots if r.is_dir()]


MODULES: Dict[tuple, List[Path]] = {}


def module_files(roots: List[Path], dotted: str) -> List[Path]:
    """Cached for the run of the process: a module that appears or disappears mid-run is seen by the next process."""
    key = (tuple(map(str, roots)), dotted)
    if key not in MODULES:
        MODULES[key] = find_module_files(roots, dotted)
    return MODULES[key]


def find_module_files(roots: List[Path], dotted: str) -> List[Path]:
    """The files that importing ``dotted`` runs inside the repository: the module and the ``__init__`` of each package above it."""
    parts = dotted.split(".")
    for root in roots:
        target = root.joinpath(*parts)
        if target.with_suffix(".py").is_file():
            main = target.with_suffix(".py")
        elif (target / "__init__.py").is_file():
            main = target / "__init__.py"
        else:
            continue
        found = [root.joinpath(*parts[:i], "__init__.py") for i in range(1, len(parts))]
        return [p for p in found if p.is_file()] + [main]
    return []


def import_names(tree: ast.Module, here: Path, roots: List[Path]) -> Tuple[Set[str], bool]:
    """``(names, complete)``: every module a file imports, as dotted names from a search root, and whether it imports none by a name it
    computes (the names found are returned either way)."""
    names: Set[str] = set()
    complete = True
    base: Optional[List[str]] = None
    for root in roots:
        if root in here.parents:
            base = list(here.parent.relative_to(root).parts)
            break
    for node in nodes_of(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix: List[str] = []
            if node.level:
                if base is None or node.level - 1 > len(base):
                    continue
                prefix = base[:len(base) - (node.level - 1)]
            module = ".".join(prefix + ([node.module] if node.module else [])) if (node.level or node.module) else ""
            if module:
                names.add(module)
                names.update(f"{module}.{alias.name}" for alias in node.names)
            elif node.level:
                names.update(".".join(prefix + [alias.name]) for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
            if called in DYNAMIC_CALLS:
                first = node.args[0] if node.args else None
                if called not in ("spec_from_file_location", "load_source") and isinstance(first, ast.Constant) \
                        and isinstance(first.value, str) and not first.value.startswith("."):
                    names.add(first.value)
                else:
                    complete = False
    return names, complete


TEST_NAMES = re.compile(r"(^test_.*|.*_test|^conftest)\.py$")
TEST_FOLDERS = {"tests", "test", "fixtures", "__pycache__"}


def is_test_file(rel: str) -> bool:
    """A test file or a shared test fixture: a ``tests`` or ``fixtures`` folder, ``test_*.py``, ``*_test.py`` or ``conftest.py``."""
    parts = rel.split("/")
    return bool(TEST_FOLDERS & set(parts[:-1])) or bool(TEST_NAMES.match(parts[-1]))


RELATIVE: Dict[Tuple[Path, Path], Optional[str]] = {}


def relative_in(root: Path, path: Path) -> Optional[str]:
    """The posix path of ``path`` under ``root`` (a folder strictly inside it), or None when it is outside; worked out once per pair."""
    key = (root, path)
    if key not in RELATIVE:
        RELATIVE[key] = path.relative_to(root).as_posix() if root in path.parents else None
    return RELATIVE[key]


def closure_of(config: Config, starts: List[Path], skip=None) -> Tuple[Set[str], bool]:
    """``(files, complete)``: the repository files the start files import, transitively, from their source, and whether the scan was
    complete. It is not when a file cannot be read, is not Python, or imports a module by a computed name; the files found so far
    are still returned, for the rule that falls back."""
    roots = search_roots(config)
    root = config.root.resolve()
    seen: Dict[Path, None] = {}
    queue = [p.resolve() for p in starts]
    complete = True
    while queue:
        here = queue.pop()
        if here in seen or not here.is_file():
            continue
        if here.suffix != ".py":
            complete = False
            continue
        seen[here] = None
        info = here.stat()
        key = (str(here), info.st_mtime_ns, info.st_size, tuple(map(str, roots)))
        if key not in NAMES:
            tree = tree_of(here)
            NAMES[key] = import_names(tree, here, roots) if tree is not None else None
        found = NAMES[key]
        if found is None:
            complete = False
            continue
        names, whole = found
        complete = complete and whole
        for dotted in names:
            for p in module_files(roots, dotted):
                inside = relative_in(root, p)
                if p not in seen and inside is not None and not (skip is not None and skip(inside)):
                    queue.append(p)
    return {relative_in(root, p) or p.relative_to(root).as_posix() for p in seen}, complete
