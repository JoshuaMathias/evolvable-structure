"""Intents as containers: find the intent folders of a repository and read their records as one tree.

An intent is a folder. The top intent is why the project exists, in the project's own words (a project's top intent is
custom to it: for one repository it is the purpose of that repository, not ESOI); the configured folder only holds it. A sub-intent is a subfolder that holds its
own ``intent.csv`` and so lies inside its parent's folder. Each intent folder holds the five specification files
(``problems.csv``, ``solutions.csv``, ``implementations.csv``, ``ideals.csv``, ``metrics.csv``) and optionally
``components.csv`` and ``waivers.csv``. Record ids are unique across the whole tree, so a link in one intent may name
a record in another, and the rules read every intent's records as one set. A folder without an ``intent.csv`` (a
generated ``tracker/``, say) is not an intent.

Records may also be kept beside the code they describe: ``[records] beside_code = ["pkg", "pkg/*"]`` in ``esoi.toml`` lists
folders (paths or globs) that hold record files next to the code. Such a folder with an ``intent.csv`` is a sub-intent; one
without it is a solution folder whose rows belong to the nearest ancestor intent folder (else the top intent). Each record
lives once, in one folder; the same id in two folders is reported (rule S29). Nothing is gathered or copied: every reader sees
the tree through ``folders`` and ``read_rows``.

A repository whose structure folder has no ``intent.csv`` is the legacy layout: one folder of records, optionally
with an ``overall`` network beside it. ``folders`` then returns that one folder, so callers need not tell the layouts
apart. Standard library only.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from .config import Config
from .fields import upgrade_rows
from .tables import read_csv, read_header

INTENT_FILE = "intent.csv"
SKIPPED_FOLDERS = {"__pycache__"}   # the configured tracker folder is skipped too (Config.tracker_dir)
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


RECORD_FILES = ("problems.csv", "ideals.csv", "solutions.csv", "implementations.csv", "metrics.csv")


def beside_folders(config: Config) -> List[Path]:
    """The folders ``[records] beside_code`` names (paths or globs from the repository root) that hold records, in the order
    listed, each once. The structure folder and anything inside it are never beside the code."""
    patterns = config.records.get("beside_code", []) if isinstance(config.records, dict) else []
    found: List[Path] = []
    for pattern in ([patterns] if isinstance(patterns, str) else patterns):
        for path in sorted(config.root.glob(str(pattern))):
            inside = path == config.structure or config.structure in path.parents
            holds = any((path / name).is_file() for name in (INTENT_FILE, *RECORD_FILES))
            if path.is_dir() and holds and not inside and path not in found and path.name not in SKIPPED_FOLDERS:
                found.append(path)
    return found


def owner_of(config: Config, folder: Path, intent_folders: Dict[Path, str]) -> str:
    """The id of the intent that owns the records in ``folder``: the nearest ancestor (or the folder itself) holding an
    ``intent.csv``, else the top intent."""
    for candidate in [folder, *folder.parents]:
        if candidate in intent_folders:
            return intent_folders[candidate]
    return intent_folders.get(config.structure, "")


def named_folders(config: Config, walked: List[Intent], beside: List[Path]) -> Dict[Path, str]:
    """{folder: intent id} for every folder holding an ``intent.csv``, inside the structure folder or beside the code."""
    named = {i.folder: i.intent_id for i in walked}
    for folder in beside:
        if (folder / INTENT_FILE).is_file():
            records = read_csv(folder / INTENT_FILE)
            named[folder] = (records[0].get("intent_id", "") if records else "").strip() or f"<{folder.name}>"
    return named


def located(config: Config) -> List[Tuple[str, Path, bool]]:
    """``(owning intent id, folder, holds an intent.csv)`` for every folder of records, in reading order: the structure
    folder's intents first, then the folders beside the code in the order the configuration lists them."""
    walked = discover_in_structure(config)
    if not walked:
        return []
    beside = beside_folders(config)
    named = named_folders(config, walked, beside)
    out: List[Tuple[str, Path, bool]] = [(i.intent_id, i.folder, True) for i in walked]
    for folder in beside:
        has = folder in named
        out.append((named[folder] if has else owner_of(config, folder, named), folder, has))
    return out


def discover_in_structure(config: Config) -> List[Intent]:
    """The intents inside the structure folder (the top intent first); see ``discover`` for the whole tree."""
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
            if child.name in SKIPPED_FOLDERS or child.name.startswith(".") or child == config.tracker_dir:
                continue
            visit(child, here)

    visit(top, "")
    return found


