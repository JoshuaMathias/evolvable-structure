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
    3. environment        ``ESOI_SELECT_<SOLUTION_ID>=name`` (the id upper-cased, ``-`` as ``_``); a package that
                          kept an older variable lists it under ``[selection_env]`` in ``esoi.toml``
    4. deployment         ``[selection]`` in ``esoi.toml``: ``greet-a-person = "name"``
    5. project default    the solution's ``selected`` in the records (read at run time; or a snapshot, see below)

A name may be a variant, ``name@key=value`` (see ``esoi.variants``): the implementation ``name`` is called with the
parameters as keyword arguments.

The project default is never written a second time in code: the records hold it, and ``esoi select --promote`` changes
it when a rival wins on the solution's own metric. An unknown solution or name raises ``SelectionError`` listing the
choices and the layer (and variable) that supplied the bad name, so a typo fails loudly instead of falling through. An
implementation declared in a module that is not imported yet is imported lazily, from the ``filepath`` of its record, only
when it is chosen, so an optional dependency is needed only when its implementation is picked.

Several packages in one process may use the same solution id (two projects can each have a ``call-a-model``): a
declaration belongs to the top-level package of the module that declares it (its scope), and a call that names the
scope (``resolve(id, scope="mylib")``) reaches that package's alone. Without ``scope`` the id must be declared by one
package. A scope also gives the lookup somewhere to start before anything is imported: the package's own location.
A scoped solution reads ``ESOI_SELECT_<SCOPE>_<SOLUTION_ID>`` first, then the plain variable.

The records are found from ``ESOI_ROOT`` or, upward from the declaring module, the nearest ``esoi.toml``; a package
installed into ``site-packages`` is not looked up in the folders around it, because those belong to whatever installed
it. A package installed without its records reads ``esoi_selection.json`` (written by ``esoi select --snapshot``)
beside its top package.

This sits on ``esoi.select``: a repository's selection table and ``Selector`` keep working, their names join the
declared ones, and their ``default`` is optional. ``register`` adds an implementation of another package, or an
object that cannot carry a decorator (an instance).
"""
from __future__ import annotations

import contextvars
import functools
import importlib
import importlib.util
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
from . import variants
from .select import Selector, import_ref, records_defaults

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


@dataclass
class Entry:
    """What the code declares about one solution of one scope."""
    solution_id: str
    scope: str = ""
    interface: Any = None
    origin: Optional[Path] = None
    implementations: Dict[str, Any] = field(default_factory=dict)   # name -> the object, or "module:Attr" to import
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


class Solution:
    """A declared interface that runs the selected implementation when called. ``using="name"`` picks one for that call."""

    def __init__(self, solution_id: str, interface: Any):
        self.solution_id = solution_id
        self.interface = interface
        self.scope = scope_of(interface)
        functools.update_wrapper(self, interface)

    def reached(self) -> str:
        """The scope this interface reaches: the only package that declares its id, else its own package."""
        return locate(self.solution_id, None, self.scope)

    def __call__(self, *args: Any, using: Optional[str] = None, **kwargs: Any) -> Any:
        return resolve(self.solution_id, using, scope=self.reached())(*args, **kwargs)

    def chosen(self, using: Optional[str] = None) -> Choice:
        """The implementation a call would run now, and which layer of the cascade chose it."""
        return choose(self.solution_id, using, scope=self.reached())

    def names(self) -> List[str]:
        return names(self.solution_id, scope=self.reached())

    def implementation(self, using: Optional[str] = None) -> Any:
        """The chosen implementation object itself (a class is not instantiated)."""
        return resolve(self.solution_id, using, scope=self.reached())


def solution(solution_id: str, scope: Optional[str] = None):
    """Declare the interface of a solution. On a function the result is callable and runs the selected implementation;
    a class (a Protocol) is returned unchanged and reached with ``resolve(solution_id)``. The scope is the declaring
    package unless given."""
    def declare(interface: Any) -> Any:
        found = scope_of(interface) if scope is None else scope
        entry_for(solution_id, origin_of(interface), found).interface = interface
        wrapped = interface if inspect.isclass(interface) else Solution(solution_id, interface)
        if wrapped is not interface:
            wrapped.scope = found
        return wrapped
    return declare


def implementation(solution_id: str, name: Optional[str] = None, scope: Optional[str] = None):
    """Declare one alternative of a solution beside its code; the name defaults to the function or class name. The scope
    is the declaring package unless given, so an implementation in one package can serve another package's solution."""
    def declare(obj: Any) -> Any:
        add(solution_id, name or getattr(obj, "__name__", ""), obj, origin_of(obj), scope_of(obj) if scope is None else scope)
        return obj
    return declare


