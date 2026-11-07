"""The flow of Structuring: the project's records and code as one true and lean structure. It calls the one-line entry of each part in the order the work happens."""
from dataclasses import dataclass
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from esoi.runtime.assemble_by_name.lazy_need import Lazy
from esoi.structure.intent_registry import intents
from esoi.runtime.implementation_selection.declare import implementation
from esoi.structure.interface import Structuring
from esoi.structure.intent_registry.interface import IntentRegistering
from esoi.structure.library_adoption.interface import LibraryAdopting
from esoi.structure.ownership_map.interface import OwnershipMapping
from esoi.structure.structure_check.interface import StructureChecking
from esoi.structure.structure_budget.interface import StructureBudgeting


@implementation("esoi-structure", "composition")
@dataclass
class StructureFlow:
    """Hands the call to each part of Structure in turn and gathers what each reports; the parts are typed needs, so each one can be
    replaced without changing this flow."""

    registry: Lazy[IntentRegistering]
    ownership: Lazy[OwnershipMapping]
    check: Lazy[StructureChecking]
    budget: Lazy[StructureBudgeting]
    adoption: Lazy[LibraryAdopting]

    def review(self, project: str) -> Dict[str, Any]:
        with intents.session():    # the record folders are found once for the whole review
            report: Dict[str, Any] = {
                "intent-registry": self.registry.count(project),
                "ownership-map": self.ownership.unowned(project),
                "structure-budget": self.budget.describe(project),
                "library-adoption": self.adoption.unresolved(project),
            }
            if os.environ.get("ESOI_IN_ENTRY_CHECK"):    # the entry check (rule S37) calls this flow from inside a structure check: it does not start another
                report["structure-check"] = {"skipped": "inside an entry check"}
                report["coherence_passed"] = None
                return report
            problems = self.check.check(project)
            report["structure-check"] = {"problems": len(problems), "by_rule": dict(Counter(line.split(" ", 1)[0] for line in problems))}
            try:
                from esoi.structure.structure_check.interface import coherence_check
                report["coherence_passed"] = coherence_check(Path(project))["summary"]["passed"]
            except ImportError:
                report["coherence_passed"] = None
            return report
