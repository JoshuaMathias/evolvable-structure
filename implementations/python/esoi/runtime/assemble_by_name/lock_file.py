"""Read a lock file: the selected arm the lock names for a solution, which the assembler's cascade uses as its lock layer.

The lock is written, diffed and updated by ``esoi.runtime.implementation_selection.lock``; reading it sits here, below the assembler, so the
assembler's cascade needs nothing from the unit that writes the lock. Standard library and ``esoi`` only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from esoi.structure.intent_registry.interface import LockError

SCHEMA = "esoi.lock/1"

CACHE: Dict[Tuple[str, int, int], Dict[str, Any]] = {}


def check_arms(found: Dict[str, Any], where: str) -> None:
    """Raise ``LockError`` for a solution entry that names no arm."""
    for sid, entry in found["solutions"].items():
        if not isinstance(entry, dict) or not str(entry.get("arm", "")).strip():
            raise LockError(f"{where}: solution {sid!r} names no arm; remedy: esoi lock --update --solution {sid}")


def read(source: Any) -> Dict[str, Any]:
    """The lock as a dict, from a path or a mapping. Raises ``LockError`` for a file that is missing, unreadable or of another schema."""
    if isinstance(source, Mapping):
        found: Any = dict(source)
        where = "the lock mapping"
    else:
        path = Path(source)
        where = str(path)
        try:
            stat = path.stat()
        except OSError as error:
            raise LockError(f"the lock {where} cannot be read ({error}); remedy: esoi lock --file {where} writes it") from error
        key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
        if key in CACHE:
            return CACHE[key]
        try:
            found = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise LockError(f"the lock {where} cannot be read ({error}); remedy: restore it from version control, or esoi lock --file {where} writes a new one") from error
    if not isinstance(found, dict) or not str(found.get("schema", "")).startswith("esoi.lock/") or not isinstance(found.get("solutions"), dict):
        raise LockError(f"{where} is not an esoi lock (schema {SCHEMA!r} with a solutions table); remedy: esoi lock writes one")
    if str(found["schema"]) != SCHEMA:
        raise LockError(f"{where} has schema {found['schema']!r}, this esoi reads {SCHEMA!r}; remedy: esoi lock --update rewrites it")
    check_arms(found, where)
    if not isinstance(source, Mapping):
        CACHE[key] = found
    return found


def locked_arm(assembler: Any, source: Any, solution_id: str) -> Optional[Tuple[str, str]]:
    """``(arm, where)`` the lock names for a solution, or ``None`` when it is not locked. Used by the assembler's cascade."""
    found = read(source)
    entry = found["solutions"].get(solution_id)
    return (str(entry["arm"]).strip().lower(), "the lock mapping" if isinstance(source, Mapping) else str(source)) if entry else None
