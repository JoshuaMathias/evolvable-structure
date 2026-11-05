"""Assess a project: the seven dimensions and the one balanced number, at stage 1 (static code and records) or stage 2 (adds co-change from git history)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from esoi.structure.structure_quality import behavior, balance, cochange, coupling, duplication, flow, scope, size, surface
from esoi.structure.structure_quality.balance import Budgets
from esoi.structure.structure_quality.project import Project, load


def assess_project(project: Project, stage: int = 1, budgets: Optional[Budgets] = None, coherence: Optional[Dict[str, object]] = None) -> Dict[str, Any]:
    """The report of one project already read. ``coherence`` is the coherence gate's report, passed in by the caller that has the records."""
    budgets = budgets or Budgets()
    history = cochange.mine(project, budgets) if stage >= 2 else None
    dimensions = [scope.measure(project, budgets), size.measure(project, budgets), coupling.measure(project, budgets, history),
                  duplication.measure(project, budgets), flow.measure(coherence), surface.measure(project, budgets), behavior.measure(project, budgets)]
    verdict = balance.balanced(dimensions)
    return {"stage": stage, "files": len(project.modules), "units": len({m.unit for m in project.modules.values()}), **verdict,
            "dimensions": {d.name: {"score": d.score, "parts": d.parts, "offenders": d.offenders, "note": d.note} for d in dimensions}}


def assess(project: str, stage: int = 1, budgets: Optional[Budgets] = None, coherence: Optional[Dict[str, object]] = None) -> Dict[str, Any]:
    return assess_project(load(Path(project)), stage, budgets, coherence)
