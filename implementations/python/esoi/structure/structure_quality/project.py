"""What the checks of Structure Quality read: a project's Python modules, parsed once, each assigned to the unit (solution folder) it belongs to.

A unit is the folder of the nearest ``interface.py`` or ``solutions.csv`` above a file; a file with neither above it belongs to the unit named by
its first two folders. Test files are kept apart: they are read only for the shared contract tests. Nothing is imported or run; the
standard library only.
"""
from __future__ import annotations

import ast
import subprocess
import tokenize
import hashlib
import os
from dataclasses import dataclass, field, replace
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry.import_base import import_base
from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of
from esoi.structure.structure_quality.complexity import cyclomatic

SKIPPED = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist", "site-packages", ".esoi_cache", ".tox", ".mypy_cache"}
MARKERS = ("interface.py", "solutions.csv")
TESTS = {"tests", "test"}


@dataclass
class Module:
    path: str
    unit: str
    lines: int
    functions: List[Tuple[str, int, int, int, bool]] = field(default_factory=list)   # name, first line, length in lines, cyclomatic complexity, outermost (not inside another function)
    imports: List[Tuple[str, Tuple[str, ...]]] = field(default_factory=list)   # dotted module, names taken from it
    names: Set[str] = field(default_factory=set)   # every identifier and attribute the code mentions
    tokens: List[str] = field(default_factory=list)   # normalized tokens outside imports and docstrings
    tree: ast.AST = None


@dataclass
class Project:
    root: Path
    modules: Dict[str, Module]
    tests: Dict[str, str]
    markers: Set[str]   # folders holding an interface.py or solutions.csv
    index: Dict[str, str]   # dotted name (and every suffix of it) to the one file it names
    named: Dict[str, List[str]] = field(default_factory=dict)   # record file name to its paths under the root, from the one walk that loaded the project

    def folder_files(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for path in self.modules:
            folder = str(PurePosixPath(path).parent)
            counts[folder] = counts.get(folder, 0) + 1
        return counts


def listed(root: Path) -> List[str]:
    """The Python files of the project: those git lists when it is a repository, else every file outside the skipped folders."""
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "*.py"], capture_output=True, text=True, timeout=60, check=True).stdout
        found = [line for line in out.splitlines() if line]
        if found:
            return [f for f in found if not SKIPPED & set(PurePosixPath(f).parts) and (root / f).is_file()]
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*.py") if not SKIPPED & set(p.relative_to(root).parts))


def is_test(path: str) -> bool:
    parts = PurePosixPath(path).parts
    name = parts[-1]
    return bool(TESTS & set(parts[:-1])) or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def unit_of(path: str, markers: Set[str]) -> str:
    folder = PurePosixPath(path).parent
    for candidate in [folder, *folder.parents]:
        if str(candidate) != "." and str(candidate) in markers:
            return str(candidate)
    parts = PurePosixPath(path).parts
    return "/".join(parts[:2]) if len(parts) > 2 else (parts[0] if len(parts) == 2 else ".")


def dotted(path: str) -> str:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def build_index(paths: List[str]) -> Dict[str, str]:
    seen: Dict[str, Set[str]] = {}
    for path in paths:
        name = dotted(path).split(".")
        for start in range(len(name)):
            seen.setdefault(".".join(name[start:]), set()).add(path)
    return {key: next(iter(files)) for key, files in seen.items() if len(files) == 1 and key}


def resolve_import(node: ast.AST, path: str) -> List[Tuple[str, Tuple[str, ...]]]:
    """The dotted modules an import statement names, relative imports resolved against the file's own package."""
    if isinstance(node, ast.Import):
        return [(alias.name, ()) for alias in node.names]
    package = dotted(path).split(".")
    base = import_base(package if path.endswith("__init__.py") else package[:-1], node.level, node.module)
    return [(base, tuple(alias.name for alias in node.names))]


def normalized_tokens(text: str, skip: Set[int]) -> List[str]:
    """Tokens with names, numbers and strings reduced to their kind, leaving out the lines in ``skip`` (imports and docstrings)."""
    out: List[str] = []
    try:
        for tok in tokenize.generate_tokens(StringIO(text).readline):
            if tok.start[0] in skip or tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
                continue
            if tok.type == tokenize.NAME:
                out.append(tok.string if tok.string in KEYWORDS else "N")
            elif tok.type == tokenize.NUMBER:
                out.append("0")
            elif tok.type == tokenize.STRING:
                out.append("S")
            else:
                out.append(tok.string)
    except (tokenize.TokenError, IndentationError):
        return out
    return out


