"""Plan the install of one assembly: its closure, the plan for it, and the substitution of another arm when the selected ones conflict."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi.runtime.assemble_by_name.environment_needs.closure import Member, members_pairs
from esoi.runtime.assemble_by_name.environment_needs.declarations import Entry, gather
from esoi.runtime.assemble_by_name.installation.conflicts import Conflict, find_conflicts
from esoi.runtime.assemble_by_name.installation.plan import Plan, Substitution
from esoi.runtime.assemble_by_name.installation.resolution_ladder import make_plan
from esoi.runtime.assemble_by_name.installation.resolvers import Resolver


def first_free(assembler: Any, scene: tuple, sid: str, alternatives: Sequence[str]) -> Optional[Tuple[str, List[Member], List[Entry]]]:
    """The first alternative arm for ``sid`` whose closure has no conflict: ``(arm, closure members, entries)``, or None."""
    base, names, solutions, every_arm = scene
    for alternative in alternatives:
        members = assembler.closure(replace(base, names={**names, sid: alternative}), None, solutions, every_arm)
        found = gather(members_pairs(members, []))
        if not find_conflicts(found):
            return alternative, members, found
    return None


def assembly_plan(assembler: Any, config: Any, environ: Mapping[str, str], solutions: Sequence[str] = (), every_arm: bool = False,
                  resolver: Optional[Resolver] = None, rank: Optional[Callable[[str, str], Sequence[str]]] = None,
                  lead: Optional[Callable[[str], Optional[float]]] = None, project: Optional[Path] = None
                  ) -> Tuple[Plan, List[Member]]:
    """The install plan for what the solutions use (their selected arms, the arms that fill their needs, and the modules each
    imports), with the ladder applied. ``rank(solution_id, selected)`` gives the arms to try instead, best first by the metric
    (default: the other names in order); ``lead(solution_id)`` says how large the selected arm's recorded lead over its runner-up
    is (None: none recorded), so the least important seat gives way first. Returns the plan and the closure it describes."""
    from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
    base = config or AssemblyConfig()
    state: Dict[str, Any] = {"members": assembler.closure(base, None, solutions, every_arm)}
    notes: List[str] = []
    entries = gather(members_pairs(state["members"], notes))
    names = dict(base.names)
    orders: Dict[Tuple[str, str], Tuple[List[str], Optional[float], str]] = {}

    def order_of(sid: str, name: str) -> Tuple[List[str], Optional[float], str]:
        if (sid, name) not in orders:
            orders[(sid, name)] = assembler.metric_order(sid, name)
            notes.append(orders[(sid, name)][2])
        return orders[(sid, name)]

    def metric_rank(sid: str, name: str) -> List[str]:
        return order_of(sid, name)[0]

    def metric_lead(sid: str, name: str) -> Optional[float]:
        return order_of(sid, name)[1]

    def fallback(conflicts: Sequence[Conflict], current: Sequence[Entry]) -> Optional[Tuple[Substitution, List[Entry]]]:
        pulled = {arm for one in conflicts for spec, arms in one.pulls for arm in arms}
        seats = [m.label for m in state["members"] if m.label in pulled]
        seats.sort(key=lambda label: (lead(label.split(":", 1)[0]) if lead else metric_lead(label.split(":", 1)[0], label.split(":", 1)[1])) or 0.0)
        for label in seats:
            sid, name = label.split(":", 1)
            ranked = [a for a in (rank(sid, name) if rank else metric_rank(sid, name)) if a != name]
            free = first_free(assembler, (base, names, solutions, every_arm), sid, ranked)
            if free is not None:
                alternative, members, found = free
                others = sorted(pulled - {label})
                because = f"{name} conflicts with {', '.join(others) or 'the other requirements'} ({conflicts[0].reason} for {conflicts[0].distribution})"
                names[sid] = alternative
                state["members"] = members
                return Substitution(sid, name, alternative, because), found
        return None

    chosen = make_plan(entries, environ, resolver, fallback, project, notes)
    return chosen, state["members"]
