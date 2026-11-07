"""The interface of KnowWhatAResultMeasures: the modules other units use to ask whether a recorded result still describes the code, and which foundations it builds on.

The solution itself (``know-what-a-result-measures``, with its three staleness rules as arms) is declared in ``staleness``. Importing this module runs nothing."""
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import attest, builds_on, code_changed, code_provenance, ownership_index, stale_reasons, staleness  # noqa: F401  (re-exported: other units call this unit through its interface)

__all__ = ["attest", "builds_on", "code_changed", "code_provenance", "ownership_index", "stale_reasons", "staleness"]
