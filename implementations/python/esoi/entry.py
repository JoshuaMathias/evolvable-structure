"""One line for any solution or intent: ``run(id, input)`` returns what that solution or intent is for.

The same call works at every level of a project's hierarchy, because every level is reached through a declared interface:

    import hubofhubs
    hubofhubs.run("card-store", "rust release")       # a leaf: the store's answer to the query
    hubofhubs.run("remember-and-recall", "rust")      # a container: its composition arm's answer
    hubofhubs.run("hub-of-hubs", "latest Rust?")      # the whole repository: its top intent's root solution

A package exposes ``run = esoi.entry.runner(<its Assembler>)``; ``esoi.run`` is the same function bound to esoi's own solutions.
``run`` also takes an interface class declared with ``@solution``: ``run(CardStore)`` returns the ready handle, typed as that
Protocol, so an editor or a type checker knows its methods.
What comes back depends on the solution's declared kind (``@solution(id, kind=..., entry=...)``, see ``esoi.runtime``):

- ``event``: the output of the entry method for the input (a search, an answer, a routing);
- ``evaluate``: the entry's feedback or score on the artifact passed as input (a check, a judge, a guard);
- ``store``: with no input, the ready handle (a database, a card store, an index); with an input, the entry's answer to it.

An intent is reached through its root solution (the one solution of the intent that nothing inside it uses, on the selected
implementations); a sub-intent with several roots is reached as the implementation of its parent's solution that it is.
Every seat is filled from the records (the arm the metric selected); keywords override only what differs (``arms``,
``options``, ``provided``, ``lock``). ``environ`` defaults to the process environment. A seat that cannot run until something is
set raises ``Pending``, whose lines (and structured ``reasons``) name exactly what to set; nothing is attempted. Standard library and ``esoi`` only.
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Type, TypeVar, overload

from . import runtime

__all__ = ["EntryError", "Pending", "Reason", "Runner", "Target", "run", "runner", "targets", "describe"]

ANSWERING = ("ok", "pending-key", "pending-install")   # the outcomes that count as the one line answering
OUTCOMES = ("ok", "pending-key", "pending-install", "needs-option", "load-error", "live-attempt", "no-entry", "fail")
INTENT_KEY = "@intents"   # where esoi_selection.json keeps the intent map (see ``intent_map``)


class EntryError(LookupError):
    """The id names nothing reachable, or what it names declares no entry; the message says what to declare. ``code`` is
    ``no-entry`` when the cause is a missing declaration, else ``fail``."""

    def __init__(self, message: str, code: str = "fail"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Reason:
    """One blocked seat and what it needs: ``kind`` is ``key`` (a variable or account), ``install`` (a package or a program),
    ``option`` (a constructor argument to pass), ``provided`` (no arm: pass your own object), ``load`` (the arm cannot be
    imported) or ``needs`` (it waits on another seat, which has its own reason)."""
    seat: str
    arm: str
    kind: str
    need: str
    waits: Tuple[str, ...] = ()   # for kind "needs": the seats it waits on, whose own reasons settle it


class Pending(RuntimeError):
    """The solution cannot run until the caller sets something. ``lines`` name each key, install or option, one per seat;
    ``reasons`` carry the same as structured ``Reason`` records, so nothing has to read the text."""

    def __init__(self, solution_id: str, lines: Sequence[str], reasons: Sequence[Reason] = ()):
        self.solution_id, self.lines, self.reasons = solution_id, tuple(lines), tuple(reasons)
        super().__init__(f"{solution_id} cannot run yet: " + " | ".join(self.lines))


@dataclass(frozen=True)
class Target:
    """What one id reaches: the solution whose entry runs, the arm forced for it (a sub-intent is one arm), and the level."""
    id: str
    solution_id: str
    level: str          # "solution" or "intent"
    arm: str = ""


def process_environment() -> Mapping[str, str]:
    """The one place this module reads the process environment: the entry function's default ``environ``."""
    return os.environ


def records_root(assembler: Any) -> Optional[Path]:
    """The folder holding the package's ``esoi.toml``: the Assembler's ``records``, else a checkout beside the package."""
    if getattr(assembler, "records", None) is not None:
        return Path(assembler.records)
    for base in (Path(assembler.package_dir).parent, Path(assembler.package_dir).parent.parent):
        if (base / "esoi.toml").is_file():
            return base
    return None


