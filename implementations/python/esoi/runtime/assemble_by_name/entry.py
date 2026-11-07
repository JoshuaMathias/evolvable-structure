"""One line for any solution or intent: ``run(id, input)`` returns what that solution or intent is for.

The same call works at every level of a project's hierarchy, because every level is reached through a declared interface:

    import hubofhubs
    hubofhubs.run("card-store", "rust release")       # a leaf: the store's answer to the query
    hubofhubs.run("remember-and-recall", "rust")      # a container: its composition arm's answer
    hubofhubs.run("hub-of-hubs", "latest Rust?")      # the whole repository: its top intent's root solution

A package exposes ``run = esoi.runtime.assemble_by_name.entry.runner(<its Assembler>)``; ``esoi.run`` is the same function bound to esoi's own solutions.
``run`` also takes an interface class declared with ``@solution``: ``run(CardStore)`` returns the ready handle, typed as that
Protocol, so an editor or a type checker knows its methods.
What comes back depends on the solution's declared kind (``@solution(id, kind=..., entry=...)``, see ``esoi.runtime.implementation_selection.declare``):

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

import inspect
import os
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional, Tuple, Type, TypeVar, overload

from esoi.runtime.assemble_by_name.entry_types import EntryError, Pending
from esoi.runtime.assemble_by_name.intent_map import intent_target, packaged_map, records_root, tree
from esoi.runtime.assemble_by_name.seat_blockers import blockers
from esoi.runtime.assemble_by_name.target_lookup import declared, locate, solution_of
from esoi.runtime.implementation_selection import declare
from esoi.runtime.implementation_selection import selection_registry

__all__ = ["Runner", "call_entry", "describe", "run", "runner", "targets"]


def process_environment() -> Mapping[str, str]:
    """The one place this module reads the process environment: the entry function's default ``environ``."""
    return os.environ


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
    from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
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
        return run_function(assembler, sid, entry, env, chosen, input)
    handle = interface_handle(assembler, sid, entry, env, chosen, (options, provided, lock))
    return handle if entry.kind == "store" and input is None else entry_answer(sid, entry, handle, input)


def interface_handle(assembler: Any, sid: str, entry: Any, env: Mapping[str, str], chosen: Mapping[str, str], rest: tuple) -> Any:
    """The ready handle of a solution declared on an interface class; it must declare its kind and entry."""
    if not entry.kind or not entry.entry:
        raise EntryError(f"{sid} declares no kind or entry: add kind=\"event\"|\"evaluate\"|\"store\" and entry=\"<method>\" to its "
                         f"@solution on {entry.interface.__name__} (rule S37)", code="no-entry")
    options, provided, lock = rest
    return build_handle(assembler, sid, env, chosen, options, provided, lock)


def entry_answer(sid: str, entry: Any, handle: Any, input: Any) -> Any:
    """What the entry method answers for the input; an ``evaluate`` entry needs an artifact to evaluate."""
    if entry.kind == "evaluate" and input is None:
        raise EntryError(f"{sid} evaluates an artifact: pass it as the input (for example {entry.example!r})")
    return call_entry(getattr(handle, entry.entry), input)


def run_function(assembler: Any, sid: str, entry: Any, env: Mapping[str, str], chosen: Mapping[str, str], input: Any) -> Any:
    """Run a solution that is a function: it is its own entry, resolved from the scope that registered it."""
    scope = next(one.scope for one in assembler.chain() if selection_registry.REGISTRY.get((one.scope, sid)) is entry)
    if input is None and entry.example is None:
        raise EntryError(f"{sid} takes an input")
    return call_entry(declare.resolve(sid, chosen.get(sid), environ=env, scope=scope), input)


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
    """``run`` bound to one package's Assembler: ``hubofhubs.run = esoi.runtime.assemble_by_name.entry.runner(HUB)``."""
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


SELF_DECLARING = ("esoi.understanding.spec_search.spec_index", "esoi.understanding.spec_search.spec_search",
                  "esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading",
                  "esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness")


def own_modules(package: Path) -> Tuple[str, ...]:
    """Every module of esoi that declares a solution: the root's ``apply_esoi``, each solution's ``interface.py`` beside its code, and the
    few modules that declare a solution in the file that does its work."""
    interfaces = sorted("esoi." + ".".join(p.relative_to(package).with_suffix("").parts) for p in package.rglob("interface.py"))
    return ("esoi.apply_esoi", *interfaces, *SELF_DECLARING)


def own_runner() -> Runner:
    """``run`` bound to esoi's own solutions (each ``interface.py``), with this checkout's records when there is one."""
    from esoi.runtime.assemble_by_name.assemble import Assembler
    package = Path(__file__).resolve().parents[2]
    root = package.parents[2] if (package.parents[2] / "esoi.toml").is_file() else None
    return runner(Assembler("esoi", package, modules=own_modules(package), records=root))
