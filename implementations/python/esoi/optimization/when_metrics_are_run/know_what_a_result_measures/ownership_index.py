"""Which files each component, solution and implementation owns, read once per state of the records, and the staleness rule in force."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry.config import Config, DEFAULT_STALENESS_RULE, STALENESS_RULES
from esoi.structure.intent_registry.tables import glob_source, ids as cells


RULES = STALENESS_RULES
DEFAULT_RULE = DEFAULT_STALENESS_RULE
SOLUTION_ID = "know-what-a-result-measures"

INDEXES: Dict[str, Tuple[tuple, "Index"]] = {}


@dataclass
class Index:
    """The ownership map of one repository as the stale rules read it."""
    components: List[Tuple[str, List[re.Pattern], Set[str]]] = field(default_factory=list)   # (id, path patterns, solution ids)
    solutions: List[Dict[str, str]] = field(default_factory=list)
    implementations: List[Dict[str, str]] = field(default_factory=list)
    selected: str = ""
    hosts: Optional[Set[Path]] = None                  # the folders that may hold records beside code, found once
    code_folders: Dict[int, Optional[Path]] = field(default_factory=dict)   # id of an implementation row -> the folder of its code


def glob_pattern(text: str) -> re.Pattern:
    """A path glob as a regular expression: ``**`` crosses folders, ``*`` and ``?`` stay in one; a plain folder owns what is in it."""
    return re.compile(glob_source(text) + r"(?:/.*)?$")


def normal(name: str) -> str:
    return name.split(":")[-1].split("::")[0].strip().lower().replace("-", "_")


def record_folders(config: Config) -> list:
    from esoi.structure.intent_registry import intents
    return intents.folders(config)


def signature(config: Config) -> tuple:
    found = []
    for _, folder in record_folders(config):
        for name in ("components.csv", "implementations.csv", "solutions.csv", "metrics.csv"):
            path = folder / name
            if path.is_file():
                info = path.stat()
                found.append((str(path), info.st_mtime_ns, info.st_size))
    return tuple(found)


def index_of(config: Config) -> Index:
    """The ownership map, read once per state of the records."""
    from esoi.structure.intent_registry.registry import load
    key = signature(config)
    cached = INDEXES.get(str(config.root))
    if cached and cached[0] == key:
        return cached[1]
    registry = load(config)
    found = Index(solutions=list(registry.solutions), implementations=list(registry.implementations))
    for row in registry.components:
        patterns = [glob_pattern(p) for p in cells(row.get("path", ""))]
        found.components.append((row.get("component_id", ""), patterns, set(cells(row.get("solutions", "")))))
    for row in found.solutions:
        if row.get("solution_id") == SOLUTION_ID:
            found.selected = normal(row.get("selected", ""))
    INDEXES[str(config.root)] = (key, found)
    return found


def rule_for(config: Config) -> str:
    """The rule in force: the configuration, else the records' selected arm, else the library default."""
    if config.staleness_rule:
        return config.staleness_rule
    chosen = index_of(config).selected
    return chosen if chosen in RULES else DEFAULT_RULE


def arm_solutions(config: Config, index: Index, component: str, impl: str) -> List[str]:
    """The solutions whose metric runs this arm (or, when no command names the arm, any arm of the component)."""
    from esoi.structure.intent_registry.registry import harness_arms
    exact, loose = [], []
    for row in index.solutions:
        arms = harness_arms(config, row.get("metric_command", ""))
        if (component, impl) in arms:
            exact.append(row["solution_id"])
        elif any(comp == component for comp, _ in arms):
            loose.append(row["solution_id"])
    return exact or loose


def implementation_files(index: Index, solutions: List[str]) -> List[str]:
    files = []
    for row in index.implementations:
        if row.get("solution_id") in solutions:
            path = (row.get("filepath") or "").partition("::")[0].strip()
            if path and not path.startswith("@") and path not in files:
                files.append(path)
    return files


def shared_with_others(index: Index, code_folder, solutions: List[str], host: Path) -> bool:
    """Whether code of a solution outside ``solutions`` lies inside the host folder."""
    for r in index.implementations:
        where = code_folder(r)
        if r.get("solution_id") not in solutions and where is not None and host in [where, *where.parents]:
            return True
    return False


def beside_folders(config: Config, index: Index, solutions: List[str]) -> List[str]:
    """The beside-code folder of a solution, when the records live beside the code and its code is alone in that folder."""
    from esoi.structure.intent_registry import besidecode
    if index.hosts is None:
        index.hosts = set(besidecode.hosts(config))
    allowed = index.hosts
    if not allowed:
        return []
    root = config.root.resolve()

    def code_folder(row: Dict[str, str]) -> Optional[Path]:
        if id(row) not in index.code_folders:
            index.code_folders[id(row)] = besidecode.code_folder(config, row.get("filepath", ""))
        return index.code_folders[id(row)]
    found = []
    for sid in solutions:
        folders = [f for f in (code_folder(r) for r in index.implementations if r.get("solution_id") == sid) if f is not None]
        host = besidecode.host_for(allowed, besidecode.common(folders), root) if folders else None
        if host is not None and host != root and not shared_with_others(index, code_folder, solutions, host):
            found.append(host.relative_to(root).as_posix())
    return found
