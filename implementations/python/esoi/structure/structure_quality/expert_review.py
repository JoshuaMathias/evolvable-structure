"""The paid arm of Structure Quality, specified and not run: an expert model reads a project's records and code outline and judges its scoping.

PAID: it calls a model, so it runs only with a cost estimate, a staged sample (3, 10, 30), a call budget and Joshua's approval
(``esoi/metric-run-policy.md``). ``prompt`` builds what the model reads, ``parse`` turns its reply into the same report shape the static arms
return, and ``review`` joins them through a ``provider`` the caller injects, so nothing here chooses a vendor or reads a key.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict

from esoi.structure.structure_quality.balance import WEIGHTS, SOUND_FLOOR, balanced, Dimension
from esoi.structure.structure_quality.project import Project

PER_CALL_TOKENS = {"input": 6000, "output": 600}   # the estimate behind the cost line in the metric record: one call per project reviewed
OUTLINE_FILES = 60

INSTRUCTIONS = (
    "You are an expert reviewer of how a software project is divided into solutions. For each dimension below, give a score from 0 to 1 "
    "(1 is excellent) and the worst offenders as short strings that begin with a path or unit name. Judge only what the outline shows. "
    "Do not use em dashes in any text you write.\n"
    "Dimensions: scope (one job per solution, arms share one purpose, every arm implements its interface), size (parts small enough to read "
    "whole), coupling (units call each other only through declared entry points, no cycles, a library never names its consumers), reuse (no "
    "copied code), surface (exported names are used), behavior (a contract test runs every arm of a solution).\n"
    'Reply with one JSON object: {"scope": {"score": 0.0, "offenders": []}, "size": {...}, "coupling": {...}, "reuse": {...}, "surface": {...}, "behavior": {...}}.'
)


def outline(project: Project) -> str:
    """Per unit, its files with their line counts and the names of its functions: what an expert reads in place of the whole code."""
    rows = []
    for path, module in sorted(project.modules.items())[:OUTLINE_FILES]:
        longest = max([length for _, _, length in module.functions] or [0])
        rows.append(f"{module.unit} | {path} | {module.lines} lines | longest function {longest} | imports {', '.join(sorted({b for b, _ in module.imports})[:8])}")
    return "\n".join(rows)


def prompt(project: Project) -> str:
    return f"{INSTRUCTIONS}\n\nOutline of the project (unit | file | size | imports):\n{outline(project)}"


def parse(reply: str) -> Dict[str, Any]:
    """The report a reply describes. A dimension the reply leaves out is not measured; a reply with no JSON object is an error."""
    found = re.search(r"\{.*\}", reply, re.S)
    if not found:
        raise ValueError("the reviewer's reply holds no JSON object")
    data = json.loads(found.group(0))
    dims = []
    for name in WEIGHTS:
        entry = data.get(name) or {}
        score = entry.get("score")
        dims.append(Dimension(name, None if score is None else round(float(score), 4), {"expert_score": score} if score is not None else {},
                              [str(o) for o in entry.get("offenders", [])]))
    verdict = balanced(dims)
    return {"stage": 3, **verdict, "sound_floor": SOUND_FLOOR,
            "dimensions": {d.name: {"score": d.score, "parts": d.parts, "offenders": d.offenders, "note": "expert review"} for d in dims}}


def review(project: Project, provider: Callable[[str], str]) -> Dict[str, Any]:
    return parse(provider(prompt(project)))
