"""The flow of RuntimeServing: how a better measurement changes what runs inside other people's programs. It calls the one-line entry of each part in the order the work happens."""
from dataclasses import dataclass
from typing import Any, Dict

from esoi.runtime.assemble_by_name.lazy_need import Lazy
from esoi.structure.intent_registry import intents
from esoi.runtime.implementation_selection.declare import implementation
from esoi.runtime.interface import RuntimeServing
from esoi.runtime.implementation_selection.interface import ImplementationSelecting
from esoi.runtime.assemble_by_name.interface import AssemblingByName
from esoi.runtime.consumer_check.interface import ConsumerChecking


@implementation("esoi-runtime", "composition")
@dataclass
class RuntimeFlow:
    """Hands the call to each part of Runtime in turn and gathers what each reports; the parts are typed needs, so each one can be
    replaced without changing this flow."""

    selection: Lazy[ImplementationSelecting]
    assembly: Lazy[AssemblingByName]
    consumer: Lazy[ConsumerChecking]

    def review(self, solution_id: str = "structure-check") -> Dict[str, Any]:
        with intents.session():    # the record folders are found once for the whole review
            report: Dict[str, Any] = {
                "implementation-selection": self.selection.choose(solution_id),
                "assemble-by-name": self.assembly.names(solution_id),
                "consumer-check": self.consumer.known_ids("esoi"),
            }
            return report
