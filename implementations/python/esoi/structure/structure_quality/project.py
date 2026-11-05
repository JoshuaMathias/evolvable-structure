"""What the checks of Structure Quality read: a project's Python modules, parsed once, each assigned to the unit (solution folder) it belongs to.

A unit is the folder of the nearest ``interface.py`` or ``solutions.csv`` above a file; a file with neither above it belongs to the unit named by
its first two folders. Test files are kept apart: they are read only for the shared contract tests. Nothing is imported or run; the
standard library only.
"""
from __future__ import annotations

import ast
import subprocess
import tokenize
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Dict, List, Set, Tuple

SKIPPED = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist", "site-packages", ".esoi_cache", ".tox", ".mypy_cache"}
MARKERS = ("interface.py", "solutions.csv")
TESTS = {"tests", "test"}


@dataclass
class Module:
    path: str
    unit: str
    lines: int
    functions: List[Tuple[str, int, int]] = field(default_factory=list)   # name, first line, length in lines
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
    base = node.module or ""
    if node.level:
        package = dotted(path).split(".")
        package = package[:-1] if not path.endswith("__init__.py") else package
        package = package[: len(package) - (node.level - 1)] if node.level > 1 else package
        base = ".".join(package + ([base] if base else []))
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


def skipped_lines(tree: ast.AST) -> Set[int]:
    skip: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            skip.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
                skip.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return skip


def read_module(root: Path, path: str, markers: Set[str]) -> Module:
    text = (root / path).read_text(encoding="utf-8", errors="replace")
    module = Module(path, unit_of(path, markers), text.count("\n") + 1)
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return module
    module.tree = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module.functions.append((node.name, node.lineno, (node.end_lineno or node.lineno) - node.lineno + 1))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module.imports.extend(resolve_import(node, path))
        elif isinstance(node, ast.Name):
            module.names.add(node.id)
        elif isinstance(node, ast.Attribute):
            module.names.add(node.attr)
    module.tokens = normalized_tokens(text, skipped_lines(tree))
    return module


def load(root: Path) -> Project:
    root = Path(root).resolve()
    every = listed(root)
    tests = {p: (root / p).read_text(encoding="utf-8", errors="replace") for p in every if is_test(p)}
    code = [p for p in every if not is_test(p)]
    markers = {str(PurePosixPath(f).parent) for f in marker_files(root)}
    modules = {p: read_module(root, p, markers) for p in code}
    return Project(root, modules, tests, markers, build_index(code))


def marker_files(root: Path) -> List[str]:
    found: List[str] = []
    for name in MARKERS:
        found += [p.relative_to(root).as_posix() for p in root.rglob(name) if not SKIPPED & set(p.relative_to(root).parts)]
    return found