def tree(root: Path) -> Tuple[Dict[str, Any], Dict[str, Dict[str, str]], List[Dict[str, str]]]:
    """``(intents by id, solutions by id, implementations)`` of the project at ``root``."""
    from . import config as config_module
    from . import intents as intents_module
    from .tables import read_csv
    cfg = config_module.load(root / "esoi.toml")
    found = {i.intent_id: i for i in intents_module.discover(cfg)}
    solutions: Dict[str, Dict[str, str]] = {}
    implementations: List[Dict[str, str]] = []
    for intent_id, folder in intents_module.folders(cfg):
        for row in read_csv(folder / "solutions.csv"):
            solutions[row["solution_id"]] = dict(row, intent_id=intent_id)
        implementations += read_csv(folder / "implementations.csv")
    return found, solutions, implementations


def selected_uses(solutions: Mapping[str, Mapping[str, str]], implementations: Sequence[Mapping[str, str]]) -> Dict[str, List[str]]:
    from .select import default_name
    from .tables import ids
    out: Dict[str, List[str]] = {}
    for sid, row in solutions.items():
        chosen = runtime.key(default_name(row, list(implementations)) or "")
        record = next((r for r in implementations if r.get("solution_id") == sid
                       and runtime.key(r["implementation_id"].split(":", 1)[-1]) == chosen), {})
        out[sid] = [t for t in ids(record.get("uses_solution_ids", "")) if t != sid]
    return out


def intent_target(intent_id: str, root: Path) -> Target:
    """The solution an intent's one line runs: its single root, else the parent solution with the arm the intent is."""
    found, solutions, implementations = tree(root)
    intent = found[intent_id]
    mine = sorted(s for s, r in solutions.items() if r["intent_id"] == intent_id)
    uses = selected_uses(solutions, implementations)
    used = {t for s in mine for t in uses[s] if t in mine}
    roots = [s for s in mine if s not in used]
    if len(roots) == 1:
        return Target(intent_id, roots[0], "intent")
    implements = (intent.row.get("implements") or "").strip()
    if implements and ":" in implements and not implements.startswith("@"):
        sid, arm = implements.split(":", 1)
        return Target(intent_id, sid, "intent", arm)
    raise EntryError(f"intent {intent_id} has {len(roots)} root solutions ({', '.join(roots) or 'none'}) and implements no local "
                     "solution, so no one solution is its entry; give it one root (metric-solution-coherence reports it)")


def intent_map(root: Path, scope: str) -> Dict[str, Any]:
    """What an installed package needs to answer ``run(<intent id>)`` without its records: for each intent its root solution (or
    the parent solution and arm it is), and the scope of each solution id. ``esoi select --snapshot`` writes it."""
    found, solutions, _ = tree(root)
    intents: Dict[str, Dict[str, str]] = {}
    for iid in sorted(found):
        try:
            where = intent_target(iid, root)
        except EntryError:
            continue
        intents[iid] = {"root": where.solution_id, "arm": where.arm}
    return {"intents": intents, "scopes": {sid: scope for sid in sorted(solutions)}}


def snapshot(config: Any) -> Dict[str, Any]:
    """``runtime.snapshot`` plus, under ``"@intents"``, the intent map: what an installed package needs to answer
    ``run("<intent id>")`` without its records. ``esoi select --snapshot`` writes this."""
    out = runtime.snapshot(config)
    try:
        if config.intent_mode:
            out[INTENT_KEY] = intent_map(config.root, config.package or "")
    except Exception:
        pass   # a snapshot without the intent map still serves every solution id
    return out


