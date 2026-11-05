"""Read an adoption: the rows of a repository that reference a solution of another library's records, and the library they point at.

A row of ``solutions.csv`` whose ``adopts`` cell reads ``@<library>/<solution id>`` is an ADOPTED solution: the library defines it and
the row holds only the reference, the repository's binding and the arms it adds. A row whose ``specializes`` cell reads the same way is a
SPECIALIZED solution: a full record of its own for the part of a library solution that needs this repository's data. Which repository
``<library>`` means is configuration: ``[adopts.<library>] repo = "../hub"`` (and optionally ``url``, where generated pages link). The
library's records are read with the same loader as this repository's; nothing of them is copied. Standard library only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from esoi.structure.intent_registry import config as config_module
from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import Registry, load as load_registry

REFERENCE = re.compile(r"^@([\w.-]+)/([\w.-]+)$")
KINDS = ("adopts", "specializes")


@dataclass(frozen=True)
class Reference:
    """One row's reference to a library solution."""
    kind: str          # "adopts" or "specializes"
    local_id: str      # the row's own solution id
    library: str       # the name in [adopts.<library>]
    solution_id: str   # the library's solution id


@dataclass
class Library:
    """A library's loaded records, or the reason they could not be read."""
    name: str
    root: Optional[Path] = None
    config: Optional[Config] = None
    registry: Optional[Registry] = None
    url: str = ""
    error: str = ""

    def solution(self, solution_id: str) -> Optional[Dict[str, str]]:
        rows = self.registry.every_solution() if self.registry is not None else []
        return next((r for r in rows if r.get("solution_id") == solution_id), None)

    def page(self, solution_id: str) -> Optional[Path]:
        """The generated README of the intent folder that holds the library's solution, when there is one."""
        row = self.solution(solution_id)
        if row is None or self.config is None:
            return None
        folder = next((f for i, f in intents.folders(self.config) if i == row.get("intent_id", i)), None)
        page = folder / "README.md" if folder else None
        return page if page is not None and page.is_file() else None


def parse(cell: str) -> Optional[Tuple[str, str]]:
    """``(library, solution id)`` of an ``@library/solution`` cell, or None when the cell is empty or malformed."""
    found = REFERENCE.match((cell or "").strip())
    return (found.group(1), found.group(2)) if found else None


def references(config: Config, registry: Registry) -> Tuple[List[Reference], List[str]]:
    """Every adoption and specialization the records make, and the cells that are not an ``@library/solution`` reference."""
    out: List[Reference] = []
    malformed: List[str] = []
    rows = registry.adopted + [r for r in registry.every_solution() if (r.get("specializes") or "").strip()]
    for row in rows:
        for kind in KINDS:
            cell = (row.get(kind) or "").strip()
            if not cell:
                continue
            parsed = parse(cell)
            if parsed is None:
                malformed.append(f"{row.get('solution_id', '')}: {kind} {cell!r}")
            else:
                out.append(Reference(kind, row.get("solution_id", ""), parsed[0], parsed[1]))
    return out, malformed


class Libraries:
    """The libraries a repository names under ``[adopts]``, each read once."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.loaded: Dict[str, Library] = {}

    def get(self, name: str) -> Library:
        if name not in self.loaded:
            self.loaded[name] = self.read(name)
        return self.loaded[name]

    def read(self, name: str) -> Library:
        entry = (self.config.adopts or {}).get(name)
        if not isinstance(entry, dict) or not str(entry.get("repo", "")).strip():
            return Library(name, error=f"no `[adopts.{name}] repo = ...` in the configuration says where the library {name} is")
        root = (self.config.root / str(entry["repo"])).resolve()
        try:
            conf = config_module.load(root)
            return Library(name, root, conf, load_registry(conf), str(entry.get("url", "")))
        except (config_module.ConfigError, OSError, ValueError) as exc:
            return Library(name, root, error=f"the library {name} cannot be read ({exc})")

    def every(self) -> List[Library]:
        return [self.get(name) for name in sorted(self.config.adopts or {})]


def unresolved(config: Config, registry: Registry) -> List[str]:
    """One line per reference that does not resolve to a solution of a readable library (empty when every one does)."""
    libraries = Libraries(config)
    refs, malformed = references(config, registry)
    out = [f"{item} is not written @library/solution_id" for item in malformed]
    for ref in refs:
        lib = libraries.get(ref.library)
        if lib.error:
            out.append(f"{ref.local_id}: {lib.error}")
        elif lib.solution(ref.solution_id) is None:
            out.append(f"{ref.local_id}: the library {ref.library} has no solution {ref.solution_id}")
    return out
