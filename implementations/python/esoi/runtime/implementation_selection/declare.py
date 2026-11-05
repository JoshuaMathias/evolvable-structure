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

A name may be a variant, ``name@key=value`` (see ``esoi.runtime.implementation_selection.variants``): the implementation ``name`` is called with the
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

This sits on ``esoi.runtime.implementation_selection.select``: a repository's selection table and ``Selector`` keep working, their names join the
declared ones, and their ``default`` is optional. ``register`` adds an implementation of another package, or an
object that cannot carry a decorator (an instance).
"""
from __future__ import annotations

import functools
import inspect
import os
from contextlib import contextmanager
from typing import Any, Iterator, List, Mapping, Optional
from esoi.runtime.implementation_selection import variants
from esoi.runtime.implementation_selection import selection_registry
from esoi.runtime.implementation_selection import selection_cascade


class Solution:
    """A declared interface that runs the selected implementation when called. ``using="name"`` picks one for that call."""

    def __init__(self, solution_id: str, interface: Any):
        self.solution_id = solution_id
        self.interface = interface
        self.scope = selection_registry.scope_of(interface)
        functools.update_wrapper(self, interface)

    def reached(self) -> str:
        """The scope this interface reaches: the only package that declares its id, else its own package."""
        return selection_registry.locate(self.solution_id, None, self.scope)

    def __call__(self, *args: Any, using: Optional[str] = None, **kwargs: Any) -> Any:
        return resolve(self.solution_id, using, scope=self.reached())(*args, **kwargs)

    def chosen(self, using: Optional[str] = None) -> selection_registry.Choice:
        """The implementation a call would run now, and which layer of the cascade chose it."""
        return selection_cascade.choose(self.solution_id, using, scope=self.reached())

    def names(self) -> List[str]:
        return selection_cascade.names(self.solution_id, scope=self.reached())

    def implementation(self, using: Optional[str] = None) -> Any:
        """The chosen implementation object itself (a class is not instantiated)."""
        return resolve(self.solution_id, using, scope=self.reached())


KINDS = ("event", "evaluate", "store")


def solution(solution_id: str, scope: Optional[str] = None, *, kind: str = "", entry: str = "", example: Any = None):
    """Declare the interface of a solution. On a function the result is callable and runs the selected implementation;
    a class (a Protocol) is returned unchanged and reached with ``resolve(solution_id)``. The scope is the declaring
    package unless given.

    ``kind`` and ``entry`` make the solution reachable by the one-line entry ``esoi.runtime.assemble_by_name.entry.run(solution_id, input)``: an
    ``event`` returns the output of ``entry`` for the input, an ``evaluate`` returns ``entry``'s feedback or score on the
    artifact passed as input, a ``store`` returns the ready handle (or, given an input, ``entry``'s answer to it). A function
    is its own entry (``kind`` defaults to ``event``). ``example`` is an input the entry accepts offline."""
    if kind and kind not in KINDS:
        raise ValueError(f"@solution({solution_id!r}): kind {kind!r} is not one of {', '.join(KINDS)}")

    def declare(interface: Any) -> Any:
        found = selection_registry.scope_of(interface) if scope is None else scope
        declared = selection_registry.entry_for(solution_id, selection_registry.origin_of(interface), found)
        declared.interface = interface
        declared.kind = kind or ("" if inspect.isclass(interface) else "event")
        declared.entry = entry
        declared.example = example
        if inspect.isclass(interface) and entry and not callable(getattr(interface, entry, None)):
            raise ValueError(f"@solution({solution_id!r}): entry {entry!r} is not a method of {interface.__name__}")
        wrapped = interface if inspect.isclass(interface) else Solution(solution_id, interface)
        if wrapped is not interface:
            wrapped.scope = found
        return wrapped
    return declare


def implementation(solution_id: str, name: Optional[str] = None, scope: Optional[str] = None):
    """Declare one alternative of a solution beside its code; the name defaults to the function or class name. The scope
    is the declaring package unless given, so an implementation in one package can serve another package's solution."""
    def declare(obj: Any) -> Any:
        selection_registry.add(solution_id, name or getattr(obj, "__name__", ""), obj, selection_registry.origin_of(obj), selection_registry.scope_of(obj) if scope is None else scope)
        return obj
    return declare


def register(solution_id: str, name: str, target: Any, scope: Optional[str] = None, replace: bool = False) -> None:
    """Declare an implementation that is not a decorated function or class: an instance, an object of another package, or
    ``"module:Attr"`` imported when chosen. The scope is the package of the module that calls this, unless given.
    ``replace=True`` lets a consumer put its own implementation under a name the package already declares, whether that
    declaration comes before or after (without it, two different objects under one name raise)."""
    found, origin = selection_registry.caller_scope_and_origin(2)
    selection_registry.add(solution_id, name, target, origin, found if scope is None else scope, replace)




@contextmanager
def override(solution_id: str, name: str, scope: Optional[str] = None) -> Iterator[None]:
    """Select ``name`` for ``solution_id`` for everything run inside the block (this thread or task only)."""
    token = selection_registry.OVERRIDES.set(selection_registry.OVERRIDES.get() + ((solution_id, selection_registry.key(name), scope or ""),))
    try:
        yield
    finally:
        selection_registry.OVERRIDES.reset(token)





def resolve(solution_id: str, using: Optional[str] = None, environ: Optional[Mapping[str, str]] = None,
            scope: Optional[str] = None) -> Any:
    """The chosen implementation object of a solution (a class is not instantiated). For a variant, the object with its
    parameters bound as keyword arguments."""
    env = os.environ if environ is None else environ
    where = selection_registry.locate(solution_id, scope)
    picked = selection_cascade.choose(solution_id, using, env, where)
    base, params = variants.split(picked.name)
    found = selection_cascade.fetch(solution_id, base, selection_cascade.project_for(solution_id, env, where), where)
    return functools.partial(found, **params) if params else found
