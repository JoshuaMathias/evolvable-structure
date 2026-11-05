"""Render an install plan as text for a person and as JSON for a program."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from esoi.runtime.assemble_by_name.environment_needs.closure import Member, explain_closure
from esoi.runtime.assemble_by_name.installation.plan import Plan


def plan_text(selected: Plan, members: Sequence[Member] = ()) -> str:
    """The plan as text: the closure with reasons, the ladder, what would run, what a person must still do."""
    lines: List[str] = []
    if members:
        lines += ["closure:"] + [f"  {line}" for line in explain_closure(members)]
    if selected.steps and (selected.conflicts or selected.substitutions or selected.isolated):
        lines += ["resolution:"] + [f"  {step}" for step in selected.steps]
    for one in selected.substitutions:
        lines.append(f"substitution: {one.text()}")
    for one in selected.conflicts:
        lines.append(f"CONFLICT {one}")
    for text in selected.options:
        lines.append(f"option: {text}")
    lines.append("nothing to install" if selected.empty and not selected.conflicts else "would run:")
    if selected.pip:
        lines.append("  python -m pip install " + " ".join(f"'{spec}'" for spec in selected.pip) + "  (then pip check)")
    for one in selected.isolated:
        lines.append(f"  python -m venv {one.folder}; {one.folder}/bin/python -m pip install " + " ".join(f"'{spec}'" for spec in one.specs))
    for role, path in selected.scripts:
        lines.append("  " + {"requirements": "python -m pip install -r ", "shell": "sh ", "python": "python "}.get(role, "") + path)
    for text in selected.binaries:
        lines.append(f"you must install: {text}")
    for text in selected.missing:
        lines.append(f"you must provide: {text}")
    for text in selected.notes:
        lines.append(f"note: {text}")
    return "\n".join(lines) + "\n"


def plan_json(selected: Plan, members: Sequence[Member] = ()) -> Dict[str, Any]:
    """The plan as plain data under a versioned schema (names only, never values)."""
    return {"schema": "esoi.install/1", "closure": explain_closure(members), "steps": list(selected.steps), "pip": list(selected.pip),
            "constraints": list(selected.constraints), "scripts": [{"role": r, "path": p} for r, p in selected.scripts],
            "isolated": [vars(one) | {"specs": list(one.specs)} for one in selected.isolated],
            "substitutions": [vars(one) for one in selected.substitutions], "conflicts": list(selected.conflicts),
            "options": list(selected.options), "binaries": list(selected.binaries), "missing": list(selected.missing),
            "notes": list(selected.notes), "coherent": selected.coherent}