def packaged_map(assembler: Any) -> Optional[Dict[str, Any]]:
    """The intent map in the ``esoi_selection.json`` beside an installed package, or None."""
    try:
        data = json.loads((Path(assembler.package_dir) / runtime.SNAPSHOT_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    found = data.get(INTENT_KEY) if isinstance(data, dict) else None
    return found if isinstance(found, dict) else None


def locate(assembler: Any, target: str) -> Target:
    """A solution id the Assembler (or a parent) knows, or an intent id of the package's records or packaged intent map."""
    assembler.prepare()
    if assembler.known_solution(target) or any(runtime.REGISTRY.get((one.scope, target)) for one in assembler.chain()):
        return Target(target, target, "solution")
    for one in assembler.chain():
        root = records_root(one)
        if root is None:
            packaged = packaged_map(one) or {}
            if target in packaged.get("intents", {}):
                info = packaged["intents"][target]
                return Target(target, info["root"], "intent", info.get("arm", ""))
            if target in packaged.get("scopes", {}):
                return Target(target, target, "solution")
            continue
        found, solutions, _ = tree(root)
        if target in found:
            return intent_target(target, root)
        if target in solutions:
            return Target(target, target, "solution")
    raise EntryError(f"{target!r} is neither a solution nor an intent of {assembler.scope}"
                     + "".join(f" or {p.scope}" for p in assembler.chain()[1:]))


def declared(assembler: Any, solution_id: str) -> Optional[runtime.Entry]:
    for one in assembler.chain():
        found = runtime.REGISTRY.get((one.scope, solution_id))
        if found is not None and found.interface is not None:
            return found
    return None


def solution_of(assembler: Any, interface: Any) -> str:
    """The solution id an interface class (or function) was declared with ``@solution`` for."""
    for one in assembler.chain():
        for (scope, sid), entry in runtime.REGISTRY.items():
            if scope == one.scope and entry.interface is interface:
                return sid
    raise EntryError(f"{getattr(interface, '__name__', interface)!r} is not declared with @solution in {assembler.scope} or its "
                     "parents", code="no-entry")


# What keeps a seat from being built, as structured reasons.

def unmet_checks(target: Any, environ: Mapping[str, str], options: Mapping[str, Any]) -> List[Any]:
    """The unmet required requirements of one arm that nothing the caller passed fills. A program is looked up on the PATH of
    ``environ`` (no PATH, no program), so ``environ={}`` never finds, and never starts, one."""
    from . import requirements as req
    out = []
    for one in req.check(req.declared(target), environ):
        item = one.requirement
        if isinstance(item, req.Binary):
            found = shutil.which(item.name, path=environ.get("PATH", ""))
            one = req.Check(item, req.MET if found else req.UNMET,
                            "" if found else (item.install_hint or f"install {item.name} and put it on PATH"))
        if isinstance(item, req.Env) and item.option in options:
            continue
        if isinstance(item, req.Api) and item.key is not None and item.key.option in options:
            continue
        if one.blocking:
            out.append(one)
    return out


def reason_of(seat: str, arm: str, one: Any) -> Reason:
    from . import requirements as req
    kind = "key" if isinstance(one.requirement, (req.Env, req.Api)) else "install"
    return Reason(seat, arm, kind, one.remedy)


def seat_reasons(assembler: Any, sid: str, cfg: Any, line: str) -> List[Reason]:
    """Why one pending seat cannot be built, by category, read from the arm itself (not from the pending line)."""
    from .assemble import builder_of, environ_lacking
    picked = assembler.pick(sid, None, cfg)
    if picked is None:
        return [Reason(sid, "", "provided", line)]
    try:
        target = assembler.load(sid, picked.name)
        needs = assembler.needs_of(target)
    except Exception:
        return [Reason(sid, picked.name, "load", line)]
    given = cfg.options.get(sid, {})
    out: List[Reason] = []
    if environ_lacking(target, given, cfg.consumer_environ):
        out.append(Reason(sid, picked.name, "key", line))
    out += [reason_of(sid, picked.name, one) for one in unmet_checks(target, cfg.consumer_environ, given)]
    builder = builder_of(target)
    for name, par in (inspect.signature(builder).parameters.items() if builder is not None else []):
        if name != "self" and name not in needs and name not in given and par.default is par.empty \
                and par.kind not in (par.VAR_POSITIONAL, par.VAR_KEYWORD) and not out:
            out.append(Reason(sid, picked.name, "option", line))
            break
    lazy = assembler.lazy_needs_of(target)     # a Lazy need is built on first use, so the seat does not wait on it
    return out or [Reason(sid, picked.name, "needs", line, tuple(need for param, need in needs.items() if param not in lazy))]


def blockers(assembler: Any, cfg: Any, pending: Mapping[str, str], sid: str, given: Mapping[str, Any]) -> Tuple[List[str], List[Reason]]:
    """Every line and structured reason that keeps ``sid`` from running: the pending seats it reaches, and, for the arms that
    would be built, each unmet key, install or program."""
    lines: List[str] = []
    reasons: List[Reason] = []
    if sid in pending:
        seen: List[str] = []
        queue = [sid]
        while queue:
            seat = queue.pop(0)
            if seat in seen or seat not in pending:
                continue
            seen.append(seat)
            lines.append(pending[seat])
            reasons += seat_reasons(assembler, seat, cfg, pending[seat])
            queue += [other for other in pending if other in pending[seat]]
        return lines, reasons
    for member in assembler.closure(cfg, given, solutions=(sid,)):
        seat, _, arm = member.label.partition(":")
        found = unmet_checks(member.target, cfg.consumer_environ, cfg.options.get(seat, {}))
        if found:
            lines.append(f"{seat} ({arm}): " + "; ".join(dict.fromkeys(one.remedy for one in found if one.remedy)))
            reasons += [reason_of(seat, arm, one) for one in found]
    return lines, reasons


def prepare(assembler: Any, target: str, environ: Optional[Mapping[str, str]], arms: Optional[Mapping[str, str]]):
    env = process_environment() if environ is None else environ
    where = locate(assembler, target)
    chosen = dict(arms or {})
    if where.arm:
        chosen.setdefault(where.solution_id, where.arm)
    return env, where.solution_id, chosen


def build_handle(assembler: Any, sid: str, env: Mapping[str, str], chosen: Mapping[str, str], options: Optional[Mapping[str, Any]],
                 provided: Optional[Mapping[str, Any]], lock: Any) -> Any:
    """The ready handle of a solution built from the selected arms, or ``Pending`` naming what to set."""
    from .assemble import AssemblyConfig
    cfg = AssemblyConfig(selections=dict(chosen), options=dict(options or {}), consumer_environ=dict(env), lock=lock)
    given = dict(provided or {})
    pending = assembler.pending_needs(cfg, given)          # what nothing can build yet, each with the line saying why
    lines, reasons = blockers(assembler, cfg, pending, sid, given)
    if lines:
        raise Pending(sid, lines, reasons)
    system = assembler.assemble(replace(cfg, solutions=(sid,)), given)    # only the target and what it needs
    return system[sid]


def run(target: Any, input: Any = None, *, assembler: Any, environ: Optional[Mapping[str, str]] = None,
        arms: Optional[Mapping[str, str]] = None, options: Optional[Mapping[str, Any]] = None,
        provided: Optional[Mapping[str, Any]] = None, lock: Any = None) -> Any:
    """Run the solution or intent ``target`` on ``input`` and return what its declared kind returns (module docstring). Given an
    interface class declared with ``@solution`` instead of an id, return the ready handle. Packages bind ``assembler`` with
    ``runner``; callers write ``<package>.run(id, input)``."""
    handle_only = not isinstance(target, str)
    env, sid, chosen = prepare(assembler, solution_of(assembler, target) if handle_only else target, environ, arms)
    entry = declared(assembler, sid)
    if entry is None:
        raise EntryError(f"{sid} declares no interface: declare it with @solution({sid!r}, kind=..., entry=...) on a Protocol or "
                         "a function where it lives (rule S37)", code="no-entry")
    if handle_only:
        return build_handle(assembler, sid, env, chosen, options, provided, lock)
    if not inspect.isclass(entry.interface):     # a function solution is its own entry
        scope = next(one.scope for one in assembler.chain() if runtime.REGISTRY.get((one.scope, sid)) is entry)
        if input is None and entry.example is None:
            raise EntryError(f"{sid} takes an input")
        return call_entry(runtime.resolve(sid, chosen.get(sid), environ=env, scope=scope), input)
    if not entry.kind or not entry.entry:
        raise EntryError(f"{sid} declares no kind or entry: add kind=\"event\"|\"evaluate\"|\"store\" and entry=\"<method>\" to its "
                         f"@solution on {entry.interface.__name__} (rule S37)", code="no-entry")
    handle = build_handle(assembler, sid, env, chosen, options, provided, lock)
    if entry.kind == "store" and input is None:
        return handle
    if entry.kind == "evaluate" and input is None:
        raise EntryError(f"{sid} evaluates an artifact: pass it as the input (for example {entry.example!r})")
    return call_entry(getattr(handle, entry.entry), input)


def call_entry(method: Callable[..., Any], input: Any) -> Any:
    """Pass the input as the entry's one argument. A mapping whose keys are all parameter names of the entry, when the entry
    takes more than one parameter, goes in as keywords instead (``{"goal": ..., "brief": ...}``). Read from the signature only."""
    if isinstance(input, Mapping) and input:
        params = {p.name for p in inspect.signature(method).parameters.values()
                  if p.name != "self" and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)}
        if len(params) > 1 and set(input) <= params:
            return method(**input)
    return method(input)


Interface = TypeVar("Interface")


class Runner:
    """``run`` bound to one package's Assembler. ``run(id, input=None, **overrides)`` runs an id; ``run(CardStore)`` with an interface
    class declared by ``@solution`` returns the ready handle, typed as that class."""

    def __init__(self, assembler: Any):
        self.assembler = assembler
        self.__name__ = "run"
        self.__doc__ = run.__doc__

    @overload
    def __call__(self, target: Type[Interface], input: Any = None, **overrides: Any) -> Interface: ...

    @overload
    def __call__(self, target: str, input: Any = None, **overrides: Any) -> Any: ...

    def __call__(self, target: Any, input: Any = None, **overrides: Any) -> Any:
        return run(target, input, assembler=self.assembler, **overrides)


def runner(assembler: Any) -> Runner:
    """``run`` bound to one package's Assembler: ``hubofhubs.run = esoi.entry.runner(HUB)``."""
    return Runner(assembler)


def targets(assembler: Any) -> List[Tuple[str, str, str, Any]]:
    """Every id the package's one line can be called with: ``(id, level, kind, example)`` for each solution of its records or
    packaged intent map (own scope only) and each intent. ``kind`` is empty where no interface is declared yet."""
    assembler.prepare()
    root = records_root(assembler)
    out: List[Tuple[str, str, str, Any]] = []

    def row(ident: str, level: str, sid: str) -> Tuple[str, str, str, Any]:
        entry = declared(assembler, sid)
        return (ident, level, (entry.kind if entry is not None else "") or "", entry.example if entry is not None else None)
    if root is None:
        packaged = packaged_map(assembler) or {}
        out += [row(sid, "solution", sid) for sid in sorted(s for s, scope in packaged.get("scopes", {}).items() if scope == assembler.scope)]
        out += [row(iid, "intent", info["root"]) for iid, info in sorted(packaged.get("intents", {}).items())]
        return out
    found, solutions, _ = tree(root)
    out += [row(sid, "solution", sid) for sid in sorted(solutions)]
    for iid in sorted(found):
        try:
            out.append(row(iid, "intent", intent_target(iid, root).solution_id))
        except EntryError:
            out.append((iid, "intent", "", None))
    return out


def describe(value: Any, limit: int = 3) -> str:
    """A short printable form of an entry's result, for the README and the metric's report."""
    if isinstance(value, (list, tuple)):
        head = [describe(v, 0) for v in value[:limit]]
        return f"{len(value)} item(s)" + (": " + "; ".join(head) if head else "")
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{k}: {str(v)[:40]}" for k, v in list(value.items())[:limit]) + "}"
    text = str(value)
    return text if len(text) <= 160 else text[:157] + "..."


