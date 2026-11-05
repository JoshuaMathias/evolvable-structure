"""Depend on other solutions by name, not by import: resolve a part by a validated name, build the parts a program uses in
dependency order, and fail at startup on a cycle or a need nothing meets.

    from pathlib import Path
    from typing import Protocol
    from esoi import solution, implementation
    from esoi.runtime.assemble_by_name.assemble import Assembler
    from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig

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
``esoi`` is given, and only the variable of this scope and solution), ``AssemblyConfig.lock`` (a lock file or mapping written by
``esoi lock``, see ``esoi.runtime.implementation_selection.lock``; no lock means the latest selections), then the package default.

A package that builds on another gives ``Assembler(..., parent=other)``. The cascade then ends with the child's own default,
then the parent's (then the parent's parent's), so the child states only what differs and every solution of the parent is
visible to it; a name must be one the solution lists in the child or a parent. A layer value may be ``name@key=value`` or a
list of them: a condition on ``AssemblyConfig.circumstances``, the first entry that applies winning. ``reasons`` says why a
selection differs from a parent's default, and ``explain`` lists every layer of one solution with the winner named
(``esoi.runtime.assemble_by_name.hierarchy``; the guide is docs/how-to/hierarchical-defaults.md).

It never imports a consumer: the consumer constructs the ``Assembler`` and passes it what it owns. Standard library and ``esoi``
only. ``Assembly`` is frozen: choices and implementations are fixed when ``assemble`` returns, nothing resolves later.
``Assembler.choice`` and ``Assembler.resolve`` are lookups made when they are called.
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import threading
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from esoi.runtime.assemble_by_name import hierarchy
from esoi.runtime.assemble_by_name.environment_needs import declarations
from esoi.runtime.assemble_by_name.environment_needs.closure import Member, members_pairs
from esoi.runtime.assemble_by_name.arm_inspection import builder_of, protocol_members, same_declaration
from esoi.runtime.assemble_by_name.arm_ranking import metric_order
from esoi.runtime.assemble_by_name.assembly import Assembly
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.runtime.assemble_by_name.assembly_errors import AssemblyError
from esoi.runtime.assemble_by_name.cascade_layers import layers
from esoi.runtime.assemble_by_name.build_parts import assemble, assemble_defaults
from esoi.runtime.assemble_by_name.closure import closure
from esoi.runtime.assemble_by_name.declared_needs import declared_needs, sync_uses, uses_problems
from esoi.runtime.assemble_by_name.lazy_need import Lazy
from esoi.runtime.assemble_by_name.name_check import check_name
from esoi.runtime.assemble_by_name.packaged_records import Packaged, read_records, read_snapshot
from esoi.runtime.assemble_by_name.pending_needs import pending_needs
from esoi.runtime.implementation_selection import declare
from esoi.runtime.implementation_selection import selection_cascade
from esoi.runtime.implementation_selection import selection_registry
from esoi.runtime.implementation_selection import variants

__all__ = ["Assembler"]

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
        return read_snapshot(Path(self.package_dir))

    def read_records(self, root: Path) -> Packaged:
        """The records of the folder ``root`` (its ``esoi.toml`` directly: no search upward, no selection table run)."""
        return read_records(root)

    def metric_order(self, solution_id: str, selected: str = "") -> Tuple[List[str], Optional[float], str]:
        """``(arm names best first, lead, note)`` for a seat (see ``arm_ranking.metric_order``)."""
        return metric_order(self, solution_id, selected)

    def owned(self, target: Any) -> bool:
        """Whether a declared target is defined in the package itself (its ``__init__`` included)."""
        module = str(getattr(target, "__module__", None) or type(target).__module__)
        return module == self.scope or module.startswith(self.scope + ".")

    def seal(self) -> None:
        """Remember each arm the package itself has declared in code. A later ``runtime.register(..., replace=True)`` over
        one is then refused at load, which a plain registry cannot tell from a consumer's own arm."""
        with self.lock:
            for (scope, sid), entry in list(selection_registry.REGISTRY.items()):
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
        return sorted({sid for one in self.chain() for scope, sid in selection_registry.REGISTRY if scope == one.scope})

    def known_solution(self, solution_id: str) -> bool:
        self.prepare()
        return any(scope == one.scope and sid == solution_id for one in self.chain() for scope, sid in selection_registry.REGISTRY)

    def check_solution(self, solution_id: str) -> str:
        check_name(solution_id, "solution id")
        if not self.known_solution(solution_id):
            raise AssemblyError(f"unknown solution {solution_id!r} in scope {self.scope!r}; available: {', '.join(self.visible()) or 'none'}")
        return solution_id

    def own_names(self, solution_id: str) -> List[str]:
        """The names this scope alone lists for a solution: declared in code, recorded, or in its snapshot."""
        entry = selection_registry.REGISTRY.get((self.scope, solution_id))
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
        allowed = {selection_cascade.env_name(sid, self.scope) for sid in self.visible()}
        found = {}
        for variable, value in dict((config or AssemblyConfig()).selection_environ).items():
            if variable not in allowed:
                raise AssemblyError(f"selection_environ may not set {variable}: only {selection_registry.ENV_PREFIX}<SCOPE>_<SOLUTION_ID> of "
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
        """Every layer that names an arm for the solution, highest priority first (see ``cascade_layers.layers``)."""
        return layers(self, solution_id, name, cfg)


    def pick(self, solution_id: str, name: Optional[str], cfg: AssemblyConfig) -> Optional[selection_registry.Choice]:
        """The first layer that names an arm and applies, checked against the names that can be chosen; None when no layer does."""
        for layer in self.layers(solution_id, name, cfg).layers:
            if layer.skipped.startswith("error: "):
                raise AssemblyError(layer.skipped[len("error: "):])
            if not layer.skipped:
                return selection_registry.Choice(layer.name, layer.layer, layer.source, layer.reasons, layer.when)
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

    def choice(self, solution_id: str, name: Optional[str] = None, config: Optional[AssemblyConfig] = None) -> selection_registry.Choice:
        """Which arm a solution would use now and which layer decided it (looked up when called). A name a layer supplies
        that is unknown is an error, never a fall-through."""
        self.check_solution(solution_id)
        picked = self.pick(solution_id, name, config or AssemblyConfig())
        if picked is None:
            raise AssemblyError(f"{solution_id!r} in scope {self.scope!r}: no layer names an implementation (explicit name, consumer "
                                f"selections, selection environ, lock, package default); available: {', '.join(self.names(solution_id)) or 'none'}; "
                                f"remedy: name one, or provide your own object")
        return picked

    def load(self, solution_id: str, picked: str) -> Any:
        """The implementation object for a name. A packaged arm's module is imported here, after the safe-loading check; an
        arm the package declared is refused if something else was registered over it behind ``register``'s back."""
        self.check_solution(solution_id)
        picked = variants.base_of(picked)    # a variant (arm@option=value) loads its base arm; build() passes the options
        check_name(picked, f"implementation name for {solution_id!r}")
        holder = self.holder(solution_id, picked)
        if holder is not self:
            return holder.load(solution_id, picked)
        with self.lock:
            entry = selection_registry.REGISTRY.get((self.scope, solution_id))
            module = self.packaged().modules.get((solution_id, picked), "")
            if module and (entry is None or picked not in entry.implementations):
                self.import_arm(module)
                self.seal()
                entry = selection_registry.REGISTRY.get((self.scope, solution_id))
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
                                    f"registered under it (declare.register with replace=True); remedy: register your own under a "
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
                selection_registry.add(solution_id, name, target, None, self.scope, replace)
            except selection_registry.SelectionError as error:
                raise AssemblyError(str(error)) from error
            self.seal()

    # needs

    def solution_of(self, protocol: Any) -> Optional[str]:
        """The solution id a Protocol was declared for in this scope, or None."""
        self.prepare()
        for one in self.chain():
            for (scope, sid), entry in selection_registry.REGISTRY.items():
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
            hint = hints.get(param)
            if typing.get_origin(hint) is Lazy:    # Lazy[Protocol] is the need of Protocol, built on first use
                hint = typing.get_args(hint)[0]
            sid = self.solution_of(hint) if param in hints else None
            if sid:
                found[param] = sid
        return found

    def lazy_needs_of(self, target: Any) -> Set[str]:
        """The parameter names of ``target`` annotated ``Lazy[...]`` (a subset of ``needs_of``'s keys)."""
        build = builder_of(target)
        if build is None:
            return set()
        try:
            hints = typing.get_type_hints(build)
        except Exception:
            return set()
        return {param for param, hint in hints.items() if typing.get_origin(hint) is Lazy}

    def declared_needs(self, implementations: Sequence[Mapping[str, str]]) -> Tuple[Dict[str, Set[str]], List[str]]:
        """``({implementation_id: {solution ids it needs}}, findings)`` (see ``declared_needs.declared_needs``)."""
        return declared_needs(self, implementations)

    def uses_problems(self, folder: Path) -> List[str]:
        """Every disagreement between the records in ``folder`` and the needs the code declares. Empty means sound."""
        return uses_problems(self, folder)

    def sync_uses(self, folder: Path) -> List[str]:
        """Write the ``uses_solution_ids`` column of ``implementations.csv`` in ``folder`` from the constructor parameters."""
        return sync_uses(self, folder)

    # assembly

    def check_provided(self, solution_id: str, obj: Any) -> None:
        """A provided object must have every method and attribute the solution's Protocol names (presence by name, not
        signatures). When the solution has no Protocol to check against, that is an error: say so rather than accept."""
        self.check_solution(solution_id)
        protocol = next((e.interface for one in self.chain() if (e := selection_registry.REGISTRY.get((one.scope, solution_id))) is not None
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
        """``{solution_id: one line}`` for each solution that cannot be built from defaults alone (see ``pending_needs.pending_needs``)."""
        return pending_needs(self, config, provided)

    def closure(self, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None,
                solutions: Sequence[str] = (), every_arm: bool = False) -> List[Member]:
        """The dependency closure of what an assembly would use, each member with the reason it is in (see ``closure.closure``)."""
        return closure(self, config, provided, solutions, every_arm)

    def requirements(self, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None,
                     every_arm: bool = False, solutions: Sequence[str] = ()) -> List[declarations.Entry]:
        """What the closure declares it needs from its environment (see ``closure``): the arms an assembly would use, the arms
        that fill their needs, and the package modules each imports, each requirement once with its users."""
        return declarations.gather(members_pairs(self.closure(config, provided, solutions, every_arm)))

    def assemble_defaults(self, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
        """Build every solution its chosen arm can build with what was passed, and report the rest in ``Assembly.pending``."""
        return assemble_defaults(self, config, provided)

    def assemble(self, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
        """Build the solutions a consumer uses, in dependency order, once; the result is frozen (see ``build_parts.assemble``)."""
        return assemble(self, config, provided)
