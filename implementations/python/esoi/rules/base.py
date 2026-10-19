"""The rule interface: what a rule group is, and what a rule sees.

A rule group is a function ``run(ctx) -> list[str]`` that returns problem lines, each starting with the id of the
rule it breaks (``S4 path/to/file.py: 1600 lines (max 1500); ...``). It declares the ids it can report with a
one-line summary each, so ``esoi rules`` can list them and ``disable = [...]`` in the configuration can turn
them off. A group whose ids are all disabled is not run; a line of a disabled id is dropped.

To add rules to one repository, write a module with a ``RULES`` list (and optionally ``write_docs(ctx)``), and
name it in the configuration's ``plugins``::

    from esoi.rules.base import Context, RuleGroup

    def no_todo(ctx: Context) -> list[str]:
        return [f"X1 {f}: contains TODO" for f in ctx.files
                if f.endswith(".py") and "TODO" in (ctx.root / f).read_text()]

    RULES = [RuleGroup({"X1": "No TODO left in a Python file."}, no_todo)]

A rule that accepts exceptions asks ``ctx.waived("X1", key)``; the waiver is then recorded as used, so rule S9
can tell the author when a waiver stops applying.
"""
from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import asdict, dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..config import Config
from ..leaderboard import Rows
from ..registry import Registry
from ..tables import glob_re, ids
from .modulefacts import Cache, Facts


@dataclass(frozen=True)
class RuleGroup:
    """Rules that share one pass over the data: ``summaries`` maps each rule id to its one-line statement."""
    summaries: Dict[str, str]
    run: Callable[["Context"], List[str]]


@dataclass
class Context:
    """Everything a rule may look at, loaded once per check."""
    config: Config
    registry: Registry
    files: List[str]
    template: Dict[str, List[Dict[str, str]]]
    results: Dict[str, Rows]
    table: Optional[Dict] = None
    history: Dict[str, Dict[str, List[Dict[str, str]]]] = field(default_factory=dict)   # every results row, oldest first
    table_error: str = ""
    strict: bool = False
    used_waivers: Set[Tuple[str, str]] = field(default_factory=set)
    modules: Optional[Cache] = None

    @property
    def root(self) -> Path:
        return self.config.root

    @property
    def solutions(self) -> List[Dict[str, str]]:
        return self.registry.solutions

    @property
    def components(self) -> List[Dict[str, str]]:
        return self.registry.components

    def every_solution(self) -> List[Dict[str, str]]:
        """Measured and specification solutions together, in record order."""
        return self.registry.every_solution()

    def cache(self) -> Cache:
        if self.modules is None:
            self.modules = Cache(self.root, self.config.cache, self.fingerprint())
        return self.modules

    def fingerprint(self) -> str:
        """What every remembered plugin result depends on besides its own files: the configuration and the structure
        folder (the records and their headers)."""
        base = self.config.structure_dir.rstrip("/") + "/"
        stats = [[f, (self.root / f).stat().st_size, (self.root / f).stat().st_mtime_ns]
                 for f in self.files if f.startswith(base) and (self.root / f).is_file()]
        settings = json.dumps(asdict(self.config), sort_keys=True, default=str)
        return hashlib.sha1((settings + json.dumps(stats)).encode()).hexdigest()

    def facts(self, rel: str) -> Facts:
        """Docstring, imports, environment reads and line count of a Python module, from one cached parse."""
        return self.cache().get(rel)

    def memo(self, name: str, globs: List[str], compute: Callable[[], Any]) -> Any:
        """Remember a plugin's expensive, JSON-serializable result until any file matching ``globs`` changes.

        ``compute`` must read nothing outside the files the globs name (and must not call ``waived``: record the keys
        it consulted in its result and ask afterwards), or a stale answer can be reused."""
        matchers = [glob_re(g) for g in globs]
        stats = []
        for f in self.files:
            if any(rx.match(f) for rx in matchers):
                stat = (self.root / f).stat()
                stats.append([f, stat.st_size, stat.st_mtime_ns])
        key = hashlib.sha1(json.dumps(stats).encode()).hexdigest()
        return self.cache().memo(name, key, compute)

    def waived(self, rule: str, key: str) -> bool:
        """Whether ``waivers.csv`` excuses ``rule`` at ``key``; a waiver that excuses something is marked used."""
        for w in self.registry.waivers:
            if w["rule"] == rule and w["path"] == key:
                self.used_waivers.add((rule, key))
                return True
        return False

    @cached_property
    def owners(self) -> Dict[str, List[str]]:
        """{file: [component ids whose path globs match it]}."""
        owners: Dict[str, List[str]] = {f: [] for f in self.files}
        for row in self.components:
            for pattern in ids(row["path"]):
                rx = glob_re(pattern)
                for f in self.files:
                    if rx.match(f) and row["component_id"] not in owners[f]:
                        owners[f].append(row["component_id"])
        return owners

    @cached_property
    def file_layer(self) -> Dict[str, str]:
        """The layer of each file: its package folder when that is a layer name (so a file placed in the wrong
        component cannot hide a violation), else the layer of the component that owns it."""
        config, layer_of = self.config, {r["component_id"]: r["layer"] for r in self.components}
        out: Dict[str, str] = {}
        base = config.package_dir + "/"
        for f, owning in self.owners.items():
            rest = f[len(base):] if config.package_dir and f.startswith(base) else ""
            pkg = rest.split("/")[0] if "/" in rest else ""
            if pkg in config.layer_rank:
                out[f] = pkg
            elif owning:
                out[f] = layer_of[owning[0]]
        return out

    def top_layer(self, top: str) -> str:
        """Layer of ``<package>/<top>`` (a module or a subpackage), from its owning component."""
        base = self.config.package_dir
        for cand in (f"{base}/{top}.py", f"{base}/{top}/__init__.py"):
            if cand in self.file_layer:
                return self.file_layer[cand]
        return next((v for f, v in self.file_layer.items() if f.startswith(f"{base}/{top}/")), "")

    def harness_arms(self, command: str) -> List[Tuple[str, str]]:
        from ..registry import harness_arms
        return harness_arms(self.config, command)


def parse_file(path: Path) -> Optional[ast.AST]:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError, UnicodeDecodeError):
        return None
