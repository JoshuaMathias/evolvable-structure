"""The flow of Understanding: how ESOI reaches the people and agents who apply it. It calls the one-line entry of each part in the order the work happens."""
from dataclasses import dataclass
from typing import Any, Dict

from esoi.runtime.assemble_by_name.lazy_need import Lazy
from esoi.structure.intent_registry import intents
from esoi.runtime.implementation_selection.declare import implementation
from esoi.understanding.interface import Understanding
from esoi.understanding.the_standard.interface import TheStandard
from esoi.understanding.esoi_for_ai.interface import EsoiForAi
from esoi.understanding.readable_records.interface import ReadableRecording
from esoi.understanding.review_tracker.interface import ReviewTracking
from esoi.understanding.local_application_index.interface import LocalApplicationIndexing


@implementation("esoi-understanding", "composition")
@dataclass
class UnderstandingFlow:
    """Hands the call to each part of Understanding in turn and gathers what each reports; the parts are typed needs, so each one can be
    replaced without changing this flow."""

    the_standard: Lazy[TheStandard]
    esoi_for_ai: Lazy[EsoiForAi]
    readable_records: Lazy[ReadableRecording]
    review_tracker: Lazy[ReviewTracking]
    local_index: Lazy[LocalApplicationIndexing]

    def review(self, project: str) -> Dict[str, Any]:
        with intents.session():    # the record folders are found once for the whole review
            report: Dict[str, Any] = {
                "the-standard": self.the_standard.describe(project),
                "esoi-for-ai": self.esoi_for_ai.describe(project),
                "readable-records": self.readable_records.page(project),
                "review-tracker": self.review_tracker.stale(project),
                "local-application-index": self.local_index.describe(project),
            }
            from esoi.structure.intent_registry.registry import load_project
            from esoi.understanding.spec_search import spec_index, spec_search
            config, _ = load_project(project)
            views = spec_search.views_from_index(spec_index.build(config))
            report["spec-search"] = {"views": len(views)}
            return report
