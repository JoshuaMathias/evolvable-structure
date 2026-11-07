"""Check the declared needs of the solutions against the records: every disagreement, and a cycle among the default arms."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence, Set

from esoi.structure.intent_registry.fields import parse_tags
from esoi.structure.intent_registry.tables import ids


CONSUMER_PROVIDED = "consumer-provided"   # the tag of a solution that has no default arm because the consumer supplies it


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


def need_problems(row: Mapping[str, str], rows: Mapping[str, Mapping[str, str]], tags: Mapping[str, Set[str]],
                  needs: Mapping[str, Set[str]]) -> List[str]:
    """How one implementation's recorded uses and declared needs disagree, and which needs have no arm to build."""
    bad: List[str] = []
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
    return bad


def problems(solutions: Sequence[Mapping[str, str]], implementations: Sequence[Mapping[str, str]],
             needs: Mapping[str, Set[str]]) -> List[str]:
    """Every way the records and the declared needs disagree. Empty means the graph is sound. ``needs`` is
    ``{implementation_id: {solution ids}}`` as ``Assembler.declared_needs`` reads it from the constructor parameters."""
    bad: List[str] = []
    rows = {s["solution_id"]: s for s in solutions}
    tags = {sid: {t["tag"] for t in parse_tags(s.get("tags", ""))} for sid, s in rows.items()}
    for row in implementations:
        bad += need_problems(row, rows, tags, needs)
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