def own_runner() -> Runner:
    """``run`` bound to esoi's own solutions (``esoi.interfaces``), with this checkout's records when there is one."""
    from .assemble import Assembler
    package = Path(__file__).resolve().parent
    root = package.parents[2] if (package.parents[2] / "esoi.toml").is_file() else None
    return runner(Assembler("esoi", package, modules=("esoi.interfaces", "esoi.spec_index", "esoi.spec_search", "esoi.evidence"), records=root))


# The first-stage check of the one line (rule S37) and of the README's example: offline, no model.

LOCAL_PROGRAMS = ("git",)   # the one program the offline check lets an entry start: reading the repository's own files


class Offline(RuntimeError):
    """Raised inside the check when an entry tries the network or starts a program no declared requirement predicted."""


def offline_guard() -> None:
    """Block sockets and child processes for the rest of this process (the check runs in its own process, which exits after
    reporting)."""
    import socket
    import subprocess

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise Offline("needs the network or a program (blocked in the offline check)")
    socket.socket.connect = refuse          # type: ignore[assignment]
    socket.create_connection = refuse       # type: ignore[assignment]
    allowed = subprocess.Popen.__init__

    def local_only(self: Any, args: Any, *rest: Any, **kwargs: Any) -> Any:
        program = Path(str(args[0] if isinstance(args, (list, tuple)) else str(args).split()[0])).name
        if program not in LOCAL_PROGRAMS:
            refuse()
        return allowed(self, args, *rest, **kwargs)
    subprocess.Popen.__init__ = local_only  # type: ignore[assignment]
    os.system = refuse                      # type: ignore[assignment]


