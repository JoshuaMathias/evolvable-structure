"""Intents as containers: find the intent folders of a repository and read their records as one tree.

An intent is a folder. The top intent is why the project exists, in the project's own words (a project's top intent is
custom to it: for one repository it is the purpose of that repository, not ESOI); the configured folder only holds it. A sub-intent is a subfolder that holds its
own ``intent.csv`` and so lies inside its parent's folder. Each intent folder holds the five specification files
(``problems.csv``, ``solutions.csv``, ``implementations.csv``, ``ideals.csv``, ``metrics.csv``) and optionally
``components.csv`` and ``waivers.csv``. Record ids are unique across the whole tree, so a link in one intent may name
a record in another, and the rules read every intent's records as one set. A folder without an ``intent.csv`` (a
generated ``tracker/``, say) is not an intent.

A repository whose structure folder has no ``intent.csv`` is the legacy layout: one folder of records, optionally
with an ``overall`` network beside it. ``folders`` then returns that one folder, so callers need not tell the layouts
apart. Standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from .config import Config
from .tables import read_csv, read_header

INTENT_FILE = "intent.csv"
SKIPPED_FOLDERS = {"tracker", "__pycache__"}
Row = Dict[str, str]


@dataclass
class Intent:
    """One intent folder: its record (``intent.csv``), its parent's id and where it lives."""
    intent_id: str
    folder: Path
    parent: str = ""
    row: Row = field(default_factory=dict)
    rows: int = 1                     # how many rows intent.csv holds (it should hold exactly one)

    @property
    def is_top(self) -> bool:
        return not self.parent


def discover(config: Config) -> List[Intent]:
    """Every intent of the repository, the top intent first, then sub-intents depth first in folder order.
    Empty when the structure folder has no ``intent.csv`` (the legacy layout)."""
    top = config.structure
    if not (top / INTENT_FILE).is_file():
        return []
    found: List[Intent] = []

    def visit(folder: Path, parent: str) -> None:
        here = parent
        if (folder / INTENT_FILE).is_file():
            records = read_csv(folder / INTENT_FILE)
            row = records[0] if records else {}
            found.append(Intent(row.get("intent_id", "").strip(), folder, parent, row, len(records)))
            here = row.get("intent_id", "").strip() or f"<{folder.name}>"
        for child in sorted(p for p in folder.iterdir() if p.is_dir()):
            if child.name in SKIPPED_FOLDERS or child.name.startswith("."):
                continue
            visit(child, here)

    visit(top, "")
    return found


def folders(config: Config) -> List[Tuple[str, Path]]:
    """``(intent id, folder)`` for every folder that holds records: each intent, or the one legacy folder."""
    intents = discover(config)
    return [(i.intent_id, i.folder) for i in intents] if intents else [("", config.structure)]


def read_rows(config: Config, name: str) -> List[Row]:
    """The rows of one record file across every intent folder, in tree order. In the intent layout each row also
    carries ``intent_id``, the intent whose folder holds it."""
    rows: List[Row] = []
    for intent_id, folder in folders(config):
        for row in read_csv(folder / name):
            if intent_id:
                row.setdefault("intent_id", intent_id)
            rows.append(row)
    return rows


def header_union(config: Config, name: str) -> List[str]:
    """The column names of one record file across every intent folder, first seen first."""
    seen: Dict[str, None] = {}
    for _, folder in folders(config):
        path = folder / name
        if path.is_file():
            for column in read_header(path):
                seen.setdefault(column, None)
    return list(seen)
