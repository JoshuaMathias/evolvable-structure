"""Depend on other solutions by name, not by import: resolve a part by a validated name, build the parts a program uses in
dependency order, and fail at startup on a cycle or a need nothing meets.

    from pathlib import Path
    from typing import Protocol
    from esoi import solution, implementation
    from esoi.assemble import Assembler, AssemblyConfig

    @solution("store")                       # a Protocol class, so importing it runs nothing
    class Store(Protocol):
        def get(self, key: str) -> str: ...

    @implementation("store", "memory")
    class Memory:
        def get(self, key): return key

    @implementation("report", "plain")
    class Report:
        def __init__(self, store: Store):    # a parameter typed with a solution's Protocol IS a need of that solution
            self.store = store

    parts = Assembler("mylib", Path(__file__).parent)    # once, in the package mylib: its scope and its folder
    system = parts.assemble(AssemblyConfig(solutions=("report",), selections={"store": "memory", "report": "plain"}))
    assert system["report"].store is system["store"]     # built in order, needs injected by name

A name is the only thing configuration, a row or an environment can carry. It is checked against ``NAME_PATTERN`` and must
be one the solution lists. A module is imported only when a record of the package names it (a record's ``filepath``, or the
package's own ``esoi_selection.json``), it starts with the scope, and its file lies inside ``package_dir``: ``safe_module``
decides that from the position of the file, importing nothing, and the import then checks each package on the way against
that file. ``Assembler.modules`` are the package's own modules that declare solutions and arms; ``prepare`` imports them.

Under an Assembler the records come from one place: the folder ``records`` names (its ``esoi.toml`` is read, never searched
for in a parent folder), else the snapshot beside the package. The deployment table, the selection table of an
``esoi.toml``, ``override()`` and the process environment are not consulted; ``sys.path`` is not changed; a load error is raised.
The cascade is: explicit name, the consumer's selections, ``AssemblyConfig.selection_environ`` (the only environment
``esoi`` is given, and only the variable of this scope and solution), then the package default.

A package that builds on another gives ``Assembler(..., parent=other)``. The cascade then ends with the child's own default,
then the parent's (then the parent's parent's), so the child states only what differs and every solution of the parent is
visible to it; a name must be one the solution lists in the child or a parent. A layer value may be ``name@key=value`` or a
list of them: a condition on ``AssemblyConfig.circumstances``, the first entry that applies winning. ``reasons`` says why a
selection differs from a parent's default, and ``explain`` lists every layer of one solution with the winner named
(``esoi.hierarchy``; the guide is docs/guides/hierarchical-defaults.md).

It never imports a consumer: the consumer constructs the ``Assembler`` and passes it what it owns. Standard library and ``esoi``
only. ``Assembly`` is frozen: choices and implementations are fixed when ``assemble`` returns, nothing resolves later.
``Assembler.choice`` and ``Assembler.resolve`` are lookups made when they are called.
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
import threading
import typing
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from . import config as config_module
from . import hierarchy
from . import registry as registry_module
from . import runtime
from .fields import parse_tags
from .select import default_name
from .tables import ids, read_csv, read_header, write_csv

__all__ = ["Assembler", "Assembly", "AssemblyConfig", "AssemblyError", "CONSUMER_PROVIDED", "NAME_PATTERN", "check_name",
           "cycle_of", "problems"]

NAME_PATTERN = "^[a-z0-9][a-z0-9_-]*$"
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
CONSUMER_PROVIDED = "consumer-provided"   # the tag of a solution that has no default arm because the consumer supplies it
log = logging.getLogger("esoi.assemble")


class AssemblyError(ValueError):
    """An assembly error. The message names the solution id, scope, layer, the available names and a remedy."""


def check_name(name: Any, what: str = "name") -> str:
    """The name, or ``AssemblyError``. A name is lower case letters, digits, ``_`` and ``-``; ``.`` and ``:`` (import
    paths) and path separators never pass, so a name is never mistaken for something to import. A dotted model name such
    as ``gpt-4.1`` is data for ``options``, or an arm named ``gpt-4-1``: no recorded arm name here needs a dot."""
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise AssemblyError(f"{what} {name!r} rejected: a name matches {NAME_PATTERN} (never an import path, so '.' and ':' "
                            f"are refused); remedy: pass one of the names the solution lists with names(solution_id)")
    return name


@dataclass(frozen=True)
class AssemblyConfig:
    """What a consumer hands the assembler, once, at startup.

    ``solutions`` is the manifest of solution ids the consumer uses (empty: every solution that has a default arm or is
    provided). ``names`` are explicit names per solution id and ``selections`` the consumer's own selections (they live on
    this object, never process-wide). ``options`` are the non-solution constructor arguments per solution id.
    ``selection_environ`` is the only environment ``esoi`` ever sees: a consumer that wants an
    ``ESOI_SELECT_<SCOPE>_<SOLUTION_ID>`` choice puts exactly that variable here, and nothing else is accepted.
    A name in ``names``, ``selections`` or ``selection_environ`` may be ``name@key=value,...`` (or, in the first two, a list of
    such entries): it then applies only when every ``key=value`` holds in ``circumstances``, the caller's own mapping.
    ``reasons`` is ``{solution_id: [record id or "unconfirmed: text", ...]}`` for the ``selections`` of the same solution: why
    it differs from a parent's default (shown by ``explain``, recorded in the ``Choice``).
    """
    solutions: Tuple[str, ...] = ()
    names: Mapping[str, str] = field(default_factory=dict)
    selections: Mapping[str, str] = field(default_factory=dict)
    options: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    selection_environ: Mapping[str, str] = field(default_factory=dict)
    reasons: Mapping[str, Sequence[str]] = field(default_factory=dict)
    circumstances: Mapping[str, Any] = field(default_factory=dict)


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


def protocol_members(protocol: Any) -> Set[str]:
    """The names a Protocol class requires of an object: its methods and annotated attributes, own and inherited."""
    members: Set[str] = set()
    for klass in protocol.__mro__:
        if klass in (typing.Protocol, typing.Generic, object) or not getattr(klass, "_is_protocol", False):
            continue
        members |= {n for n in vars(klass) if not (n.startswith("__") and n.endswith("__")) and not n.startswith("_abc_")
                    and n not in ("_is_protocol", "_is_runtime_protocol")}
        members |= set(klass.__dict__.get("__annotations__", {}))
    return members


def same_declaration(one: Any, other: Any) -> bool:
    """The same object, or the same definition imported again (a reloaded module declares its arm anew)."""
    return one is other or (getattr(one, "__module__", 0) == getattr(other, "__module__", 1)
                            and getattr(one, "__qualname__", 0) == getattr(other, "__qualname__", 1))


def cycle_of(edges: Mapping[str, Set[str]]) -> List[str]:
    """One dependency cycle in ``{solution: {solutions it needs}}`` as a list ending where it began, or []."""
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
    rows = {s["solution_id"]: s for s in solutions}
    tags = {sid: {t["tag"] for t in parse_tags(s.get("tags", ""))} for sid, s in rows.items()}
    for row in implementations:
        iid = row["implementation_id"]
        recorded = set(ids(row.get("uses_solution_ids", "")))
        if iid in needs and recorded != needs[iid]:
            bad.append(f"{iid}: uses_solution_ids is {sorted(recorded) or 'empty'} but its constructor parameters need "
                       f"{sorted(needs[iid]) or 'nothing'} (sync_uses writes it)")
        for need in sorted(needs.get(iid, set())):
            if need not in rows:
                bad.append(f"{iid}: needs {need}, which is no solution in the records")
            elif not rows[need].get("selected", "").strip() and CONSUMER_PROVIDED not in tags[need]:
                bad.append(f"{iid}: needs {need}: the solution has no default arm and is not tagged {CONSUMER_PROVIDED}")
    for sid, tag in tags.items():
        if CONSUMER_PROVIDED in tag and rows[sid].get("selected", "").strip():
            bad.append(f"{sid}: tagged {CONSUMER_PROVIDED} but has a default arm ({rows[sid]['selected']})")
    default = {sid: s.get("selected", "").strip() for sid, s in rows.items()}
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
    """The built objects of one consumer, frozen. ``assembly[solution_id]`` is the object; ``reasons`` has one line per
    solution; ``choice`` and ``implementation`` return what was chosen and loaded when ``assemble`` ran."""

    def __init__(self, assembler: "Assembler", config: AssemblyConfig, built: Mapping[str, Tuple[Any, str, Any, Any]],
                 pending: Optional[Mapping[str, str]] = None):
        """``built`` is ``{solution_id: (object, reason line, Choice or None, implementation or None)}`` in build order.
        ``pending`` is ``{solution_id: one line saying what the consumer must pass}`` for a solution ``assemble_defaults`` skipped."""
        self.pending = MappingProxyType(dict(pending or {}))
        self.assembler = assembler
        self.config = config
        self.objects = MappingProxyType({sid: item[0] for sid, item in built.items()})
        self.reason_by_solution = MappingProxyType({sid: item[1] for sid, item in built.items()})
        self.choices = MappingProxyType({sid: item[2] for sid, item in built.items() if item[2] is not None})
        self.implementations = MappingProxyType({sid: item[3] for sid, item in built.items() if item[3] is not None})

    @property
    def reasons(self) -> Tuple[str, ...]:
        return tuple(self.reason_by_solution.values())

    def solutions(self) -> List[str]:
        """The assembled solution ids, in build order."""
        return list(self.objects)

    def __getitem__(self, solution_id: str) -> Any:
        try:
            return self.objects[solution_id]
        except KeyError:
            raise AssemblyError(f"{solution_id!r} was not assembled; assembled: {', '.join(self.objects) or 'none'}; "
                                "remedy: list it in AssemblyConfig.solutions or provide it") from None

    def __contains__(self, solution_id: str) -> bool:
        return solution_id in self.objects

    def get(self, solution_id: str, default: Any = None) -> Any:
        return self.objects.get(solution_id, default)

    def choice(self, solution_id: str) -> runtime.Choice:
        """The arm chosen for an assembled solution and the layer that chose it (a provided object has none)."""
        try:
            return self.choices[solution_id]
        except KeyError:
            raise AssemblyError(f"{solution_id!r} has no recorded choice: it was not assembled, or it was provided") from None

    def explain(self, solution_id: str) -> hierarchy.Explanation:
        """Every layer that names an arm for the solution, under the configuration this assembly was built with."""
        return self.assembler.explain(solution_id, config=self.config)

    def implementation(self, solution_id: str) -> Any:
        """The implementation class or function the solution's object was built from (not instantiated again)."""
        try:
            return self.implementations[solution_id]
        except KeyError:
            raise AssemblyError(f"{solution_id!r} has no recorded implementation: it was not assembled, or it was provided") \
                from None