def project_runner(root: Path) -> Callable[..., Any]:
    """The one-line entry of the project at ``root``: its package's ``run`` (bound by ``runner``), else its ``assembler()``,
    else an Assembler over the package's records; esoi's own repository uses ``esoi.run``."""
    import sys
    from . import config as config_module
    cfg = config_module.load(root / "esoi.toml")
    for extra in reversed([str(root / p) for p in (cfg.python_path or ["."])]):
        if extra not in sys.path:
            sys.path.insert(0, extra)
    if cfg.package == "esoi":
        return own_runner()
    module = importlib.import_module(cfg.package)
    bound = getattr(module, "run", None)
    if callable(bound) and getattr(bound, "assembler", None) is not None:
        return bound
    if callable(getattr(module, "assembler", None)):
        return runner(module.assembler())
    from .assemble import Assembler
    return runner(Assembler(cfg.package, root / cfg.package_dir, records=root))


def chain_of_errors(error: BaseException) -> List[BaseException]:
    out: List[BaseException] = []
    while error is not None and error not in out:
        out.append(error)
        error = error.__cause__ or error.__context__
    return out


def pending_outcome(reasons: Sequence[Reason]) -> str:
    """The outcome of a ``Pending`` read from its reasons by their leaves: a ``needs`` reason is settled by the reasons of the seats it
    waits on, so the result is the worst leaf (load-error, then needs-option for an option or an object to pass, then
    pending-install, then pending-key). The leaves are found through any chain of ``needs`` reasons. A ``needs`` with no leaf
    under it is needs-option."""
    settled = {one.seat for one in reasons if one.kind != "needs"}      # seats that end in a leaf
    grown = True
    while grown:    # a needs reason is settled once a seat it waits on is: a leaf, or a needs reason that is itself settled
        grown = False
        for one in reasons:
            if one.kind == "needs" and one.seat not in settled and any(seat in settled for seat in one.waits):
                settled.add(one.seat)
                grown = True
    kinds = set()
    for one in reasons:
        if one.kind != "needs":
            kinds.add(one.kind)
        elif one.seat not in settled:
            kinds.add("option")
    if "load" in kinds:
        return "load-error"
    if kinds & {"option", "provided"}:
        return "needs-option"
    if "install" in kinds:
        return "pending-install"
    if "key" in kinds:
        return "pending-key"
    return "needs-option"   # pending for a reason nothing declares: the default does not fill the seat


