"""Declare a solution where the code is; call it; the selected implementation runs.

    from esoi import solution, implementation

    @solution("greet-a-person")                       # the interface: its signature is the contract
    def greet(name: str) -> str:
        ...                                           # the body is never run

    @implementation("greet-a-person", "plain")        # one alternative, declared beside its code
    def plain(name: str) -> str:
        return f"Hello, {name}!"

    greet("Ada")                                      # runs the selected implementation
    greet("Ada", using="loud")                        # this call only, by name (like run_version's name string)
    with override("greet-a-person", "loud"):          # everything inside the block
        greet("Ada")

Which implementation runs is decided by one cascade, the innermost layer that names one winning:

    1. per call           ``greet(..., using="name")``
    2. context            ``with override(solution_id, "name"):``
    3. environment        ``ESOI_SELECT_<SOLUTION_ID>=name`` (the id upper-cased, ``-`` as ``_``)
    4. deployment         ``[selection]`` in ``esoi.toml``: ``greet-a-person = "name"``
    5. project default    the solution's ``selected`` in the records (read at run time; or a snapshot, see below)

The project default is never written a second time in code: the records hold it, and ``esoi select --promote`` changes
it when a rival wins on the solution's own metric. An unknown solution or name raises ``SelectionError`` listing the
choices and the layer that supplied the bad name, so a typo fails loudly instead of falling through. An implementation
declared in a module that is not imported yet is imported lazily, from the ``path`` of its record, only when it is
chosen, so an optional dependency is needed only when its implementation is picked.

The records are found from ``ESOI_ROOT`` or, upward from the declaring module, the nearest ``esoi.toml``. A package
installed without them reads ``esoi_selection.json`` (written by ``esoi select --snapshot``) beside its top package.

This sits on ``esoi.select``: a repository's selection table and ``Selector`` keep working, their names join the
declared ones, and their ``default`` is optional. ``register`` adds an implementation of another package.
"""
from __future__ import annotations

import contextvars
import functools
import importlib
import inspect
import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple

from . import config as config_module
from . import registry as registry_module
from .select import Selector, import_ref, records_defaults

ENV_PREFIX = "ESOI_SELECT_"
ROOT_ENV = "ESOI_ROOT"
SNAPSHOT_NAME = "esoi_selection.json"
SNAPSHOT_ENV = "ESOI_SNAPSHOT"
LAYERS = ("call", "context", "environment", "deployment", "project")


class SelectionError(ValueError):
    """The solution or implementation asked for is not known; the message lists the choices."""


@dataclass
class Choice:
    """The implementation a call would run, and the cascade layer that decided it."""
    name: str
    layer: str


@dataclass
class Entry:
    """What the code declares about one solution."""
    solution_id: str
    interface: Any = None
    origin: Optional[Path] = None
    implementations: Dict[str, Any] = field(default_factory=dict)   # name -> the object, or "module:Attr" to import


@dataclass
class Project:
    """The records (and configuration) a declaration belongs to, loaded once."""
    config: Any = None
    defaults: Dict[str, str] = field(default_factory=dict)
    paths: Dict[Tuple[str, str], str] = field(default_factory=dict)   # (solution_id, name) -> repository-relative file
    snapshot: Dict[str, Any] = field(default_factory=dict)
    selector: Optional[Selector] = None


REGISTRY: Dict[str, Entry] = {}
PROJECTS: Dict[str, Optional[Project]] = {}
OVERRIDES: contextvars.ContextVar[Tuple[Tuple[str, str], ...]] = contextvars.ContextVar("esoi_overrides", default=())


def key(name: str) -> str:
    return str(name).strip().lower()


def origin_of(obj: Any) -> Optional[Path]:
    try:
        found = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except (TypeError, OSError):
        return None
    return Path(found).resolve() if found else None


def entry_for(solution_id: str, origin: Optional[Path] = None) -> Entry:
    entry = REGISTRY.setdefault(solution_id, Entry(solution_id))
    entry.origin = entry.origin or origin
    return entry


class Solution:
    """A declared interface that runs the selected implementation when called. ``using="name"`` picks one for that call."""

    def __init__(self, solution_id: str, interface: Any):
        self.solution_id = solution_id
        self.interface = interface
        functools.update_wrapper(self, interface)

    def __call__(self, *args: Any, using: Optional[str] = None, **kwargs: Any) -> Any:
        return resolve(self.solution_id, using)(*args, **kwargs)

    def chosen(self, using: Optional[str] = None) -> Choice:
        """The implementation a call would run now, and which layer of the cascade chose it."""
        return choose(self.solution_id, using)

    def names(self) -> List[str]:
        return names(self.solution_id)

    def implementation(self, using: Optional[str] = None) -> Any:
        """The chosen implementation object itself (a class is not instantiated)."""
        return resolve(self.solution_id, using)


