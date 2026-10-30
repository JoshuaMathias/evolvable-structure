"""Depend on other solutions by name, not by import: resolve a part by a validated name, build the parts a program uses in
dependency order, and fail at startup on a cycle or a need nothing meets.

    from typing import Protocol
    from esoi import solution, implementation
    from esoi.assemble import Assembler, AssemblyConfig

    @solution("store")                       # a seat: a Protocol class, so importing it runs nothing
    class Store(Protocol):
        def get(self, key: str) -> str: ...

    @implementation("store", "memory")
    class Memory:
        def get(self, key): return key

    @implementation("report")
    class Report:
        def __init__(self, store: Store):    # a parameter typed with a seat IS a need of that seat
            self.store = store

    parts = Assembler("mylib", package_dir, noun="mylib")        # one per package: its scope, its folder
    system = parts.assemble(AssemblyConfig(seats=("report",)))   # builds store, then report, once
    system["report"].store is system["store"]                    # needs injected by name, no import between the two

A name is the only thing configuration, a row or an environment can carry. It is checked against ``NAME_PATTERN`` before
``esoi.runtime`` sees it (an import path such as ``os:system`` never reaches an import) and must be one the seat lists.
An import target comes only from a ``register`` call in the consumer's code (trusted) or from the package's own packaged
records and snapshot, whose module must start with the scope and whose file must lie inside ``package_dir``.

Everything goes through ``esoi.runtime`` (register, resolve, names, choose) under the package's scope. The library reads no
environment: the only environment ``esoi.runtime`` sees is ``AssemblyConfig.selection_environ``, a mapping the consumer
hands in (default empty). It never imports a consumer: the consumer constructs the ``Assembler`` and passes it what it
owns. Standard library and ``esoi`` only.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import logging
import re
import typing
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from . import runtime
from .fields import parse_tags
from .tables import ids, read_csv, read_header, write_csv

NAME_PATTERN = "^[a-z0-9][a-z0-9_-]*$"
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
FORBIDDEN_ENVIRON = (runtime.ROOT_ENV, runtime.SNAPSHOT_ENV)   # these would point esoi at records the package did not ship
CONSUMER_PROVIDED = "consumer-provided"   # the tag of a solution that has no default arm because the consumer supplies it
log = logging.getLogger("esoi.assemble")


class AssemblyError(ValueError):
    """An assembly error. The message names the solution id, scope, layer, the available names and a remedy."""


def check_name(name: Any, what: str = "name") -> str:
    """The name, or ``AssemblyError``. ``:`` and ``.`` (import paths) and anything off the pattern never reach ``esoi``."""
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise AssemblyError(f"{what} {name!r} rejected: a name matches {NAME_PATTERN} (never an import path, so ':' and '.' "
                            f"are refused); remedy: pass one of the names the seat lists with names(solution_id)")
    return name


@dataclass(frozen=True)
class AssemblyConfig:
    """What a consumer hands the assembler, once, at startup.

    ``seats`` is the manifest of solution ids the consumer uses (empty: every seat that has a default arm or is provided).
    ``names`` are explicit names per solution id and ``selections`` the consumer's own selections (they live on this object,
    never process-wide). ``options`` are the non-seat constructor arguments per solution id. ``selection_environ`` is the
    only environment ``esoi`` ever sees: a consumer that wants an ``ESOI_SELECT_<SCOPE>_<SOLUTION_ID>`` choice puts it here.
    """
    seats: Tuple[str, ...] = ()
    names: Mapping[str, str] = field(default_factory=dict)
    selections: Mapping[str, str] = field(default_factory=dict)
    options: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    selection_environ: Mapping[str, str] = field(default_factory=dict)


def environ_of(config: Optional[AssemblyConfig]) -> Dict[str, str]:
    """The environment ``esoi`` is allowed to see: the config field, validated. Never the process environment."""
    raw = dict((config or AssemblyConfig()).selection_environ)
    for key, value in raw.items():
        if key in FORBIDDEN_ENVIRON:
            raise AssemblyError(f"selection_environ may not set {key}: it would point esoi at records the package did not ship")
        if key.startswith(runtime.ENV_PREFIX) and value:
            check_name(str(value), f"selection_environ {key}")
    return {str(k): str(v) for k, v in raw.items()}


def builder_of(target: Any) -> Any:
    """The callable that builds an arm: a class's ``__init__``, or the function itself."""
    if inspect.isclass(target):
        return None if target.__init__ is object.__init__ else target.__init__
    return target if inspect.isfunction(target) else None