def classify(error: BaseException) -> Tuple[str, str, List[Reason]]:
    """``(outcome, detail, reasons)`` of an entry that raised, read from the exception's type and structured reasons."""
    from .assemble import AssemblyError
    from .runtime import SelectionError
    if isinstance(error, Pending):
        outcome = pending_outcome(error.reasons)
        detail = " | ".join(error.lines)
        return outcome, detail, list(error.reasons)
    if any(isinstance(one, Offline) for one in chain_of_errors(error)):
        return "live-attempt", "tried the network or a program that no declared requirement named", []
    if isinstance(error, EntryError) and error.code == "no-entry":
        return "no-entry", str(error), []
    if isinstance(error, (AssemblyError, SelectionError, ImportError)):
        return "load-error", f"{type(error).__name__}: {error}"[:300], []
    return "fail", f"{type(error).__name__}: {error}"[:300], []


def check_entries(root: Path) -> List[Dict[str, Any]]:
    """Call every id of the project's one line with its example under ``environ={}`` and no network: one row per id with
    ``outcome``: ok (a value of the declared kind came back), pending-key or pending-install (it named the key or install that
    would let it run), needs-option (it asks the caller for an option or an object: no default fills the seat), load-error (an
    arm cannot be loaded), live-attempt (it reached for the network or a program nothing declared), no-entry (no interface,
    kind, entry or example) or fail (it raised anything else). Only the first three answer."""
    os.environ["ESOI_IN_ENTRY_CHECK"] = "1"   # an entry that runs `esoi check` does not start this check again (rule S37)
    offline_guard()
    run_one = project_runner(root)
    out: List[Dict[str, Any]] = []
    for target, level, kind, example in targets(run_one.assembler):
        row: Dict[str, Any] = {"id": target, "level": level, "kind": kind, "reasons": []}
        if not kind or example is None:
            row.update(outcome="no-entry", detail="declare kind=, entry= and example= on its @solution" if not kind else "no example input")
        else:
            try:
                value = run_one(target, example, environ={})
                if kind == "store" and value is None:
                    raise EntryError("a store's query returned None")
                row.update(outcome="ok", detail=describe(value))
            except Exception as error:
                outcome, detail, reasons = classify(error)
                row.update(outcome=outcome, detail=detail, reasons=[vars(r) for r in reasons])
        out.append(row)
    return out


