"""Find what an id reaches in a package and its parents: a solution, or an intent with its root solution and arm."""
from __future__ import annotations

from typing import Any, Optional

from esoi.runtime.assemble_by_name.entry_types import EntryError, Target
from esoi.runtime.assemble_by_name.intent_map import intent_target, packaged_map, records_root, tree
from esoi.runtime.implementation_selection import selection_registry


def locate(assembler: Any, target: str) -> Target:
    """A solution id the Assembler (or a parent) knows, or an intent id of the package's records or packaged intent map."""
    assembler.prepare()
    if assembler.known_solution(target) or any(selection_registry.REGISTRY.get((one.scope, target)) for one in assembler.chain()):
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


def declared(assembler: Any, solution_id: str) -> Optional[selection_registry.Entry]:
    for one in assembler.chain():
        found = selection_registry.REGISTRY.get((one.scope, solution_id))
        if found is not None and found.interface is not None:
            return found
    return None


def solution_of(assembler: Any, interface: Any) -> str:
    """The solution id an interface class (or function) was declared with ``@solution`` for."""
    for one in assembler.chain():
        for (scope, sid), entry in selection_registry.REGISTRY.items():
            if scope == one.scope and entry.interface is interface:
                return sid
    raise EntryError(f"{getattr(interface, '__name__', interface)!r} is not declared with @solution in {assembler.scope} or its "
                     "parents", code="no-entry")
