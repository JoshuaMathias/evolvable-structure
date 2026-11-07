"""The interface of MetricRecordKeeping: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from pathlib import Path
from typing import Dict, List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.optimization.keep_metric_record.iteration import MetricIteration  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.optimization.keep_metric_record.metric_meter import AFTER, BEFORE, OfflineArmMeter, RecordedRowMeter, read_value  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.optimization.keep_metric_record.metric_results import FileMetricLedger, MetricResult, reconcile, render_line  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.optimization.keep_metric_record.spec_slice import Chosen, RepoSliceSource, SpecSlice, lexical_choice, next_milestone, target_of  # noqa: F401  (re-exported: other units call this unit through its interface)

__all__ = ["AFTER", "BEFORE", "Chosen", "FileMetricLedger", "MetricIteration", "MetricRecordKeeping", "MetricResult", "OfflineArmMeter", "RecordedRowMeter", "RepoSliceSource", "SpecSlice", "lexical_choice", "next_milestone", "read_value", "reconcile", "render_line", "target_of"]


@solution("keep-metric-record", kind="event", entry="readings", example=".")
@runtime_checkable
class MetricRecordKeeping(Protocol):
    """The two readings a piece of work records (before and after) and how each is said while it is taken."""

    def readings(self, project: str) -> Dict[str, str]: ...


@implementation("keep-metric-record", "library-modules")
class LibraryModules:
    """The iteration, meter and ledger modules of the library, over the slice of the specification that ``spec-index`` gives for the work."""

    def readings(self, project: str) -> Dict[str, str]:
        from esoi.optimization.keep_metric_record import iteration
        return {name: texts[0] for name, texts in iteration.READING_STATUS.items()}

    def slice_of(self, project: str, request: str, k: int = 5) -> List[str]:
        """The ids of the best ``k`` records of the project's index for the words of ``request``: the slice the work is measured against."""
        from esoi.structure.intent_registry import config as config_module
        from esoi.understanding.spec_search import spec_index
        index = spec_index.build(config_module.load(Path(project)))
        return [hit["id"] for hit in spec_index.find_specs(index, request, k)]