# The README's example (rule S37): the first fenced block that calls ``<package>.run(`` runs as written.

def readme_block(root: Path) -> Tuple[str, str, List[str]]:
    """``(block text, entry name, problems)``: the first ``pycon`` or ``python`` block with ``>>>`` lines that calls the entry."""
    import re as regex
    from . import config as config_module
    cfg = config_module.load(root / "esoi.toml")
    name = "esoi.run" if cfg.package == "esoi" else f"{cfg.package}.run"
    readme = root / "README.md"
    if not readme.is_file():
        return "", name, ["README.md: missing"]
    blocks = regex.findall(r"```(?:python|pycon)\n(.*?)```", readme.read_text(encoding="utf-8"), flags=regex.S)
    block = next((b for b in blocks if ">>>" in b and f"{name}(" in b), None)
    if block is None:
        return "", name, [f"README.md: no fenced example with >>> lines that calls {name}(...)"]
    return block, name, []


def run_block(block: str, label: str = "README.md", guard: bool = True) -> Dict[str, List[str]]:
    """Run a doctest-style block in this process, offline. Each ``>>>`` line's printed output must match the lines under it. An
    example that raises ``Pending`` whose reasons are only keys or installs is pending (its shown output is proven by the
    installed stage, not here), and so is every example after it. Any other mismatch or error is a problem. ``guard`` blocks the
    network and programs for the rest of this process, so only a process meant to exit after reporting passes True."""
    import contextlib
    import doctest
    import io
    import traceback
    if guard:
        offline_guard()
    parser, checker = doctest.DocTestParser(), doctest.OutputChecker()
    flags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
    examples = parser.get_examples(block)
    names: Dict[str, Any] = {}
    problems: List[str] = []
    pending: List[str] = []
    for index, example in enumerate(examples):
        buffer = io.StringIO()
        raised: Optional[BaseException] = None
        with contextlib.redirect_stdout(buffer):
            try:
                exec(compile(example.source, label, "single"), names)
            except BaseException as error:   # noqa: BLE001  the example's own failure is the finding
                raised = error
        if raised is None:
            if example.exc_msg is not None:
                problems.append(f"{label}: `{example.source.strip()}` was shown raising an error, but it returned")
                break
            if not checker.check_output(example.want, buffer.getvalue(), flags):
                problems.append(f"{label}: `{example.source.strip()}` prints {buffer.getvalue().strip()!r}, not {example.want.strip()!r}")
                break
            continue
        if isinstance(raised, Pending) and raised.reasons and pending_outcome(raised.reasons) in ("pending-key", "pending-install"):
            pending.append(f"{label}: `{example.source.strip()}` is pending ({'; '.join(raised.lines)[:200]})")
            pending += [f"{label}: `{rest.source.strip()}` pending after it" for rest in examples[index + 1:]]
            break
        text = "".join(traceback.format_exception_only(type(raised), raised))
        if example.exc_msg is not None and checker.check_output(example.exc_msg, text, flags):
            continue
        problems.append(f"{label}: `{example.source.strip()}` raised {type(raised).__name__}: {str(raised)[:200]}")
        break
    return {"problems": problems, "pending": pending}


