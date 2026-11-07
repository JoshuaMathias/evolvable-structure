"""The interface of KnowWhatAResultMeasures: the modules other units use to ask whether a recorded result still describes the code, and which foundations it builds on.

The solution itself (``know-what-a-result-measures``, with its three staleness rules as arms) is declared in ``staleness``. Importing this module runs nothing."""
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import builds_on, code_provenance, stale_reasons
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.builds_on import Foundation, declared, declared_arms, identity as builds_on_identity, load_config, problems
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_reasons import defect_reason, stale_reason
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_provenance import code_shas, current_sha, external_code_paths
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.ownership_index import RULES
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness import count_stale, explain_cli
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.attest import note, run_cli as attest_run_cli

__all__ = ["Foundation", "defect_reason", "RULES", "attest_run_cli", "builds_on", "builds_on_identity", "code_provenance", "code_shas", "count_stale", "current_sha", "declared", "declared_arms", "explain_cli", "external_code_paths", "load_config", "note", "problems", "stale_reason", "stale_reasons"]
