"""What the code declares and where: the registry of solutions and implementations by scope, its entries and projects, the scope and origin of a declaration, and adding or forgetting one."""
from __future__ import annotations

import contextvars
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from esoi.runtime.implementation_selection.select import Selector

ENV_PREFIX = "ESOI_SELECT_"
ROOT_ENV = "ESOI_ROOT"
SNAPSHOT_NAME = "esoi_selection.json"
SNAPSHOT_ENV = "ESOI_SNAPSHOT"
LAYERS = ("call", "context", "environment", "deployment", "project")
INSTALLED_FOLDERS = ("site-packages", "dist-packages")


class SelectionError(ValueError):
    """The solution or implementation asked for is not known; the message lists the choices."""


@dataclass
class Choice:
    """The implementation a call would run, the cascade layer that decided it, and where the name came from."""
    name: str
    layer: str
    source: str = ""
    reasons: Tuple[str, ...] = ()   # why a consumer chose this arm (record ids, or an unconfirmed marker); set by esoi.runtime.assemble_by_name.assemble
    when: str = ""   # the circumstance condition of a conditional entry (``name@key=value``) that applied; set by esoi.runtime.assemble_by_name.assemble


@dataclass
class Entry:
    """What the code declares about one solution of one scope."""
    solution_id: str
    scope: str = ""
    interface: Any = None
    origin: Optional[Path] = None
    implementations: Dict[str, Any] = field(default_factory=dict)   # name -> the object, or "module:Attr" to import
    kind: str = ""          # what the one-line entry returns: event (output for an input), evaluate (feedback on an artifact),
                            # store (the ready handle; with an input, its query); see esoi.runtime.assemble_by_name.entry
    entry: str = ""         # the method of the interface the one-line entry calls (a function solution is its own entry)
    example: Any = None     # an input the entry accepts offline, shown in the README and run by metric-one-line-entry
    replaced: set = field(default_factory=set)   # names a consumer replaced on purpose: a later declaration of one is ignored


@dataclass
class Project:
    """The records (and configuration) a declaration belongs to, loaded once."""
    config: Any = None
    defaults: Dict[str, str] = field(default_factory=dict)
    paths: Dict[Tuple[str, str], str] = field(default_factory=dict)   # (solution_id, name) -> repository-relative file
    snapshot: Dict[str, Any] = field(default_factory=dict)
    selector: Optional[Selector] = None


REGISTRY: Dict[Tuple[str, str], Entry] = {}   # (scope, solution_id) -> what the code declares
PROJECTS: Dict[str, Optional[Project]] = {}
OVERRIDES: contextvars.ContextVar[Tuple[Tuple[str, str, str], ...]] = contextvars.ContextVar("esoi_overrides", default=())


def key(name: str) -> str:
    return str(name).strip().lower()


def origin_of(obj: Any) -> Optional[Path]:
    try:
        found = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except (TypeError, OSError):
        return None
    return Path(found).resolve() if found else None


def scope_of(obj: Any) -> str:
    """The scope a declaration belongs to: the top-level package of the module that defines it."""
    top = str(getattr(obj, "__module__", "") or "").split(".")[0]
    return "" if top in ("", "__main__", "builtins") else top


def caller_scope_and_origin(depth: int) -> Tuple[str, Optional[Path]]:
    """The scope and file of the module ``depth`` frames up (for ``register``, which has no object to inspect)."""
    frame = inspect.currentframe()
    for _ in range(depth):
        frame = frame.f_back if frame is not None else None
    if frame is None:
        return "", None
    names = frame.f_globals
    top = str(names.get("__name__", "")).split(".")[0]
    where = names.get("__file__")
    return ("" if top in ("", "__main__") else top), (Path(where).resolve() if where else None)


def entry_for(solution_id: str, origin: Optional[Path] = None, scope: str = "") -> Entry:
    entry = REGISTRY.setdefault((scope, solution_id), Entry(solution_id, scope))
    entry.origin = entry.origin or origin
    return entry


def locate(solution_id: str, scope: Optional[str] = None, prefer: str = "") -> str:
    """The scope a call reaches: the one named, else the only package that declares the id (none declared: unscoped).
    When several declare it, ``prefer`` (the scope of the interface being called) breaks the tie."""
    if scope:
        return scope
    scopes = sorted(s for s, sid in REGISTRY if sid == solution_id)
    if len(scopes) > 1 and prefer in scopes:
        return prefer
    if len(scopes) > 1:
        raise SelectionError(f"{solution_id!r} is declared by several packages ({', '.join(s or 'none' for s in scopes)}): "
                             "name one with scope=")
    return scopes[0] if scopes else ""


def entry_of(solution_id: str, scope: str = "") -> Optional[Entry]:
    """What the code declares for a solution in a scope; for no scope, the only package that declares it (a module the
    records name is imported lazily, and declares under its own package)."""
    found = REGISTRY.get((scope, solution_id))
    if found is None and not scope:
        every = [entry for (where, sid), entry in REGISTRY.items() if sid == solution_id]
        found = every[0] if len(every) == 1 else None
    return found



def add(solution_id: str, name: str, target: Any, origin: Optional[Path], scope: str = "", replace: bool = False) -> None:
    label = key(name)
    if not label:
        raise SelectionError(f"an implementation of {solution_id!r} needs a name")
    entry = entry_for(solution_id, origin, scope)
    if label in entry.replaced and not replace:
        return   # the consumer chose its own under this name; the package's declaration, imported later, steps aside
    if replace:
        entry.replaced.add(label)
        entry.implementations[label] = target
        return
    old = entry.implementations.get(label)
    same = old is target or (old is not None and getattr(old, "__qualname__", 0) == getattr(target, "__qualname__", 1)
                             and getattr(old, "__module__", 0) == getattr(target, "__module__", 1))
    if old is not None and not same:
        raise SelectionError(f"{solution_id!r} already has an implementation named {label!r}")
    entry.implementations[label] = target


def forget(solution_id: str, scope: Optional[str] = None) -> None:
    """Drop a solution's declarations (for tests and reloads): every scope's, or only the one named."""
    for found in [k for k in REGISTRY if k[1] == solution_id and (scope is None or k[0] == scope)]:
        REGISTRY.pop(found)