KEYWORDS = frozenset("False None True and as assert async await break class continue def del elif else except finally for from global if import in is "
                     "lambda nonlocal not or pass raise return try while with yield".split())


def declaration_parts(value: ast.AST) -> Optional[List[ast.AST]]:
    """The parts a declaring value is made of (none for a constant or a name), else ``None`` when the value computes something."""
    if isinstance(value, (ast.Constant, ast.Name, ast.Attribute)):
        return []
    if isinstance(value, ast.UnaryOp):
        return [value.operand]
    if isinstance(value, ast.Dict):
        return [part for part in [*value.keys, *value.values] if part is not None]
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return list(value.elts)
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "field":   # a dataclass field(...)
        return [part.value for part in value.keywords]
    return None


def declaration_value(value: Optional[ast.AST]) -> bool:
    """Whether a value only declares: a constant, a name, or a dict, list, tuple or set of them (a table, a string list), or a dataclass ``field(...)`` of them."""
    parts = [] if value is None else declaration_parts(value)
    return parts is not None and all(declaration_value(part) for part in parts)


def declaration_lines(tree: ast.AST) -> Set[int]:
    """The lines of statements that declare and compute nothing: module and class level assignments whose value is a table or list of constants, and the
    annotated fields of a dataclass. Two such tables share a shape, not logic, so they are not copied code."""
    skip: Set[int] = set()
    for scope in nodes_of(tree):
        if not isinstance(scope, (ast.Module, ast.ClassDef)):
            continue
        for node in scope.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and declaration_value(node.value):
                skip.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return skip


def skipped_lines(tree: ast.AST) -> Set[int]:
    skip: Set[int] = declaration_lines(tree)
    for node in nodes_of(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            skip.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
                skip.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return skip


FACTS: Dict[Tuple[str, str], Module] = {}   # (relative path, digest of the text) to the facts read from it, so a file unchanged between two projects is read once
RECORD_NAMES = ("interface.py", "solutions.csv", "implementations.csv", "metrics.csv", "intent.csv", "cases.json")


def read_module(root: Path, path: str, markers: Set[str]) -> Module:
    text = (root / path).read_text(encoding="utf-8", errors="replace")
    key = (path, hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest())
    held = FACTS.get(key)
    if held is None:
        held = FACTS[key] = parse_module(root, path, text)
    return replace(held, unit=unit_of(path, markers))


def note_node(module: Module, node: ast.AST, path: str, inner: set) -> None:
    """Record what one syntax node adds to the module: a function, an import, or a name used."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        module.functions.append((node.name, node.lineno, (node.end_lineno or node.lineno) - node.lineno + 1, cyclomatic(node), id(node) not in inner))
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        module.imports.extend(resolve_import(node, path))
    elif isinstance(node, ast.Name):
        module.names.add(node.id)
    elif isinstance(node, ast.Attribute):
        module.names.add(node.attr)


def parse_module(root: Path, path: str, text: str) -> Module:
    module = Module(path, "", text.count("\n") + 1)
    tree = tree_of(root / path)
    if tree is None:
        return module
    module.tree = tree
    inner = {id(sub) for node in nodes_of(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             for sub in ast.walk(node) if sub is not node and isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in nodes_of(tree):
        note_node(module, node, path, inner)
    module.tokens = normalized_tokens(text, skipped_lines(tree))
    return module


def walk_records(root: Path) -> Dict[str, List[str]]:
    """The record files (``RECORD_NAMES``) under the root outside the skipped folders, from one walk of the tree."""
    found: Dict[str, List[str]] = {name: [] for name in RECORD_NAMES}
    for folder, names, files in os.walk(root):
        names[:] = [n for n in names if n not in SKIPPED]
        for name in files:
            if name in found:
                found[name].append((Path(folder) / name).relative_to(root).as_posix())
    return found


def load(root: Path) -> Project:
    root = Path(root).resolve()
    every = listed(root)
    tests = {p: (root / p).read_text(encoding="utf-8", errors="replace") for p in every if is_test(p)}
    code = [p for p in every if not is_test(p)]
    named = walk_records(root)
    markers = {str(PurePosixPath(f).parent) for name in MARKERS for f in named[name]}
    modules = {p: read_module(root, p, markers) for p in code}
    return Project(root, modules, tests, markers, build_index(code), named)