def installed_readme(root: Path, block: str) -> List[str]:
    """Build the project's wheel (``pip wheel --no-deps --no-build-isolation``), install it into a temporary virtual environment
    that sees the system packages, and run the README block there from a temporary folder with the project root off the path."""
    import subprocess
    import sys
    import tempfile
    from . import config as config_module
    cfg = config_module.load(root / "esoi.toml")
    folders = [root / p for p in (cfg.python_path or ["."])]
    home = next((f for f in [root, *folders] if (f / "pyproject.toml").is_file()), None)
    if home is None:
        return ["README.md: installed stage: no pyproject.toml to build a wheel from"]
    with tempfile.TemporaryDirectory() as scratch:
        scratch_path = Path(scratch)
        import shutil
        source = scratch_path / "source"     # built from a copy, so the project folder never gets build/ or egg-info litter
        shutil.copytree(home, source, ignore=shutil.ignore_patterns("build", "*.egg-info", "__pycache__", ".esoi_cache", ".git"))
        done = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir",
                               str(scratch_path / "dist"), str(source)], capture_output=True, text=True, timeout=600)
        wheels = sorted((scratch_path / "dist").glob("*.whl"))
        if done.returncode or not wheels:
            return [f"README.md: installed stage: the wheel did not build: {(done.stderr or done.stdout)[-300:]}"]
        env_dir = scratch_path / "venv"
        subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(env_dir)], check=True, capture_output=True, timeout=600)
        python = env_dir / "bin" / "python"
        clean = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}   # a path entry must not make pip think it is installed
        installed = subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--no-index", "--ignore-installed", str(wheels[0])],
                                   capture_output=True, text=True, timeout=600, env=clean)
        if installed.returncode:
            return [f"README.md: installed stage: the wheel did not install: {installed.stderr[-300:]}"]
        (scratch_path / "block.txt").write_text(block, encoding="utf-8")
        drop = {str(Path(p).resolve()) for p in [root, *folders]}
        kept = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and str(Path(p).resolve()) not in drop]
        library = str(Path(__file__).resolve().parents[1])
        if cfg.package != "esoi" and library not in kept:
            kept.append(library)   # the library that runs this check; esoi's own wheel supplies itself
        work = scratch_path / "cwd"
        work.mkdir()
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(kept), ESOI_IN_ENTRY_CHECK="1")
        ran = subprocess.run([str(python), "-m", "esoi.entry", "--readme-block", str(scratch_path / "block.txt"), "--json"],
                             cwd=work, env=env, capture_output=True, text=True, timeout=600)
        try:
            found = json.loads(ran.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return [f"README.md: installed stage did not report: {(ran.stderr or ran.stdout)[-300:]}"]
        return [f"installed: {line}" for line in found.get("problems", [])]


def readme_check(root: Path, installed: bool = False) -> Dict[str, List[str]]:
    """The README example, offline (and from an installed wheel when ``installed``): ``{"problems": [...], "pending": [...]}``."""
    block, name, bad = readme_block(root)
    if bad:
        return {"problems": bad, "pending": []}
    if installed:
        return {"problems": installed_readme(root, block), "pending": []}
    project_runner(root)
    os.environ["ESOI_IN_ENTRY_CHECK"] = "1"
    return run_block(block)


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="esoi.entry", description="One line for any solution or intent: check that each runs.")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--readme", action="store_true", help="run the README's first example that calls <package>.run (rule S37)")
    ap.add_argument("--installed", action="store_true", help="with --readme: build the wheel, install it in a temporary venv, run it there")
    ap.add_argument("--readme-block", default="", help="run the doctest block in this file (used by the installed stage)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gate", action="store_true", help="exit 1 unless every id answers (ok, pending-key or pending-install)")
    args = ap.parse_args(argv)
    if args.readme_block:
        found = run_block(Path(args.readme_block).read_text(encoding="utf-8"))
        print(json.dumps(found))
        return 1 if found["problems"] else 0
    root = Path(args.root).resolve()
    if args.readme:
        found = readme_check(root, installed=args.installed)
        if args.json:
            print(json.dumps(found))
        else:
            print("\n".join(found["problems"] + found["pending"]) or "README: ok")
        return 1 if (args.gate and found["problems"]) else 0
    rows = check_entries(root)
    if args.json:
        print(json.dumps(rows, default=str))
    else:
        for r in rows:
            print(f"{r['outcome']:16s} {r['level']:8s} {r['id']} ({r['kind'] or 'no kind'}): {r['detail']}")
        answering = sum(r["outcome"] in ANSWERING for r in rows)
        counts = ", ".join(f"{o} {sum(r['outcome'] == o for r in rows)}" for o in OUTCOMES if any(r["outcome"] == o for r in rows))
        print(f"summary: {answering} of {len(rows)} ids answer ({counts}); share {round(answering / (len(rows) or 1), 3)}")
    return 1 if args.gate and any(r["outcome"] not in ANSWERING for r in rows) else 0


if __name__ == "__main__":   # run through the imported module, so its Pending and Offline are the ones the entries raise
    import sys
    from esoi import entry
    sys.exit(entry.main())