def register(solution_id: str, name: str, target: Any, scope: Optional[str] = None, replace: bool = False) -> None:
    """Declare an implementation that is not a decorated function or class: an instance, an object of another package, or
    ``"module:Attr"`` imported when chosen. The scope is the package of the module that calls this, unless given.
    ``replace=True`` lets a consumer put its own implementation under a name the package already declares, whether that
    declaration comes before or after (without it, two different objects under one name raise)."""
    found, origin = caller_scope_and_origin(2)
    add(solution_id, name, target, origin, found if scope is None else scope, replace)


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


@contextmanager
def override(solution_id: str, name: str, scope: Optional[str] = None) -> Iterator[None]:
    """Select ``name`` for ``solution_id`` for everything run inside the block (this thread or task only)."""
    token = OVERRIDES.set(OVERRIDES.get() + ((solution_id, key(name), scope or ""),))
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
                where = row.get("filepath", "").strip().split("::")[0]
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


def anchor_of(scope: str, entry: Optional[Entry]) -> Optional[Path]:
    """Where the lookup of records starts: the file that declares the solution, else the location of the scope's package
    (so a solution nothing has imported yet can still find its package's records or snapshot)."""
    if entry is not None and entry.origin is not None:
        return entry.origin
    if scope:
        try:
            spec = importlib.util.find_spec(scope)
        except (ImportError, ValueError):
            spec = None
        if spec is not None and spec.origin and spec.origin not in ("built-in", "frozen"):
            return Path(spec.origin).resolve()
    return None


def project_for(solution_id: str, environ: Mapping[str, str], scope: str = "") -> Optional[Project]:
    origin = anchor_of(scope, entry_of(solution_id, scope))
    explicit = environ.get(ROOT_ENV, "").strip()
    if explicit:
        root: Optional[Path] = Path(explicit).expanduser()
    elif origin is not None and any(part in INSTALLED_FOLDERS for part in origin.parts):
        root = None   # the folders around an installed package belong to whatever installed it, not to the package
    else:
        root = origin.parent if origin else Path.cwd()
    project = load_project(root)
    if project is None:
        project = Project(snapshot=read_snapshot(origin, environ))
    return project


def env_name(solution_id: str, scope: str = "") -> str:
    def part(text: str) -> str:
        return re.sub(r"[^0-9A-Za-z]+", "_", text).upper()
    return ENV_PREFIX + (part(scope) + "_" if scope else "") + part(solution_id)


def known_names(solution_id: str, project: Optional[Project], scope: str = "") -> List[str]:
    entry = entry_of(solution_id, scope)
    found = set(entry.implementations) if entry else set()
    if project is not None:
        found |= {name for sid, name in project.paths if sid == solution_id}
        found |= set(project.snapshot.get(solution_id, {}).get("modules", {}))
        if project.selector is not None and solution_id in project.selector.table:
            found |= set(project.selector.names(solution_id))
    return sorted(found)


def names(solution_id: str, environ: Optional[Mapping[str, str]] = None, scope: Optional[str] = None) -> List[str]:
    """Every implementation name that can be chosen for a solution: declared, recorded, or in the legacy table."""
    env = os.environ if environ is None else environ
    where = locate(solution_id, scope)
    return known_names(solution_id, project_for(solution_id, env, where), where)


def project_default(solution_id: str, project: Optional[Project]) -> str:
    if project is None:
        return ""
    if project.selector is not None and solution_id in project.selector.table:
        try:
            return project.selector.default_name(solution_id)
        except ValueError:
            return ""
    return project.defaults.get(solution_id) or project.snapshot.get(solution_id, {}).get("default", "")


def environment_choice(solution_id: str, scope: str, project: Optional[Project],
                       environ: Mapping[str, str]) -> Tuple[str, str]:
    """``(name, variable)`` from the first variable that is set: the scoped one, the plain one, then the older names a
    package lists under ``[selection_env]`` (``solution_id = "VARIABLE"``, or a list of them)."""
    older: Any = project.config.selection_env.get(solution_id, []) if project and project.config else []
    variables = ([env_name(solution_id, scope)] if scope else []) + [env_name(solution_id)] \
        + ([older] if isinstance(older, str) else list(older))
    for variable in variables:
        value = key(environ.get(variable, ""))
        if value:
            return value, variable
    return "", ""


def layer_values(solution_id: str, using: Optional[str], project: Optional[Project], environ: Mapping[str, str],
                 scope: str = "") -> List[Tuple[str, str, str]]:
    """``(layer, name, source)`` for each layer of the cascade that names an implementation, innermost first."""
    pushed = [n for sid, n, where in reversed(OVERRIDES.get()) if sid == solution_id and where in ("", scope)]
    chosen, variable = environment_choice(solution_id, scope, project, environ)
    values = [("call", key(using or ""), "using="), ("context", pushed[0] if pushed else "", "override()"),
              ("environment", chosen, variable),
              ("deployment", key(project.config.selection_choices.get(solution_id, "")) if project and project.config else "",
               "[selection] in esoi.toml"),
              ("project", key(project_default(solution_id, project)), "the records")]
    return [(layer, name, source) for layer, name, source in values if name]