def package_version(target: Any) -> str:
    top = str(getattr(target, "__module__", None) or type(target).__module__).split(".")[0]
    try:
        return importlib.metadata.version(top)
    except importlib.metadata.PackageNotFoundError:
        return "unversioned"


def config_hash(options: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(options, sort_keys=True, default=str).encode()).hexdigest()[:8]


def cycle_of(edges: Mapping[str, Set[str]]) -> List[str]:
    """One dependency cycle in ``{seat: {seats it needs}}`` as a list ending where it began, or []."""
    state: Dict[str, int] = {}
    stack: List[str] = []

    def visit(node: str) -> List[str]:
        state[node] = 1
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if state.get(nxt) is None:
                ring = visit(nxt)
                if ring:
                    return ring
        stack.pop()
        state[node] = 2
        return []

    for node in sorted(edges):
        if state.get(node) is None:
            ring = visit(node)
            if ring:
                return ring
    return []


def problems(solutions: Sequence[Mapping[str, str]], implementations: Sequence[Mapping[str, str]],
             needs: Mapping[str, Set[str]]) -> List[str]:
    """Every way the records and the declared needs disagree. Empty means the graph is sound. ``needs`` is
    ``{implementation_id: {solution ids}}`` as ``Assembler.declared_needs`` reads it from the constructor parameters."""
    bad: List[str] = []
    seats = {s["solution_id"]: s for s in solutions}
    tags = {sid: {t["tag"] for t in parse_tags(s.get("tags", ""))} for sid, s in seats.items()}
    for row in implementations:
        iid = row["implementation_id"]
        recorded = set(ids(row.get("uses_solution_ids", "")))
        if iid in needs and recorded != needs[iid]:
            bad.append(f"{iid}: uses_solution_ids is {sorted(recorded) or 'empty'} but its constructor parameters need "
                       f"{sorted(needs[iid]) or 'nothing'} (sync_uses writes it)")
        for need in sorted(needs.get(iid, set())):
            if need not in seats:
                bad.append(f"{iid}: needs {need}, which is no solution in the records")
            elif not seats[need].get("selected", "").strip() and CONSUMER_PROVIDED not in tags[need]:
                bad.append(f"{iid}: needs {need}: the seat has no default arm and is not tagged {CONSUMER_PROVIDED}")
    for sid, tag in tags.items():
        if CONSUMER_PROVIDED in tag and seats[sid].get("selected", "").strip():
            bad.append(f"{sid}: tagged {CONSUMER_PROVIDED} but has a default arm ({seats[sid]['selected']})")
    default = {sid: s.get("selected", "").strip() for sid, s in seats.items()}
    edges: Dict[str, Set[str]] = {}
    for row in implementations:
        sid = row["solution_id"]
        if default.get(sid) and row["implementation_id"].partition(":")[2] == default[sid]:
            edges.setdefault(sid, set()).update(needs.get(row["implementation_id"], set()))
    ring = cycle_of(edges)
    if ring:
        bad.append("default arms form a cycle: " + " -> ".join(ring))
    return bad


class Assembly:
    """The built objects of one consumer, frozen. ``assembly[solution_id]`` is the object; ``reasons`` has one line per seat."""

    def __init__(self, assembler: "Assembler", config: AssemblyConfig, objects: Mapping[str, Any], reasons: Mapping[str, str]):
        self.assembler = assembler
        self.config = config
        self.objects = MappingProxyType(dict(objects))
        self.reason_by_seat = MappingProxyType(dict(reasons))

    @property
    def reasons(self) -> Tuple[str, ...]:
        return tuple(self.reason_by_seat.values())

    def seats(self) -> List[str]:
        return list(self.objects)

    def __getitem__(self, solution_id: str) -> Any:
        try:
            return self.objects[solution_id]
        except KeyError:
            raise AssemblyError(f"{solution_id!r} was not assembled; assembled seats: {', '.join(self.objects) or 'none'}; "
                                "remedy: list it in AssemblyConfig.seats or provide it") from None

    def __contains__(self, solution_id: str) -> bool:
        return solution_id in self.objects

    def get(self, solution_id: str, default: Any = None) -> Any:
        return self.objects.get(solution_id, default)

    def choice(self, solution_id: str, name: Optional[str] = None) -> runtime.Choice:
        return self.assembler.choice(solution_id, name, self.config)

    def resolve(self, solution_id: str, name: Optional[str] = None) -> Any:
        """The implementation object (not built) under this consumer's selections."""
        return self.assembler.resolve(solution_id, name, self.config)