def discover(config: Config) -> List[Intent]:
    """Every intent of the repository, the top intent first, then sub-intents depth first in folder order, then the
    sub-intents kept beside the code. Empty when the structure folder has no ``intent.csv`` (the legacy layout)."""
    found = discover_in_structure(config)
    if not found:
        return []
    beside = beside_folders(config)
    named = named_folders(config, found, beside)
    for folder in beside:
        if (folder / INTENT_FILE).is_file():
            records = read_csv(folder / INTENT_FILE)
            parent = owner_of(config, folder.parent, {k: v for k, v in named.items() if k != folder})
            found.append(Intent(named[folder], folder, parent, records[0] if records else {}, len(records)))
    return found


SESSION: Dict[str, List[Tuple[str, Path]]] = {}   # filled only while a ``session()`` is open
OPEN = [0]


@contextmanager
def session():
    """Within this block a command finds the record folders once (finding them globs the tree, and a run that judges many results asks
    hundreds of times). Nothing outside a session is remembered, so a program that edits records and asks again sees the edit."""
    OPEN[0] += 1
    try:
        yield
    finally:
        OPEN[0] -= 1
        if not OPEN[0]:
            SESSION.clear()


def folders(config: Config) -> List[Tuple[str, Path]]:
    """``(intent id, folder)`` for every folder that holds records: each intent, or the one legacy folder."""
    key = str(config.root)
    if OPEN[0] and key in SESSION:
        return SESSION[key]
    places = located(config)
    found = [(iid, folder) for iid, folder, _ in places] if places else [("", config.structure)]
    if OPEN[0]:
        SESSION[key] = found
    return found


ENTITY_OF_FILE = {"solutions.csv": "solution", "metrics.csv": "metric"}


def read_rows(config: Config, name: str) -> List[Row]:
    """The rows of one record file across every intent folder, in tree order. In the intent layout each row also
    carries ``intent_id``, the intent whose folder holds it."""
    rows: List[Row] = []
    for intent_id, folder in folders(config):
        for row in upgrade_rows(ENTITY_OF_FILE.get(name, ""), read_csv(folder / name)):
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


def coherence_notes(config: Config, registry) -> List[str]:
    """One note per intent whose ``solution_coherence`` paragraph does not name every solution of the intent (by id or by name, ignoring
    case). Notes, not errors: the paragraph's wording is free, and a name may be put in other words. A blank paragraph is reported as
    an unfilled field by rule S28."""
    out: List[str] = []
    solutions = registry.every_solution()
    for intent in discover(config):
        text = " ".join(intent.row.get("solution_coherence", "").lower().split())
        if not text or not intent.intent_id:
            continue
        def named(r) -> bool:
            name = " ".join(r.get("name", "").lower().split())
            return r.get("solution_id", "").lower() in text or bool(name and re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text))

        missing = [r.get("solution_id", "") for r in solutions if r.get("intent_id", intent.intent_id) == intent.intent_id and not named(r)]
        if missing:
            out.append(f"note: intent {intent.intent_id}: solution_coherence does not name {', '.join(missing)}; say how each fits "
                       "(write the paragraph in display names; ids are handles)")
    return out


def duplicate_rows(config: Config) -> List[Tuple[str, str, List[Path]]]:
    """``(file name, record id, folders)`` for every record id that more than one folder of the tree holds in the same file:
    a record lives once, in the one folder that holds its code."""
    from .records import FILES
    out: List[Tuple[str, str, List[Path]]] = []
    for name, key in ((n, k) for n, k in FILES.values()):
        where: Dict[str, List[Path]] = {}
        for _, folder in folders(config):
            for row in read_csv(folder / name):
                ident = row.get(key, "").strip()
                if ident:
                    where.setdefault(ident, []).append(folder)
        out += [(name, ident, found) for ident, found in where.items() if len(found) > 1]
    return out


def tree_folders(folder: Path) -> List[Path]:
    """The folders of records that belong with ``folder``, a repository's structure folder: itself and every intent folder below it
    and every folder beside the code that its repository's ``esoi.toml`` (in ``folder`` or the folder above it, never searched
    further) lists. A folder with no configuration is just itself. For a program that is handed a records folder, not a Config."""
    from . import config as config_module
    folder = Path(folder).resolve()
    for candidate in (folder, folder.parent):
        if (candidate / config_module.CONFIG_NAME).is_file():
            cfg = config_module.load(candidate / config_module.CONFIG_NAME)
            if cfg.structure.resolve() == folder or candidate == folder:
                return [f for _, f in folders(cfg)] or [folder]
    return [folder]


def read_tree(folder: Path, name: str) -> List[Row]:
    """The rows of one record file across ``tree_folders(folder)``, in reading order (raw rows, no ``intent_id``)."""
    return [row for each in tree_folders(folder) for row in read_csv(each / name)]
