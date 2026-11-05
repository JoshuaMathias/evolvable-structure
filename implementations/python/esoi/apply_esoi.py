"""The root of esoi: Apply ESOI to a Project. ``esoi.run("apply-esoi", ".")`` calls the four containers in the order the work happens, each
through its one-line entry: Understanding, Structure, Optimization, Runtime."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.optimization.interface import Optimizing
from esoi.runtime.assemble_by_name.lazy_need import Lazy
from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.interface import Structuring
from esoi.structure.intent_registry import intents
from esoi.understanding.interface import Understanding
from esoi.runtime.interface import RuntimeServing


@solution("apply-esoi", kind="evaluate", entry="review", example=".")
@runtime_checkable
class ApplyingEsoi(Protocol):
    """How far a project applies ESOI: one read-only report from each container."""

    def review(self, project: str) -> Dict[str, Any]: ...


@implementation("apply-esoi", "through-the-four-containers")
class ThroughTheFourContainers:
    """Understanding, then Structure, then Optimization, then Runtime, each called through its entry."""

    def __init__(self, understanding: Lazy[Understanding], structure: Lazy[Structuring], optimization: Lazy[Optimizing], runtime: Lazy[RuntimeServing]):
        self.understanding, self.structure, self.optimization, self.runtime = understanding, structure, optimization, runtime

    def review(self, project: str) -> Dict[str, Any]:
        with intents.session():    # the record folders are found once for the whole review
            return {"understanding": self.understanding.review(project), "structure": self.structure.review(project),
                    "optimization": self.optimization.review(project), "runtime": self.runtime.review()}


@implementation("apply-esoi", "documents-only")
class DocumentsOnly:
    """What applying ESOI by hand needs: Understanding alone, with no checks and no measurements."""

    def __init__(self, understanding: Lazy[Understanding]):
        self.understanding = understanding

    def review(self, project: str) -> Dict[str, Any]:
        return {"understanding": self.understanding.review(project)}