def explain(solution_id: str, using: Optional[str] = None, environ: Optional[Mapping[str, str]] = None,
            scope: Optional[str] = None) -> List[Tuple[str, str, str]]:
    """Every layer that names an implementation for the solution, innermost first: the first one decides."""
    env = os.environ if environ is None else environ
    where = locate(solution_id, scope)
    return layer_values(solution_id, using, project_for(solution_id, env, where), env, where)


def choose(solution_id: str, using: Optional[str] = None, environ: Optional[Mapping[str, str]] = None,
           scope: Optional[str] = None) -> Choice:
    """The implementation that runs for the solution now, and the layer that chose it."""
    env = os.environ if environ is None else environ
    where = locate(solution_id, scope)
    project = project_for(solution_id, env, where)
    layers = layer_values(solution_id, using, project, env, where)
    known = known_names(solution_id, project, where)
    if not layers:
        solutions = sorted({sid for scoped, sid in REGISTRY if scoped == where} | {sid for sid, _ in (project.paths if project else {})})
        raise SelectionError(f"no implementation is selected for {solution_id!r}: no layer of the cascade "
                             f"({', '.join(LAYERS)}) names one" + (f"; choices: {', '.join(known)}" if known else
                             " and none is declared or recorded (declare one with @implementation, or find the records "
                             f"with {ROOT_ENV})" + (f"; solutions that have implementations: {', '.join(solutions)}"
                                                    if solutions else "")))
    layer, name, source = layers[0]
    try:
        variants.split(name)
    except ValueError as exc:
        raise SelectionError(f"{exc} (named by the {layer} layer: {source})") from exc
    if variants.base_of(name) not in known:
        raise SelectionError(f"unknown implementation {name!r} for {solution_id!r} (named by the {layer} layer: {source}); "
                             f"choices: {', '.join(known) or 'none'}")
    return Choice(name, layer, source)


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


def fetch(solution_id: str, name: str, project: Optional[Project], scope: str = "") -> Any:
    entry = entry_of(solution_id, scope)
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
        entry = entry_of(solution_id, scope)
    if entry is not None and name in entry.implementations:
        target = entry.implementations[name]
        if isinstance(target, str):
            target = entry.implementations[name] = import_ref(target)
        return target
    if project is not None and project.selector is not None and solution_id in project.selector.table:
        return project.selector.resolve(solution_id, name)
    raise SelectionError(f"{solution_id!r} lists {name!r} but no declaration of that name was found: declare it with "
                         f"@implementation({solution_id!r}, {name!r}) in the module its record's `filepath` names")


def resolve(solution_id: str, using: Optional[str] = None, environ: Optional[Mapping[str, str]] = None,
            scope: Optional[str] = None) -> Any:
    """The chosen implementation object of a solution (a class is not instantiated). For a variant, the object with its
    parameters bound as keyword arguments."""
    env = os.environ if environ is None else environ
    where = locate(solution_id, scope)
    picked = choose(solution_id, using, env, where)
    base, params = variants.split(picked.name)
    found = fetch(solution_id, base, project_for(solution_id, env, where), where)
    return functools.partial(found, **params) if params else found


def load_declared(config: Any, solution_id: str) -> Dict[str, Any]:
    """Import every implementation the records list for a solution and return the declared ones by name. Used by the
    harness, which measures declarations without an ``impls/`` wrapper."""
    project = load_project(config.root)
    if project is None:
        raise SelectionError(f"the records of {config.root} cannot be loaded")
    for sid, name in sorted(project.paths):
        if sid == solution_id:
            for where in sorted({s for s, i in REGISTRY if i == solution_id} | {config.package or ""}):
                try:
                    fetch(solution_id, name, project, where)
                    break
                except SelectionError:
                    continue   # recorded, but its module declares no implementation of that name
    scopes = [s for s, i in REGISTRY if i == solution_id]
    where = config.package if (config.package or "") in scopes else (scopes[0] if scopes else "")
    return dict(REGISTRY[(where, solution_id)].implementations) if (where, solution_id) in REGISTRY else {}


def snapshot(config: Any) -> Dict[str, Any]:
    """``{solution_id: {"default": name, "modules": {name: dotted module}}}`` from the records, for a package that ships
    without them (``esoi select --snapshot``)."""
    project = load_project(config.root)
    out: Dict[str, Any] = {}
    for sid, name in sorted(project.paths if project else {}):
        entry = out.setdefault(sid, {"default": project.defaults.get(sid, ""), "modules": {}})
        entry["modules"][name] = module_for(project, project.paths[(sid, name)])
    return out
