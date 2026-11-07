"""The flow of Optimizing: how a project comes to run the implementation the evidence shows is best. It calls the one-line entry of each part in the order the work happens."""
from dataclasses import dataclass
from typing import Any, Dict

from esoi.runtime.assemble_by_name.lazy_need import Lazy
from esoi.structure.intent_registry import intents
from esoi.runtime.implementation_selection.declare import implementation
from esoi.optimization.interface import Optimizing
from esoi.optimization.measurement_harness.interface import MeasurementHarnessing
from esoi.optimization.when_metrics_are_run.interface import WhenMetricsAreRun
from esoi.optimization.leaderboard.interface import Leaderboarding
from esoi.optimization.promote_the_winner.interface import WinnerPromoting
from esoi.optimization.keep_metric_record.interface import MetricRecordKeeping


@implementation("esoi-optimization", "composition")
@dataclass
class OptimizationFlow:
    """Hands the call to each part of Optimization in turn and gathers what each reports; the parts are typed needs, so each one can be
    replaced without changing this flow."""

    harness: Lazy[MeasurementHarnessing]
    when: Lazy[WhenMetricsAreRun]
    board: Lazy[Leaderboarding]
    promotion: Lazy[WinnerPromoting]
    record: Lazy[MetricRecordKeeping]

    def review(self, project: str) -> Dict[str, Any]:
        with intents.session():    # the record folders are found once for the whole review
            report: Dict[str, Any] = {
                "measurement-harness": self.harness.components(project),
                "when-metrics-are-run": self.when.describe(project),
                "leaderboard": self.board.standings(project),
                "promote-the-winner": self.promotion.proposals(project),
                "keep-metric-record": self.record.readings(project),
            }
            return report