@dataclass(frozen=True)
class Packaged:
    """What the package's own records or snapshot say: the default per solution, and the module per ``(solution, name)``."""
    defaults: Mapping[str, str]
    modules: Mapping[Tuple[str, str], str]
    source: str
    reasons: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)   # from overrides.csv: why a default differs from a parent's


@dataclass(frozen=True)
class Assembler:
    """Name-based resolution and assembly for the solutions one package declares.

    ``scope`` is the package's top-level name (the scope its solutions are declared under) and ``package_dir`` its folder
    (the safe-loading boundary). ``modules`` are the dotted modules of the package that declare its solutions and arms:
    ``prepare`` imports exactly these, once, before any name is checked. ``records`` is the folder holding the package's
    ``esoi.toml`` (development in a checkout); leave it out and the package default comes from ``esoi_selection.json`` in
    ``package_dir``, as an installed copy has it. Neither is ever searched for in a parent folder. ``parent`` is the Assembler
    of the package this one builds on: its solutions, names and defaults are inherited (see the module docstring).
    """
    scope: str
    package_dir: Path
    modules: Tuple[str, ...] = ()
    records: Optional[Path] = None
    parent: Optional["Assembler"] = None
    lock: Any = field(default_factory=threading.RLock, init=False, repr=False, compare=False)
    memo: Dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)
    sealed: Dict[Tuple[str, str], Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    # modules and records

    def expected_files(self, module: str) -> List[Path]:
        """The files ``module`` can be, by position under ``package_dir``: ``a/b.py`` or ``a/b/__init__.py``."""
        base = Path(self.package_dir).resolve()
        parts = module.split(".")[1:]
        if not parts:
            return [base / "__init__.py"]
        return [base.joinpath(*parts).with_suffix(".py"), base.joinpath(*parts, "__init__.py")]

    def safe_module(self, module: str) -> str:
        """A packaged record's module, or ``AssemblyError``: it must start with the scope, be plain dotted identifiers, and be a
        file that lies inside ``package_dir``. Nothing is imported to find out: only the position of the file is read."""
        parts = module.split(".") if isinstance(module, str) else []
        if not parts or parts[0] != self.scope or len(parts) < 2 or not all(p.isidentifier() for p in parts):
            raise AssemblyError(f"packaged record module {module!r} rejected: it must start with '{self.scope}.' and be plain "
                                "dotted names")
        if not any(f.is_file() for f in self.expected_files(module)):
            raise AssemblyError(f"packaged record module {module!r} rejected: its file is not inside the installed "
                                f"{self.scope} package")
        return module

    def import_arm(self, module: str) -> None:
        """Import a packaged module after ``safe_module``. Each package on the way is imported only once the file the import
        system would run is the one under ``package_dir``, so a look-alike earlier on ``sys.path`` never runs."""
        self.safe_module(module)
        parts = module.split(".")
        for end in range(1, len(parts) + 1):
            prefix = ".".join(parts[:end])
            try:
                spec = importlib.util.find_spec(prefix)
            except (ImportError, ValueError):
                spec = None
            origin = Path(spec.origin).resolve() if spec is not None and spec.origin not in (None, "built-in", "frozen") else None
            if origin is None or origin not in self.expected_files(prefix):
                raise AssemblyError(f"packaged record module {module!r} rejected: {prefix!r} would be loaded from "
                                    f"{origin or 'nowhere'}, which is not inside the installed {self.scope} package")
            try:
                importlib.import_module(prefix)
            except Exception as error:
                raise AssemblyError(f"cannot import {prefix!r} ({type(error).__name__}: {error}); remedy: install what it needs, "
                                    "or choose another implementation") from error

    def packaged(self) -> Packaged:
        """The package's own records (``records``) or snapshot, read once. A file that cannot be read is an error."""
        with self.lock:
            if "packaged" not in self.memo:
                self.memo["packaged"] = self.read_records(Path(self.records)) if self.records is not None else self.read_snapshot()
            return self.memo["packaged"]

    def read_snapshot(self) -> Packaged:
        path = Path(self.package_dir) / runtime.SNAPSHOT_NAME
        if not path.is_file():
            return Packaged({}, {}, "no records and no snapshot")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            defaults = {sid: runtime.key(entry.get("default", "")) for sid, entry in data.items() if entry.get("default")}
            modules = {(sid, runtime.key(n)): str(m) for sid, entry in data.items() for n, m in entry.get("modules", {}).items()}
        except (OSError, ValueError, AttributeError) as error:
            raise AssemblyError(f"the snapshot {path} cannot be read ({error}); remedy: regenerate it with esoi select --snapshot")\
                from error
        return Packaged(defaults, modules, "the packaged snapshot")

    def read_records(self, root: Path) -> Packaged:
        """The records of the folder ``root`` (its ``esoi.toml`` directly: no search upward, no selection table run)."""
        file = root / "esoi.toml"
        if not file.is_file():
            raise AssemblyError(f"records folder {root} has no esoi.toml; it is never looked for in a parent folder")
        try:
            cfg = config_module.load(file)
            loaded = registry_module.load(cfg)
            defaults = {r["solution_id"]: runtime.key(name) for r in loaded.every_solution()
                        if r.get("solution_id") and (name := default_name(r, loaded.implementations))}
            project = runtime.Project(config=cfg)
            modules = {}
            for row in loaded.implementations:
                sid, name = row.get("implementation_id", "").split(":", 1) if ":" in row.get("implementation_id", "") else ("", "")
                where = row.get("filepath", "").strip().split("::")[0]
                if where.endswith(".py") and name and not where.startswith(cfg.evaluation_dir + "/"):
                    modules[(sid, runtime.key(name))] = runtime.module_for(project, where)
        except Exception as error:
            raise AssemblyError(f"the records in {root} cannot be loaded ({type(error).__name__}: {error})") from error
        return Packaged(defaults, modules, "the records", hierarchy.read_overrides(cfg))

    def owned(self, target: Any) -> bool:
        """Whether a declared target is defined in the package itself (its ``__init__`` included)."""
        module = str(getattr(target, "__module__", None) or type(target).__module__)
        return module == self.scope or module.startswith(self.scope + ".")

    def seal(self) -> None:
        """Remember each arm the package itself has declared in code. A later ``runtime.register(..., replace=True)`` over
        one is then refused at load, which a plain registry cannot tell from a consumer's own arm."""
        with self.lock:
            for (scope, sid), entry in list(runtime.REGISTRY.items()):
                if scope == self.scope:
                    for name, target in list(entry.implementations.items()):
                        if not isinstance(target, str) and self.owned(target):
                            self.sealed.setdefault((sid, name), target)

    def prepare(self) -> None:
        """Import the package's declaring modules once: after this the scope knows its solution ids and the arms it declares."""
        if self.parent is not None:
            self.parent.prepare()
        with self.lock:
            if self.memo.get("prepared"):
                return
            for module in self.modules:
                self.import_arm(module)
            self.seal()
            self.memo["prepared"] = True

    # names and the cascade

    def chain(self) -> List["Assembler"]:
        """This assembler, then its parent, then the parent's parent: nearest first."""
        return [self] + (self.parent.chain() if self.parent is not None else [])

    def visible(self) -> List[str]:
        """Every solution id the scope or a parent declares."""
        self.prepare()
        return sorted({sid for one in self.chain() for scope, sid in runtime.REGISTRY if scope == one.scope})

    def known_solution(self, solution_id: str) -> bool:
        self.prepare()
        return any(scope == one.scope and sid == solution_id for one in self.chain() for scope, sid in runtime.REGISTRY)

    def check_solution(self, solution_id: str) -> str:
        check_name(solution_id, "solution id")
        if not self.known_solution(solution_id):
            raise AssemblyError(f"unknown solution {solution_id!r} in scope {self.scope!r}; available: {', '.join(self.visible()) or 'none'}")
        return solution_id

    def own_names(self, solution_id: str) -> List[str]:
        """The names this scope alone lists for a solution: declared in code, recorded, or in its snapshot."""
        entry = runtime.REGISTRY.get((self.scope, solution_id))
        found = set(entry.implementations) if entry else set()
        return sorted(found | {n for sid, n in self.packaged().modules if sid == solution_id})

    def names(self, solution_id: str) -> List[str]:
        """Every implementation name that can be chosen for a solution, in this scope or a parent."""
        self.check_solution(solution_id)
        return sorted({n for one in self.chain() for n in one.own_names(solution_id)})

    def holder(self, solution_id: str, name: str) -> "Assembler":
        """The nearest assembler of the chain that lists the name for the solution (this one when none does)."""
        return next((one for one in self.chain() if name in one.own_names(solution_id)), self)

    def declared(self, solution_id: str) -> List[str]:
        """Names the package itself (and its parents) declare for a solution: records and snapshots, and code in their own
        modules (an ``__init__`` included)."""
        found: Set[str] = set()
        for one in self.chain():
            one.prepare()
            one.seal()
            found |= {n for sid, n in one.packaged().modules if sid == solution_id} | {n for sid, n in one.sealed if sid == solution_id}
        return sorted(found)

    def module_for(self, solution_id: str, name: str) -> str:
        """The dotted module the package's own records or snapshot (or a parent's) name for an arm ('' when none)."""
        return next((m for one in self.chain() if (m := one.packaged().modules.get((solution_id, name), ""))), "")

    def selection_environ(self, config: Optional[AssemblyConfig]) -> Dict[str, str]:
        """The environment ``esoi`` is allowed to see: the config field, validated. Never the process environment. Only the
        variable of this scope and a known solution (its own or a parent's) is accepted, and its value must be a name, or
        ``name@key=value`` (a condition on the circumstances)."""
        self.prepare()
        allowed = {runtime.env_name(sid, self.scope) for sid in self.visible()}
        found = {}
        for variable, value in dict((config or AssemblyConfig()).selection_environ).items():
            if variable not in allowed:
                raise AssemblyError(f"selection_environ may not set {variable}: only {runtime.ENV_PREFIX}<SCOPE>_<SOLUTION_ID> of "
                                    f"scope {self.scope!r} is read (allowed: {', '.join(sorted(allowed)) or 'none'})")
            if value:
                try:
                    text, base, _ = hierarchy.entries(str(value))[0]
                except ValueError as error:
                    raise AssemblyError(f"selection_environ {variable}: {error}") from error
                check_name(base, f"selection_environ {variable}")
                found[variable] = text
        return found

    def reasons_for(self, solution_id: str, cfg: AssemblyConfig) -> Tuple[str, ...]:
        """The validated reasons a consumer gave for its selection of the solution (none when it gave none)."""
        if solution_id not in cfg.reasons:
            return ()
        if solution_id not in cfg.selections:
            raise AssemblyError(f"reasons are given for {solution_id!r} but selections names no arm for it; reasons say why a "
                                "selection differs from the default")
        try:
            return hierarchy.check_reasons(cfg.reasons[solution_id], f"reasons for {solution_id!r}")
        except ValueError as error:
            raise AssemblyError(str(error)) from error

    def layers(self, solution_id: str, name: Optional[str], cfg: AssemblyConfig) -> hierarchy.Explanation:
        """Every layer that names an arm for the solution, highest priority first: explicit name, consumer selections,
        selection environ, this scope's default, then each parent's default. A name that is not listed raises; a conditional
        entry whose condition does not hold stays in the list, marked skipped."""
        available = self.names(solution_id)
        variable = runtime.env_name(solution_id, self.scope)
        found: List[hierarchy.Layer] = []
        for layer, kind, given, why, source in (("explicit name", "explicit", name or cfg.names.get(solution_id), (), ""),
                                                ("consumer selections", "selections", cfg.selections.get(solution_id),
                                                 self.reasons_for(solution_id, cfg), ""),
                                                ("selection environ", "environ", self.selection_environ(cfg).get(variable), (), variable)):
            if not given:
                continue
            if not isinstance(given, (str, list, tuple)):
                check_name(given, f"{layer} for {solution_id!r}")
            try:
                parsed = hierarchy.entries(given)
            except ValueError as error:
                raise AssemblyError(f"{layer} for {solution_id!r}: {error}") from error
            for _, base, conditions in parsed:
                check_name(base, f"{layer} for {solution_id!r}")
                if base not in available:
                    raise AssemblyError(f"unknown implementation {base!r} for {solution_id!r} in scope {self.scope!r} (layer: {layer}); "
                                        f"available: {', '.join(available) or 'none'}; remedy: use one of them, or register your own "
                                        f"under a name you own with register()")
                found.append(hierarchy.Layer(layer, base, source, kind, "", ",".join(f"{k}={v}" for k, v in sorted(conditions.items())),
                                             why, hierarchy.met(conditions, cfg.circumstances)))
        for one in self.chain():
            packaged = one.packaged()
            default = packaged.defaults.get(solution_id, "")
            if default:
                broken = "" if default in available else (
                    f"error: the default {default!r} of {solution_id!r} in scope {one.scope!r} (from {packaged.source}) is "
                    f"not an implementation that can be chosen; available: {', '.join(available) or 'none'}")
                found.append(hierarchy.Layer(f"{one.scope} default", default, packaged.source, "default", one.scope, "",
                                             tuple(packaged.reasons.get(solution_id, ())), broken, one is not self))
        parent_default = next((layer.name for layer in found if layer.inherited), "")
        return hierarchy.Explanation(solution_id, tuple(found), parent_default)

    def pick(self, solution_id: str, name: Optional[str], cfg: AssemblyConfig) -> Optional[runtime.Choice]:
        """The first layer that names an arm and applies, checked against the names that can be chosen; None when no layer does."""
        for layer in self.layers(solution_id, name, cfg).layers:
            if layer.skipped.startswith("error: "):
                raise AssemblyError(layer.skipped[len("error: "):])
            if not layer.skipped:
                return runtime.Choice(layer.name, layer.layer, layer.source, layer.reasons, layer.when)
        return None

    def explain(self, solution_id: str, name: Optional[str] = None, config: Optional[AssemblyConfig] = None) -> hierarchy.Explanation:
        """One report across this scope and its parents: every layer with its value, source, condition and reasons, and the
        winner named (``str()`` of it prints the lines). The winner is what ``choice`` returns."""
        self.check_solution(solution_id)
        return self.layers(solution_id, name, config or AssemblyConfig())

    def overrides(self, config: Optional[AssemblyConfig] = None) -> List[hierarchy.Override]:
        """Each solution whose chosen arm differs from a parent's default, with the reasons recorded for it. Empty with no
        parent. ``justified`` is true when a reason is the id of a record, which an ``unconfirmed:`` marker is not."""
        cfg = config or AssemblyConfig()
        found = []
        for sid in self.visible():
            explained = self.layers(sid, None, cfg)
            won = explained.winner
            if explained.overrides_parent and won is not None:
                found.append(hierarchy.Override(sid, won.name, explained.parent_default, won.layer, won.reasons))
        return found

    def choice(self, solution_id: str, name: Optional[str] = None, config: Optional[AssemblyConfig] = None) -> runtime.Choice:
        """Which arm a solution would use now and which layer decided it (looked up when called). A name a layer supplies
        that is unknown is an error, never a fall-through."""
        self.check_solution(solution_id)
        picked = self.pick(solution_id, name, config or AssemblyConfig())
        if picked is None:
            raise AssemblyError(f"{solution_id!r} in scope {self.scope!r}: no layer names an implementation (explicit name, consumer "
                                f"selections, selection environ, package default); available: {', '.join(self.names(solution_id)) or 'none'}; "
                                f"remedy: name one, or provide your own object")
        return picked

    def load(self, solution_id: str, picked: str) -> Any:
        """The implementation object for a name. A packaged arm's module is imported here, after the safe-loading check; an
        arm the package declared is refused if something else was registered over it behind ``register``'s back."""
        self.check_solution(solution_id)
        check_name(picked, f"implementation name for {solution_id!r}")
        holder = self.holder(solution_id, picked)
        if holder is not self:
            return holder.load(solution_id, picked)
        with self.lock:
            entry = runtime.REGISTRY.get((self.scope, solution_id))
            module = self.packaged().modules.get((solution_id, picked), "")
            if module and (entry is None or picked not in entry.implementations):
                self.import_arm(module)
                self.seal()
                entry = runtime.REGISTRY.get((self.scope, solution_id))
            target = entry.implementations.get(picked) if entry else None
            if target is None:
                raise AssemblyError(f"{solution_id!r} lists {picked!r}{' (module ' + module + ')' if module else ''} but no declaration "
                                    f"of that name was found; declare it with @implementation({solution_id!r}, {picked!r})")
            if isinstance(target, str):
                raise AssemblyError(f"{picked!r} for {solution_id!r} is an import reference, which an Assembler never loads; "
                                    "register the object itself")
            sealed = self.sealed.get((solution_id, picked))
            recorded = (solution_id, picked) in self.packaged().modules
            if (sealed is not None and not same_declaration(target, sealed)) or (recorded and not self.owned(target)):
                raise AssemblyError(f"{picked!r} is declared by the {self.scope} package for {solution_id!r} but another object was "
                                    f"registered under it (runtime.register with replace=True); remedy: register your own under a "
                                    f"name you own with Assembler.register")
            return target

    def resolve(self, solution_id: str, name: Optional[str] = None, config: Optional[AssemblyConfig] = None) -> Any:
        """The chosen implementation object of a solution (a class is not instantiated), looked up when called."""
        return self.load(solution_id, self.choice(solution_id, name, config).name)

    def register(self, solution_id: str, name: str, target: Any, replace: bool = False) -> None:
        """Register an implementation (a class, a function, or an instance) under a name the consumer owns. The package's own
        names are never replaced: asking to register or replace one raises, so a consumer cannot shadow an arm by accident or
        by attack. Registered targets are trusted code of the consumer that called this; never loaded from a record, and
        never an import reference. Register through here: ``runtime.register`` skips this protection (an arm the package
        declared is then refused at load)."""
        self.check_solution(solution_id)
        check_name(name, f"registered name for {solution_id!r}")
        if isinstance(target, str):
            raise AssemblyError(f"register an object for {solution_id!r}, not the import reference {target!r}")
        with self.lock:
            if name in self.declared(solution_id):
                raise AssemblyError(f"{name!r} is declared by the {self.scope} package for {solution_id!r} and cannot be "
                                    f"{'replaced' if replace else 'registered over'}; remedy: register your own under a name you own")
            try:
                runtime.add(solution_id, name, target, None, self.scope, replace)
            except runtime.SelectionError as error:
                raise AssemblyError(str(error)) from error
            self.seal()

    # needs

    def solution_of(self, protocol: Any) -> Optional[str]:
        """The solution id a Protocol was declared for in this scope, or None."""
        self.prepare()
        for one in self.chain():
            for (scope, sid), entry in runtime.REGISTRY.items():
                if scope == one.scope and entry.interface is protocol:
                    return sid
        return None

    def needs_of(self, target: Any) -> Dict[str, str]:
        """``{parameter name: solution id}`` for each parameter typed with a solution's Protocol. An instance has none."""
        build = builder_of(target)
        if build is None:
            return {}
        try:
            hints = typing.get_type_hints(build)
        except Exception as error:   # a forward reference that does not resolve is a declaration bug: say so
            raise AssemblyError(f"cannot read the parameter types of {getattr(target, '__qualname__', target)!r}: {error}") from error
        found = {}
        for param in inspect.signature(build).parameters:
            sid = self.solution_of(hints.get(param)) if param in hints else None
            if sid:
                found[param] = sid
        return found

    def declared_needs(self, implementations: Sequence[Mapping[str, str]]) -> Tuple[Dict[str, Set[str]], List[str]]:
        """``({implementation_id: {solution ids it needs}}, findings)`` read from the constructor parameters of each recorded
        implementation. An arm that cannot be loaded (an optional dependency missing) is a finding, not an exception, and is
        left out of the first."""
        found: Dict[str, Set[str]] = {}
        findings: List[str] = []
        for row in implementations:
            iid = row["implementation_id"]
            sid, name = iid.split(":", 1) if ":" in iid else (iid, "")
            try:
                found[iid] = set(self.needs_of(self.load(sid, name)).values())
            except AssemblyError as error:
                findings.append(f"{iid}: cannot be loaded to read its needs ({error})")
        return found, findings

    def uses_problems(self, folder: Path) -> List[str]:
        """Every disagreement between the records in ``folder`` and the needs the code declares. Empty means sound."""
        rows = read_csv(Path(folder) / "implementations.csv")
        needs, findings = self.declared_needs(rows)
        return findings + problems(read_csv(Path(folder) / "solutions.csv"), rows, needs)

    def sync_uses(self, folder: Path) -> List[str]:
        """Write the ``uses_solution_ids`` column of ``implementations.csv`` in ``folder`` from the constructor parameters.
        A row whose arm cannot be loaded keeps its cell and is returned as a finding."""
        path = Path(folder) / "implementations.csv"
        rows = read_csv(path)
        needs, findings = self.declared_needs(rows)
        for row in rows:
            if row["implementation_id"] in needs:
                row["uses_solution_ids"] = ";".join(sorted(needs[row["implementation_id"]]))
        write_csv(path, read_header(path), rows)
        return findings

    # assembly

    def check_provided(self, solution_id: str, obj: Any) -> None:
        """A provided object must have every method and attribute the solution's Protocol names (presence by name, not
        signatures). When the solution has no Protocol to check against, that is an error: say so rather than accept."""
        self.check_solution(solution_id)
        protocol = next((e.interface for one in self.chain() if (e := runtime.REGISTRY.get((one.scope, solution_id))) is not None
                         and e.interface is not None), None)
        if not (inspect.isclass(protocol) and getattr(protocol, "_is_protocol", False)):
            raise AssemblyError(f"cannot check the object provided for {solution_id!r}: the solution declares no Protocol class; "
                                "remedy: declare it with @solution on a typing.Protocol class")
        missing = sorted(m for m in protocol_members(protocol) if not hasattr(obj, m))
        if missing:
            raise AssemblyError(f"the object provided for {solution_id!r} does not satisfy {protocol.__name__}: missing "
                                f"{', '.join(missing)}")

    def with_a_default(self, config: AssemblyConfig) -> List[str]:
        """Every solution of the scope that some layer names an arm for. A layer that names a broken one raises."""
        self.prepare()
        return [sid for sid in self.visible() if self.pick(sid, None, config) is not None]

    def pending_needs(self, config: AssemblyConfig, provided: Mapping[str, Any]) -> Dict[str, str]:
        """``{solution_id: one line}`` for each solution of the scope that cannot be built from defaults alone: no layer names an
        arm, the arm cannot be loaded, it needs a constructor argument that is not a solution (pass it in ``options``), or it needs
        a solution that is itself pending. A name a layer supplies that is unknown still raises: that is the caller's mistake."""
        self.prepare()
        found: Dict[str, str] = {}
        state: Dict[str, bool] = {}

        def check(sid: str) -> bool:
            if sid in state:
                return state[sid]
            state[sid] = True   # a cycle is left for assemble to name
            if sid in provided:
                return True
            picked = self.pick(sid, None, config)
            if picked is None:
                available = ", ".join(self.names(sid))
                found[sid] = (f"{sid}: no selected arm; pass arms={{{sid!r}: <one of {available}>}}" if available
                              else f"{sid}: no arm yet; pass provided={{{sid!r}: <your object>}}")
            else:
                try:
                    target = self.load(sid, picked.name)
                    needs = self.needs_of(target)
                except Exception as error:
                    found[sid] = f"{sid} ({picked.name}): cannot be loaded ({error}); install what it needs or pass provided={{{sid!r}: ...}}"
                else:
                    builder = builder_of(target)
                    options = config.options.get(sid, {})
                    missing = [name for name, par in (inspect.signature(builder).parameters.items() if builder is not None else [])
                               if name != "self" and name not in needs and name not in options and par.default is par.empty
                               and par.kind not in (par.VAR_POSITIONAL, par.VAR_KEYWORD)]
                    unmet = [need for need in needs.values() if not check(need)]
                    if missing:
                        found[sid] = f"{sid} ({picked.name}): pass options={{{sid!r}: {{{', '.join(repr(m) + ': ...' for m in missing)}}}}}"
                    elif unmet:
                        found[sid] = f"{sid} ({picked.name}): needs {', '.join(unmet)}; see those lines"
            state[sid] = sid not in found
            return state[sid]

        for sid in self.visible():
            check(sid)
        return found

    def assemble_defaults(self, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
        """Build every solution of the scope that its chosen arm (explicit name, selections, then the package default) can build
        with what was passed, and report the rest in ``Assembly.pending`` instead of raising. With no arguments this is the
        zero-configuration call; a consumer passes only what differs: ``names``/``selections`` for an arm, ``options`` for its
        arguments, ``provided`` for objects it owns."""
        cfg = config or AssemblyConfig()
        given = dict(provided or {})
        self.prepare()
        pending = self.pending_needs(cfg, given)
        wanted = tuple(sid for sid in self.visible() if sid not in pending)
        built = self.assemble(replace(cfg, solutions=wanted), given)
        return Assembly(built.assembler, built.config, {sid: (built.objects[sid], built.reason_by_solution[sid], built.choices.get(sid),
                                                           built.implementations.get(sid)) for sid in built.objects}, pending)

    def assemble(self, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
        """Build the solutions a consumer uses, in dependency order, once. A provided object wins for its solution; otherwise
        the cascade's arm is built with its needs injected and its ``options`` passed. A cycle or an unmet need fails here,
        naming the chain. The result is frozen: its choices and implementations are fixed."""
        cfg = config or AssemblyConfig()
        given = dict(provided or {})
        self.prepare()
        self.selection_environ(cfg)
        for sid in cfg.reasons:
            self.reasons_for(sid, cfg)
        for sid, obj in given.items():
            self.check_provided(sid, obj)
        built: Dict[str, Tuple[Any, str, Any, Any]] = {}

        def need_error(chain: List[Tuple[str, str]], sid: str) -> AssemblyError:
            remedy = f"remedy: pass provided={{{sid!r}: ...}} or register an arm for it"
            if not chain:
                return AssemblyError(f"{sid}: no arm, not provided; {remedy}")
            parent, arm = chain[-1]
            return AssemblyError(f"{parent} ({arm}) needs {sid}: no arm, not provided (chain: "
                                 f"{' -> '.join([p for p, a in chain] + [sid])}); {remedy}")

        def build(sid: str, chain: List[Tuple[str, str]]) -> Any:
            if sid in built:
                return built[sid][0]
            ring = [p for p, a in chain]
            if sid in ring:
                raise AssemblyError("dependency cycle: " + " -> ".join(ring[ring.index(sid):] + [sid]))
            if sid in given:
                reason = (f"{sid} -> {type(given[sid]).__name__} (layer: consumer provided, package version "
                          f"{package_version(given[sid])}, config hash {config_hash({})})")
                built[sid] = (given[sid], reason, None, None)
                return given[sid]
            picked = self.pick(sid, None, cfg)
            if picked is None:
                raise need_error(chain, sid)
            target = self.load(sid, picked.name)
            options = dict(cfg.options.get(sid, {}))
            kwargs = {param: build(need, chain + [(sid, picked.name)]) for param, need in self.needs_of(target).items()}
            if inspect.isclass(target) or inspect.isfunction(target):   # a class or factory is built; anything else is an instance
                builder = builder_of(target)
                params = inspect.signature(builder).parameters if builder is not None else {}
                extra = [k for k in options if k not in params or k in kwargs]
                if extra:
                    raise AssemblyError(f"{sid} ({picked.name}) has no option(s) {', '.join(extra)}; its parameters: "
                                        f"{', '.join(p for p in params if p != 'self' and p not in kwargs) or 'none'}")
                obj = target(**kwargs, **options)
            else:
                obj = target
            reason = (f"{sid} -> {picked.name} (layer: {picked.layer}, package version {package_version(target)}, "
                      f"config hash {config_hash(options)}{', reasons: ' + '; '.join(picked.reasons) if picked.reasons else ''})")
            built[sid] = (obj, reason, picked, target)
            return obj

        for sid in (list(cfg.solutions) or sorted(set(given) | set(self.with_a_default(cfg)))):
            self.check_solution(sid)
            build(sid, [])
        for item in built.values():
            log.info(item[1])
        return Assembly(self, cfg, built)