@dataclass(frozen=True)
class Assembler:
    """Name-based resolution and assembly for the solutions one package declares.

    ``scope`` is the package's top-level name (the scope its solutions are declared under), ``package_dir`` its folder (the
    safe-loading boundary), ``seats_module`` the dotted module that declares the seats (imported once, by ``prepare``, so a
    name can be checked before anything else is imported), and ``noun`` the word its messages use for the package.
    """
    scope: str
    package_dir: Path
    seats_module: str = ""
    noun: str = "package"

    # names and the cascade

    def prepare(self) -> None:
        """Declare the seats (importing them runs nothing): after this the scope knows its solution ids."""
        if self.seats_module:
            importlib.import_module(self.seats_module)

    def known_solution(self, solution_id: str) -> bool:
        self.prepare()
        return any(scope == self.scope and sid == solution_id for scope, sid in runtime.REGISTRY)

    def check_solution(self, solution_id: str) -> str:
        check_name(solution_id, "solution id")
        if not self.known_solution(solution_id):
            known = sorted(sid for scope, sid in runtime.REGISTRY if scope == self.scope)
            raise AssemblyError(f"unknown solution {solution_id!r} in scope {self.scope!r}; available: {', '.join(known) or 'none'}")
        return solution_id

    def names(self, solution_id: str, config: Optional[AssemblyConfig] = None) -> List[str]:
        """Every implementation name that can be chosen for a seat: declared in code, recorded, or in the packaged snapshot."""
        self.check_solution(solution_id)
        return runtime.names(solution_id, environ=environ_of(config), scope=self.scope)

    def declared(self, solution_id: str, config: Optional[AssemblyConfig] = None) -> List[str]:
        """Names the package itself declares for a seat: its records and snapshot, and code in its own modules."""
        project = runtime.project_for(solution_id, environ_of(config), self.scope)
        found: Set[str] = set()
        if project is not None:
            found |= {n for sid, n in project.paths if sid == solution_id}
            found |= set(project.snapshot.get(solution_id, {}).get("modules", {}))
        entry = runtime.entry_of(solution_id, self.scope)
        for name, target in (entry.implementations.items() if entry else ()):
            if str(getattr(target, "__module__", "")).startswith(self.scope + "."):
                found.add(name)
        return sorted(found)

    def module_for(self, solution_id: str, name: str, config: Optional[AssemblyConfig] = None) -> str:
        """The dotted module the package's own records or snapshot name for an arm ('' when none)."""
        project = runtime.project_for(solution_id, environ_of(config), self.scope)
        if project is None:
            return ""
        if project.config is not None and (solution_id, name) in project.paths:
            return runtime.module_for(project, project.paths[(solution_id, name)])
        return str(project.snapshot.get(solution_id, {}).get("modules", {}).get(name, ""))

    def safe_module(self, module: str) -> str:
        """A packaged record's module, or ``AssemblyError``: it must start with the scope and its ``find_spec`` origin must
        lie inside ``package_dir``. Nothing is imported to find out."""
        if not isinstance(module, str) or not module.startswith(self.scope + ".") or ".." in module:
            raise AssemblyError(f"packaged record module {module!r} rejected: it must start with '{self.scope}.'")
        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError):
            spec = None
        origin = Path(spec.origin).resolve() if spec is not None and spec.origin not in (None, "built-in", "frozen") else None
        if origin is None or Path(self.package_dir).resolve() not in origin.parents:
            raise AssemblyError(f"packaged record module {module!r} rejected: its file is not inside the installed "
                                f"{self.scope} package")
        return module

    def choice(self, solution_id: str, name: Optional[str] = None, config: Optional[AssemblyConfig] = None) -> runtime.Choice:
        """Which arm a seat would use now and which layer decided it. Cascade: explicit name, the consumer's selections on the
        config, then the package default. A name a layer supplies that is unknown is an error, never a fall-through."""
        self.check_solution(solution_id)
        cfg = config or AssemblyConfig()
        env = environ_of(cfg)
        available = runtime.names(solution_id, environ=env, scope=self.scope)
        for layer, named in (("explicit name", name or cfg.names.get(solution_id)), ("consumer selections", cfg.selections.get(solution_id))):
            if named:
                check_name(named, f"{layer} for {solution_id!r}")
                if named not in available:
                    raise AssemblyError(f"unknown implementation {named!r} for {solution_id!r} in scope {self.scope!r} (layer: {layer}); "
                                        f"available: {', '.join(available) or 'none'}; remedy: use one of them, or register your own "
                                        f"under a name you own with register()")
                return runtime.Choice(named, layer, "")
        try:
            picked = runtime.choose(solution_id, None, environ=env, scope=self.scope)
        except runtime.SelectionError as error:
            raise AssemblyError(f"{solution_id!r} in scope {self.scope!r}: {error}; available: {', '.join(available) or 'none'}; "
                                f"remedy: name one, or provide your own object") from error
        labels = {"call": "explicit name", "context": "context override", "environment": "selection environ",
                  "deployment": "deployment (esoi.toml)", "project": f"{self.noun} default"}
        return runtime.Choice(picked.name, labels.get(picked.layer, picked.layer), picked.source)

    def load(self, solution_id: str, picked: str, config: Optional[AssemblyConfig] = None) -> Any:
        """The implementation object for a name. A packaged arm's module is imported here, after the safe-loading check, so
        ``esoi`` never extends ``sys.path`` or imports a module the package did not vouch for."""
        entry = runtime.entry_of(solution_id, self.scope)
        if entry is None or picked not in entry.implementations:
            module = self.module_for(solution_id, picked, config)
            if module:
                importlib.import_module(self.safe_module(module))
        return runtime.resolve(solution_id, picked, environ=environ_of(config), scope=self.scope)

    def resolve(self, solution_id: str, name: Optional[str] = None, config: Optional[AssemblyConfig] = None) -> Any:
        """The chosen implementation object of a seat (a class is not instantiated)."""
        return self.load(solution_id, self.choice(solution_id, name, config).name, config)

    def register(self, solution_id: str, name: str, target: Any, replace: bool = False) -> None:
        """Register an implementation (a class, a function, or an instance) under a name the consumer owns. The package's own
        names are never replaced: asking to register or replace one raises, so a consumer cannot shadow an arm by accident or
        by attack. Registered targets are trusted code of the consumer that called this; never loaded from a record."""
        self.check_solution(solution_id)
        check_name(name, f"registered name for {solution_id!r}")
        if name in self.declared(solution_id):
            raise AssemblyError(f"{name!r} is declared by the {self.noun} for {solution_id!r} in scope {self.scope!r} and cannot be "
                                f"{'replaced' if replace else 'registered over'}; remedy: register your own under a name you own")
        runtime.register(solution_id, name, target, scope=self.scope, replace=replace)

    # needs

    def seat_of(self, protocol: Any) -> Optional[str]:
        """The solution id a seat Protocol was declared for in this scope, or None."""
        self.prepare()
        for (scope, sid), entry in runtime.REGISTRY.items():
            if scope == self.scope and entry.interface is protocol:
                return sid
        return None

    def needs_of(self, target: Any) -> Dict[str, str]:
        """``{parameter name: solution id}`` for each parameter typed with a seat Protocol. An instance has none."""
        build = builder_of(target)
        if build is None:
            return {}
        try:
            hints = typing.get_type_hints(build)
        except Exception as error:   # a forward reference that does not resolve is a declaration bug: say so
            raise AssemblyError(f"cannot read the parameter types of {getattr(target, '__qualname__', target)!r}: {error}") from error
        found = {}
        for param in inspect.signature(build).parameters:
            seat = self.seat_of(hints.get(param)) if param in hints else None
            if seat:
                found[param] = seat
        return found

    def declared_needs(self, implementations: Sequence[Mapping[str, str]]) -> Dict[str, Set[str]]:
        """``{implementation_id: {seat ids it needs}}`` read from the constructor parameters of each recorded implementation."""
        found = {}
        for row in implementations:
            sid, _, name = row["implementation_id"].partition(":")
            found[row["implementation_id"]] = set(self.needs_of(self.load(sid, name)).values())
        return found

    def uses_problems(self, folder: Path) -> List[str]:
        """Every disagreement between the records in ``folder`` and the needs the code declares. Empty means sound."""
        rows = read_csv(Path(folder) / "implementations.csv")
        return problems(read_csv(Path(folder) / "solutions.csv"), rows, self.declared_needs(rows))

    def sync_uses(self, folder: Path) -> None:
        """Write the ``uses_solution_ids`` column of ``implementations.csv`` in ``folder`` from the constructor parameters."""
        path = Path(folder) / "implementations.csv"
        rows = read_csv(path)
        needs = self.declared_needs(rows)
        for row in rows:
            row["uses_solution_ids"] = ";".join(sorted(needs[row["implementation_id"]]))
        write_csv(path, read_header(path), rows)

    # assembly

    def check_provided(self, solution_id: str, obj: Any) -> None:
        self.check_solution(solution_id)
        entry = runtime.entry_of(solution_id, self.scope)
        protocol = entry.interface if entry is not None else None
        if protocol is not None and getattr(protocol, "_is_runtime_protocol", False) and not isinstance(obj, protocol):
            raise AssemblyError(f"the object provided for {solution_id!r} does not satisfy {protocol.__name__}")

    def seats_with_a_default(self, config: AssemblyConfig) -> List[str]:
        found = []
        for scope, sid in sorted(runtime.REGISTRY):
            if scope != self.scope:
                continue
            try:
                self.choice(sid, None, config)
            except AssemblyError:
                continue
            found.append(sid)
        return found

    def assemble(self, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
        """Build the seats a consumer uses, in dependency order, once. A provided object wins for its seat; otherwise the
        cascade's arm is built with its needs injected and its ``options`` passed. A cycle or an unmet need fails here,
        naming the chain. The result is frozen: nothing resolves at call time, so no lock is needed."""
        cfg = config or AssemblyConfig()
        given = dict(provided or {})
        environ_of(cfg)
        self.prepare()
        for sid, obj in given.items():
            self.check_provided(sid, obj)
        objects: Dict[str, Any] = {}
        reasons: Dict[str, str] = {}

        def need_error(chain: List[Tuple[str, str]], sid: str) -> AssemblyError:
            remedy = f"remedy: pass provided={{{sid!r}: ...}} or register an arm for it"
            if not chain:
                return AssemblyError(f"{sid}: no arm, not provided; {remedy}")
            parent, arm = chain[-1]
            return AssemblyError(f"{parent} ({arm}) needs {sid}: no arm, not provided (chain: "
                                 f"{' -> '.join([s for s, _ in chain] + [sid])}); {remedy}")

        def build(sid: str, chain: List[Tuple[str, str]]) -> Any:
            if sid in objects:
                return objects[sid]
            ring = [s for s, _ in chain]
            if sid in ring:
                raise AssemblyError("dependency cycle: " + " -> ".join(ring[ring.index(sid):] + [sid]))
            if sid in given:
                objects[sid] = given[sid]
                reasons[sid] = (f"{sid} -> {type(given[sid]).__name__} (layer: consumer provided, package version "
                                f"{package_version(given[sid])}, config hash {config_hash({})})")
                return objects[sid]
            explicit = bool(cfg.names.get(sid) or cfg.selections.get(sid))
            try:
                picked = self.choice(sid, None, cfg)
            except AssemblyError:
                if explicit:
                    raise
                raise need_error(chain, sid) from None
            target = self.load(sid, picked.name, cfg)
            options = dict(cfg.options.get(sid, {}))
            kwargs = {param: build(need, chain + [(sid, picked.name)]) for param, need in self.needs_of(target).items()}
            if inspect.isclass(target) or inspect.isfunction(target):   # a class or factory is built; anything else is an instance
                built = builder_of(target)
                params = inspect.signature(built).parameters if built is not None else {}
                extra = [k for k in options if k not in params or k in kwargs]
                if extra:
                    raise AssemblyError(f"{sid} ({picked.name}) has no option(s) {', '.join(extra)}; its parameters: "
                                        f"{', '.join(p for p in params if p != 'self' and p not in kwargs) or 'none'}")
                objects[sid] = target(**kwargs, **options)
            else:
                objects[sid] = target
            reasons[sid] = (f"{sid} -> {picked.name} (layer: {picked.layer}, package version {package_version(target)}, "
                            f"config hash {config_hash(options)})")
            return objects[sid]

        for sid in (list(cfg.seats) or sorted(set(given) | set(self.seats_with_a_default(cfg)))):
            self.check_solution(sid)
            build(sid, [])
        for line in reasons.values():
            log.info(line)
        return Assembly(self, cfg, objects, reasons)
