"""Read what a package's own records or snapshot say: the default arm per solution and the module of each arm."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from esoi.optimization.leaderboard.interface import lock_evidence_records_evidence
from esoi.runtime.assemble_by_name import hierarchy
from esoi.structure.intent_registry.interface import AssemblyError
from esoi.runtime.implementation_selection import selection_cascade
from esoi.runtime.implementation_selection import selection_registry
from esoi.runtime.implementation_selection.select import default_name
from esoi.structure.intent_registry import config as config_module
from esoi.structure.intent_registry import registry as registry_module


@dataclass(frozen=True)
class Packaged:
    """What the package's own records or snapshot say: the default per solution, and the module per ``(solution, name)``."""
    defaults: Mapping[str, str]
    modules: Mapping[Tuple[str, str], str]
    source: str
    reasons: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)   # from overrides.csv: why a default differs from a parent's
    evidence: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)   # {solution_id: {verdict, detail, p}}: why the default was chosen


def read_snapshot(package_dir: Path) -> Packaged:
    path = Path(package_dir) / selection_registry.SNAPSHOT_NAME
    if not path.is_file():
        return Packaged({}, {}, "no records and no snapshot")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data = {sid: entry for sid, entry in data.items() if not sid.startswith("@")}   # "@intents" is the intent map, not a solution
        defaults = {sid: selection_registry.key(entry.get("default", "")) for sid, entry in data.items() if entry.get("default")}
        modules = {(sid, selection_registry.key(n)): str(m) for sid, entry in data.items() for n, m in entry.get("modules", {}).items()}
        evidence = {sid: entry["evidence"] for sid, entry in data.items() if isinstance(entry.get("evidence"), dict)}
    except (OSError, ValueError, AttributeError) as error:
        raise AssemblyError(f"the snapshot {path} cannot be read ({error}); remedy: regenerate it with esoi select --snapshot")\
            from error
    return Packaged(defaults, modules, "the packaged snapshot", evidence=evidence)


def arm_modules(cfg: Any, loaded: Any) -> Dict[Tuple[str, str], str]:
    """The module each implementation record names, keyed by ``(solution id, arm key)``; evaluation files are not arms."""
    project = selection_registry.Project(config=cfg)
    modules = {}
    for row in loaded.implementations:
        sid, name = row.get("implementation_id", "").split(":", 1) if ":" in row.get("implementation_id", "") else ("", "")
        where = row.get("filepath", "").strip().split("::")[0]
        if where.endswith(".py") and name and not where.startswith(cfg.evaluation_dir + "/"):
            modules[(sid, selection_registry.key(name))] = selection_cascade.module_for(project, where)
    return modules


def read_records(root: Path) -> Packaged:
    """The records of the folder ``root`` (its ``esoi.toml`` directly: no search upward, no selection table run)."""
    file = root / "esoi.toml"
    if not file.is_file():
        raise AssemblyError(f"records folder {root} has no esoi.toml; it is never looked for in a parent folder")
    try:
        cfg = config_module.load(file)
        loaded = registry_module.load(cfg)
        defaults = {r["solution_id"]: selection_registry.key(name) for r in loaded.every_solution()
                    if r.get("solution_id") and (name := default_name(r, loaded.implementations))}
        modules = arm_modules(cfg, loaded)
    except Exception as error:
        raise AssemblyError(f"the records in {root} cannot be loaded ({type(error).__name__}: {error})") from error
    try:
        evidence = lock_evidence_records_evidence(cfg, loaded)
    except Exception:
        evidence = {}   # no results to judge by: the lock then records the default without a verdict
    return Packaged(defaults, modules, "the records", hierarchy.read_overrides(cfg), evidence)
