"""What the layout rules need to know about a Python module, read from one parse and cached on disk.

Parsing every module of a large package dominates the time of ``esoi check``, and the layout rules ask three questions
of each module (is there a docstring, which package modules does it import, does it read the environment). This module
answers all three from a single pass and remembers the answer in ``.esoi_cache/modules.json`` under the repository root,
keyed by file size and modification time, so a second run only reads the files that changed. The cache is a pure
accelerator: deleting it changes nothing but the time, ``cache = false`` in the configuration turns it off, and the
folder is never listed as a repository file.
"""
from __future__ import annotations

import ast
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

CACHE_DIR = ".esoi_cache"
CACHE_FILE = "modules.json"
VERSION = 1
PARALLEL_FROM = 80   # cold modules before the scan is spread over processes


@dataclass
class Facts:
    """The answers for one module. ``imports`` are ``[line, level, module, names]``; ``plain`` are ``[line, dotted name]``."""
    size: int = 0
    lines: int = 0
    docstring: bool = False
    parsed: bool = True
    imports: List[list] = field(default_factory=list)
    plain: List[list] = field(default_factory=list)
    env: List[int] = field(default_factory=list)


def is_type_checking(node: ast.If) -> bool:
    return getattr(node.test, "id", getattr(node.test, "attr", "")) == "TYPE_CHECKING"


def collect(node: ast.AST, facts: Facts) -> None:
    """Walk once, skipping the body of ``if TYPE_CHECKING:`` (imports there are annotations only)."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and is_type_checking(child):
            for stmt in child.orelse:
                collect_one(stmt, facts)
            continue
        collect_one(child, facts)


def collect_one(node: ast.AST, facts: Facts) -> None:
    if isinstance(node, ast.ImportFrom):
        facts.imports.append([node.lineno, node.level, node.module, [a.name for a in node.names]])
        if node.module == "os" and any(a.name in ("environ", "getenv", "putenv") for a in node.names):
            facts.env.append(node.lineno)
    elif isinstance(node, ast.Import):
        for a in node.names:
            facts.plain.append([node.lineno, a.name])
    elif isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv", "putenv") \
            and isinstance(node.value, ast.Name) and node.value.id == "os":
        facts.env.append(node.lineno)
    collect(node, facts)


def scan(path: Path) -> Facts:
    """Read one module. A module that does not parse has no imports and no docstring, and ``parsed`` is false."""
    facts = Facts()
    try:
        text = path.read_text(encoding="utf-8")
        facts.size = path.stat().st_size
    except (OSError, UnicodeDecodeError):
        facts.parsed = False
        return facts
    facts.lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        facts.parsed = False
        return facts
    facts.docstring = bool(ast.get_docstring(tree))
    collect(tree, facts)
    return facts


class Cache:
    """On-disk memory of ``scan`` results; ``get`` re-reads a file only when its size or modification time changed."""

    def __init__(self, root: Path, enabled: bool = True):
        self.root = Path(root)
        self.enabled = enabled
        self.path = self.root / CACHE_DIR / CACHE_FILE
        self.entries: Dict[str, dict] = {}
        self.memos: Dict[str, dict] = {}
        self.dirty = False
        if enabled and self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("version") == VERSION:
                    self.entries = data.get("files", {})
                    self.memos = data.get("memos", {})
            except (OSError, ValueError):
                self.entries = {}

    def fresh(self, rel: str) -> bool:
        try:
            stat = (self.root / rel).stat()
        except OSError:
            return True
        hit = self.entries.get(rel)
        return bool(hit and hit["key"] == [stat.st_size, stat.st_mtime_ns])

    def prefetch(self, rels: List[str]) -> None:
        """Scan the modules not in the cache in parallel, when there are enough of them to repay starting workers."""
        misses = [r for r in rels if not self.fresh(r)]
        if len(misses) < PARALLEL_FROM:
            return
        try:
            with ProcessPoolExecutor() as pool:
                scanned = list(pool.map(scan, [self.root / r for r in misses], chunksize=16))
        except (OSError, RuntimeError):
            return
        for rel, facts in zip(misses, scanned):
            stat = (self.root / rel).stat()
            self.entries[rel] = {"key": [stat.st_size, stat.st_mtime_ns], "facts": facts.__dict__}
        self.dirty = True

    def get(self, rel: str) -> Facts:
        path = self.root / rel
        try:
            stat = path.stat()
        except OSError:
            return Facts(parsed=False)
        key = [stat.st_size, stat.st_mtime_ns]
        hit = self.entries.get(rel)
        if hit and hit["key"] == key:
            return Facts(**hit["facts"])
        facts = scan(path)
        self.entries[rel] = {"key": key, "facts": facts.__dict__}
        self.dirty = True
        return facts

    def memo(self, name: str, key: str, compute: Callable[[], Any]) -> Any:
        """The result of ``compute()`` remembered under ``name`` for as long as ``key`` (a fingerprint of its inputs) holds."""
        hit = self.memos.get(name)
        if self.enabled and hit and hit["key"] == key:
            return hit["value"]
        value = compute()
        if self.enabled:
            self.memos[name] = {"key": key, "value": value}
            self.dirty = True
        return value

    def save(self, keep: Optional[set] = None) -> None:
        if not (self.enabled and self.dirty):
            return
        files = {k: v for k, v in self.entries.items() if keep is None or k in keep}
        try:
            self.path.parent.mkdir(exist_ok=True)
            self.path.write_text(json.dumps({"version": VERSION, "files": files, "memos": self.memos}), encoding="utf-8")
        except OSError:
            pass