def solution(solution_id: str):
    """Declare the interface of a solution. On a function the result is callable and runs the selected implementation;
    a class (a Protocol) is returned unchanged and reached with ``resolve(solution_id)``."""
    def declare(interface: Any) -> Any:
        entry_for(solution_id, origin_of(interface)).interface = interface
        return interface if inspect.isclass(interface) else Solution(solution_id, interface)
    return declare


def implementation(solution_id: str, name: Optional[str] = None):
    """Declare one alternative of a solution beside its code; the name defaults to the function or class name."""
    def declare(obj: Any) -> Any:
        add(solution_id, name or getattr(obj, "__name__", ""), obj, origin_of(obj))
        return obj
    return declare


def register(solution_id: str, name: str, target: Any) -> None:
    """Declare an implementation that lives in another package: an object, or ``"module:Attr"`` imported when chosen."""
    add(solution_id, name, target, None)


def add(solution_id: str, name: str, target: Any, origin: Optional[Path]) -> None:
    label = key(name)
    if not label:
        raise SelectionError(f"an implementation of {solution_id!r} needs a name")
    entry = entry_for(solution_id, origin)
    old = entry.implementations.get(label)
    same = old is target or (old is not None and getattr(old, "__qualname__", 0) == getattr(target, "__qualname__", 1)
                             and getattr(old, "__module__", 0) == getattr(target, "__module__", 1))
    if old is not None and not same:
        raise SelectionError(f"{solution_id!r} already has an implementation named {label!r}")
    entry.implementations[label] = target


def forget(solution_id: str) -> None:
    """Drop a solution's declarations (for tests and reloads)."""
    REGISTRY.pop(solution_id, None)


@contextmanager
def override(solution_id: str, name: str) -> Iterator[None]:
    """Select ``name`` for ``solution_id`` for everything run inside the block (this thread or task only)."""
    token = OVERRIDES.set(OVERRIDES.get() + ((solution_id, key(name)),))
    try:
        yield
    finally:
        OVERRIDES.reset(token)


def load_project(root: Optional[Path]) -> Optional[Project]:
    if root is None:
        return None
    found = config_module.find(root)
    if found is None:
        return None
    tag = str(found)
    if tag not in PROJECTS:
        try:
            cfg = config_module.load(found)
            project = Project(config=cfg, defaults=records_defaults(cfg))
            for row in registry_module.load(cfg).implementations:
                sid, _, name = row.get("implementation_id", "").partition(":")
                where = row.get("path", "").strip().split("::")[0]
                if where.endswith(".py") and name and not where.startswith(cfg.evaluation_dir + "/"):   # a harness wrapper is no runtime choice
                    project.paths[(sid, key(name))] = where
            if cfg.selection_table:
                project.selector = Selector.from_config(cfg)
            PROJECTS[tag] = project
        except Exception:
            PROJECTS[tag] = None   # records that cannot load fall through to the snapshot, then a loud error
    return PROJECTS[tag]


def read_snapshot(origin: Optional[Path], environ: Mapping[str, str]) -> Dict[str, Any]:
    wanted = environ.get(SNAPSHOT_ENV, "").strip()
    folders = [origin.parent, *origin.parents] if origin else []
    for path in ([Path(wanted)] if wanted else []) + [f / SNAPSHOT_NAME for f in folders]:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
    return {}


def project_for(solution_id: str, environ: Mapping[str, str]) -> Optional[Project]:
    entry = REGISTRY.get(solution_id)
    origin = entry.origin if entry else None
    explicit = environ.get(ROOT_ENV, "").strip()
    project = load_project(Path(explicit).expanduser() if explicit else (origin.parent if origin else Path.cwd()))
    if project is None:
        project = Project(snapshot=read_snapshot(origin, environ))
    return project


def env_name(solution_id: str) -> str:
    return ENV_PREFIX + re.sub(r"[^0-9A-Za-z]+", "_", solution_id).upper()


def known_names(solution_id: str, project: Optional[Project]) -> List[str]:
    found = set(REGISTRY[solution_id].implementations) if solution_id in REGISTRY else set()
    if project is not None:
        found |= {name for sid, name in project.paths if sid == solution_id}
        found |= set(project.snapshot.get(solution_id, {}).get("modules", {}))
        if project.selector is not None and solution_id in project.selector.table:
            found |= set(project.selector.names(solution_id))
    return sorted(found)


def names(solution_id: str, environ: Optional[Mapping[str, str]] = None) -> List[str]:
    """Every implementation name that can be chosen for a solution: declared, recorded, or in the legacy table."""
    return known_names(solution_id, project_for(solution_id, os.environ if environ is None else environ))


def project_default(solution_id: str, project: Optional[Project]) -> str:
    if project is None:
        return ""
    if project.selector is not None and solution_id in project.selector.table:
        try:
            return project.selector.default_name(solution_id)
        except ValueError:
            return ""
    return project.defaults.get(solution_id) or project.snapshot.get(solution_id, {}).get("default", "")


