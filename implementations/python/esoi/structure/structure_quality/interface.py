"""The interface of StructureQualityAssessing: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Any, Callable, Dict, Optional, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution

__all__ = ["StructureQualityAssessing"]


@solution("structure-quality", kind="evaluate", entry="assess", example="docs")
@runtime_checkable
class StructureQualityAssessing(Protocol):
    """How well a project's code and records divide the work: one balanced number from 0 to 1, each dimension's score, the dimensions flagged and their worst offenders."""

    def assess(self, project: str) -> Dict[str, Any]: ...


@implementation("structure-quality", "balanced_static")
class BalancedStatic:
    """Seven dimensions read from the code and records without a model (scope, size, coupling, reuse, flow, surface, behavior), weighted into one number."""

    def assess(self, project: str) -> Dict[str, Any]:
        from esoi.structure.structure_quality import assess
        return assess.assess(project)


@implementation("structure-quality", "file_size_only")
class FileSizeOnly:
    """The size dimension alone, as the number: the single-factor bound a balanced number has to beat, since shrinking files wins it."""

    def assess(self, project: str) -> Dict[str, Any]:
        from esoi.structure.structure_quality import assess
        report = assess.assess(project)
        size = report["dimensions"]["size"]
        return {**report, "score": size["score"], "flagged": ["size"] if size["offenders"] else [],
                "verdict": "unmeasured" if size["score"] is None else ("sound" if size["score"] >= 0.8 else "unsound")}


@implementation("structure-quality", "expert_review")
class ExpertScopingReview:
    """An expert model judges the scoping from an outline of the project. PAID: it needs a provider, a cost estimate and Joshua's approval; it is not run offline."""

    def __init__(self, ask: Optional[Callable[[str], str]] = None):
        self.ask = ask

    def assess(self, project: str) -> Dict[str, Any]:
        from pathlib import Path
        from esoi.structure.structure_quality import expert_review
        from esoi.structure.structure_quality.project import load
        if self.ask is None:
            raise ValueError("the expert review needs a provider (a function from a prompt to a reply); nothing was called")
        return expert_review.review(load(Path(project)), self.ask)
