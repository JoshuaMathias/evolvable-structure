"""The selection cascade: from the records, snapshot, environment, deployment and context, which implementation a call would run, fetched and imported when chosen, and the selection snapshot."""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
from esoi.structure.intent_registry import config as config_module
from esoi.structure.intent_registry import registry as registry_module
from esoi.runtime.implementation_selection import variants
from esoi.runtime.implementation_selection.select import Selector, import_ref, records_defaults
from esoi.runtime.implementation_selection.selection_registry import Choice, ENV_PREFIX, Entry, INSTALLED_FOLDERS, LAYERS, OVERRIDES, PROJECTS, Project, REGISTRY, ROOT_ENV, SNAPSHOT_ENV, SNAPSHOT_NAME, SelectionError, entry_of, key, locate

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
    without them (``esoi select --snapshot``). ``esoi.runtime.assemble_by_name.entry.snapshot`` adds the intent map."""
    project = load_project(config.root)
    out: Dict[str, Any] = {}
    for sid, name in sorted(project.paths if project else {}):
        entry = out.setdefault(sid, {"default": project.defaults.get(sid, ""), "modules": {}})
        entry["modules"][name] = module_for(project, project.paths[(sid, name)])
    return out
