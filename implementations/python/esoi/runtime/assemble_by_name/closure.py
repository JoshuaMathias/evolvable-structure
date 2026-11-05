"""The dependency closure of what an assembly would use: the selected arm of each solution and the arms that fill their needs."""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence, Set, Tuple

from esoi.runtime.assemble_by_name.environment_needs.closure import Member
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig


def closure(assembler: Any, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None,
            solutions: Sequence[str] = (), every_arm: bool = False) -> List[Member]:
    """The dependency closure of what an assembly would use, each member with the reason it is in: the selected arm of each
    solution asked for (``solutions``, else the config's, else every visible one) that is not provided, then the arms that
    fill their solution-typed needs, recursively (``needed by <solution>:<arm>``; a ``Lazy`` need is left out). ``every_arm=True`` takes every named arm
    of the roots instead. An arm that cannot be loaded is left to ``pending_needs``."""
    cfg = config or AssemblyConfig()
    given = dict(provided or {})
    assembler.prepare()
    members: List[Member] = []
    seen: Set[Tuple[str, str]] = set()

    def visit(sid: str, name: Optional[str], reason: str) -> None:
        for one in ([name] if name else assembler.names(sid)):
            if (sid, one) in seen:
                continue
            seen.add((sid, one))
            try:
                target = assembler.load(sid, one)
                needs = assembler.needs_of(target)
            except Exception:
                continue
            members.append(Member(f"{sid}:{one}", target, reason))
            if not every_arm:
                lazy = assembler.lazy_needs_of(target)
                for param, need in needs.items():
                    if param in lazy:    # built on first use: its requirements are asked for then, not up front
                        continue
                    picked = assembler.pick(need, None, cfg) if need not in given and assembler.known_solution(need) else None
                    if picked is not None:
                        visit(need, picked.name, f"needed by {sid}:{one}")

    for sid in (list(solutions) or list(cfg.solutions) or assembler.visible()):
        assembler.check_solution(sid)
        if sid in given:
            continue
        if every_arm:
            visit(sid, None, "every arm")
        else:
            picked = assembler.pick(sid, None, cfg)
            if picked is not None:
                visit(sid, picked.name, "selected")
    return members