def layer_values(solution_id: str, using: Optional[str], project: Optional[Project],
                 environ: Mapping[str, str]) -> List[Tuple[str, str]]:
    """``(layer, name)`` for each layer of the cascade that names an implementation, innermost first."""
    pushed = [n for sid, n in reversed(OVERRIDES.get()) if sid == solution_id]
    values = [("call", key(using or "")), ("context", pushed[0] if pushed else ""),
              ("environment", key(environ.get(env_name(solution_id), ""))),
              ("deployment", key(project.config.selection_choices.get(solution_id, "")) if project and project.config else ""),
              ("project", key(project_default(solution_id, project)))]
    return [(layer, name) for layer, name in values if name]


def explain(solution_id: str, using: Optional[str] = None, environ: Optional[Mapping[str, str]] = None) -> List[Tuple[str, str]]:
    """Every layer that names an implementation for the solution, innermost first: the first one decides."""
    env = os.environ if environ is None else environ
    return layer_values(solution_id, using, project_for(solution_id, env), env)


def choose(solution_id: str, using: Optional[str] = None, environ: Optional[Mapping[str, str]] = None) -> Choice:
    """The implementation that runs for the solution now, and the layer that chose it."""
    env = os.environ if environ is None else environ
    project = project_for(solution_id, env)
    layers = layer_values(solution_id, using, project, env)
    known = known_names(solution_id, project)
    if not layers:
        raise SelectionError(f"no implementation is selected for {solution_id!r}: no layer of the cascade "
                             f"({', '.join(LAYERS)}) names one" + (f"; choices: {', '.join(known)}" if known else
                             " and none is declared or recorded (declare one with @implementation, or find the records "
                             f"with {ROOT_ENV})"))
    layer, name = layers[0]
    if name not in known:
        raise SelectionError(f"unknown implementation {name!r} for {solution_id!r} (named by the {layer} layer); "
                             f"choices: {', '.join(known) or 'none'}")
    return Choice(name, layer)


def import_module_of(project: Project, module: str) -> None:
    roots = [project.config.root / p for p in project.config.python_path] + [project.config.root]
    for folder in map(str, roots):
        if folder not in sys.path:
            sys.path.append(folder)
    importlib.import_module(module)


def module_for(project: Project, relative: str) -> str:
    """The dotted module of a repository-relative file, under the first configured ``python_path`` folder that holds it."""
    config = project.config
    path = Path(relative)
    for base in [Path(p) for p in config.python_path] + [Path(".")]:
        try:
            parts = path.relative_to(base).with_suffix("").parts
        except ValueError:
            continue
        return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
    return ".".join(path.with_suffix("").parts)


def fetch(solution_id: str, name: str, project: Optional[Project]) -> Any:
    entry = REGISTRY.get(solution_id)
    if entry is None or name not in entry.implementations:
        module = ""
        if project is not None and (solution_id, name) in project.paths:
            module = module_for(project, project.paths[(solution_id, name)])
        elif project is not None:
            module = project.snapshot.get(solution_id, {}).get("modules", {}).get(name, "")
        if module:
            if project.config is not None:
                import_module_of(project, module)
            else:
                importlib.import_module(module)
        entry = REGISTRY.get(solution_id)
    if entry is not None and name in entry.implementations:
        target = entry.implementations[name]
        if isinstance(target, str):
            target = entry.implementations[name] = import_ref(target)
        return target
    if project is not None and project.selector is not None and solution_id in project.selector.table:
        return project.selector.resolve(solution_id, name)
    raise SelectionError(f"{solution_id!r} lists {name!r} but no declaration of that name was found: declare it with "
                         f"@implementation({solution_id!r}, {name!r}) in the module its record's `path` names")


def resolve(solution_id: str, using: Optional[str] = None, environ: Optional[Mapping[str, str]] = None) -> Any:
    """The chosen implementation object of a solution (a class is not instantiated)."""
    env = os.environ if environ is None else environ
    picked = choose(solution_id, using, env)
    return fetch(solution_id, picked.name, project_for(solution_id, env))


def load_declared(config: Any, solution_id: str) -> Dict[str, Any]:
    """Import every implementation the records list for a solution and return the declared ones by name. Used by the
    harness, which measures declarations without an ``impls/`` wrapper."""
    project = load_project(config.root)
    if project is None:
        raise SelectionError(f"the records of {config.root} cannot be loaded")
    for sid, name in sorted(project.paths):
        if sid == solution_id:
            try:
                fetch(solution_id, name, project)
            except SelectionError:
                continue   # recorded, but its module declares no implementation of that name
    return dict(REGISTRY[solution_id].implementations) if solution_id in REGISTRY else {}


def snapshot(config: Any) -> Dict[str, Any]:
    """``{solution_id: {"default": name, "modules": {name: dotted module}}}`` from the records, for a package that ships
    without them (``esoi select --snapshot``)."""
    project = load_project(config.root)
    out: Dict[str, Any] = {}
    for sid, name in sorted(project.paths if project else {}):
        entry = out.setdefault(sid, {"default": project.defaults.get(sid, ""), "modules": {}})
        entry["modules"][name] = module_for(project, project.paths[(sid, name)])
    return out
