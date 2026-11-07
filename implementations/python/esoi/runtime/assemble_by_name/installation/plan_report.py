"""Render an install plan as text for a person and as JSON for a program."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from esoi.runtime.assemble_by_name.environment_needs.closure import Member, explain_closure
from esoi.runtime.assemble_by_name.installation.plan import Plan


def head_lines(selected: Plan, members: Sequence[Member]) -> List[str]:
    """The closure with reasons, then the resolution steps when the ladder had something to resolve."""
    lines: List[str] = []
    if members:
        lines += ["closure:"] + [f"  {line}" for line in explain_closure(members)]
    if selected.steps and (selected.conflicts or selected.substitutions or selected.isolated):
        lines += ["resolution:"] + [f"  {step}" for step in selected.steps]
    return lines


def plan_text(selected: Plan, members: Sequence[Member] = ()) -> str:
    """The plan as text: the closure with reasons, the ladder, what would run, what a person must still do."""
    lines = head_lines(selected, members)
    lines += [f"substitution: {one.text()}" for one in selected.substitutions]
    lines += [f"CONFLICT {one}" for one in selected.conflicts]
    lines += [f"option: {text}" for text in selected.options]
    lines.append("nothing to install" if selected.empty and not selected.conflicts else "would run:")
    lines += run_lines(selected)
    lines += [f"you must install: {text}" for text in selected.binaries]
    lines += [f"you must provide: {text}" for text in selected.missing]
    lines += [f"note: {text}" for text in selected.notes]
    return "\n".join(lines) + "\n"


def run_lines(selected: Plan) -> List[str]:
    """What would run: the pip install, one venv per isolated group, and the scripts."""
    lines: List[str] = []
    if selected.pip:
        lines.append("  python -m pip install " + " ".join(f"'{spec}'" for spec in selected.pip) + "  (then pip check)")
    for one in selected.isolated:
        lines.append(f"  python -m venv {one.folder}; {one.folder}/bin/python -m pip install " + " ".join(f"'{spec}'" for spec in one.specs))
    for role, path in selected.scripts:
        lines.append("  " + {"requirements": "python -m pip install -r ", "shell": "sh ", "python": "python "}.get(role, "") + path)
    return lines


def plan_json(selected: Plan, members: Sequence[Member] = ()) -> Dict[str, Any]:
    """The plan as plain data under a versioned schema (names only, never values)."""
    return {"schema": "esoi.install/1", "closure": explain_closure(members), "steps": list(selected.steps), "pip": list(selected.pip),
            "constraints": list(selected.constraints), "scripts": [{"role": r, "path": p} for r, p in selected.scripts],
            "isolated": [vars(one) | {"specs": list(one.specs)} for one in selected.isolated],
            "substitutions": [vars(one) for one in selected.substitutions], "conflicts": list(selected.conflicts),
            "options": list(selected.options), "binaries": list(selected.binaries), "missing": list(selected.missing),
            "notes": list(selected.notes), "coherent": selected.coherent}
