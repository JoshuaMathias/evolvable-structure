"""The interface of MeasurementHarnessing: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, List, Protocol, runtime_checkable

from esoi.optimization.measurement_harness.access import loosening
from esoi.optimization.measurement_harness.arm_loading import load_impl
from esoi.optimization.measurement_harness.balance import balanced
from esoi.optimization.measurement_harness.case_loading import load_cases, sample_args
from esoi.optimization.measurement_harness.case_count import count_cases
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_provenance import current_sha
from esoi.optimization.measurement_harness.component_folder import prepare_path
from esoi.optimization.measurement_harness.run_command import run_cli
from esoi.optimization.measurement_harness.run_errors import RunError
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.stale_reasons import defect_reason, stale_reason
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_changed import code_changed_reason
from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project
from esoi.optimization.measurement_harness import cassette  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.optimization.measurement_harness import access, case_loading, record_result, run_component  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import stale_reasons

# What a consumer of the harness needs: load and run a component's cases for an arm, fold the result into the balanced number, narrow the
# source-access limits, and ask whether a recorded row still describes the code (``stale_reason``, ``defect_reason``, ``code_changed_reason``).
__all__ = ["MeasurementHarnessing", "access", "case_loading", "cassette", "count_cases", "defect_reason", "record_result", "run_component", "stale_reason", "stale_reasons"]


@solution("measurement-harness", kind="event", entry="components", example=".")
@runtime_checkable
class MeasurementHarnessing(Protocol):
    """The components the project can measure, one per folder of cases and implementations."""

    def components(self, project: str) -> List[str]: ...


@implementation("measurement-harness", "component-harness")
class ComponentHarness:
    """The harness that runs each implementation over a component's cases, tells which recorded rows a change has made stale
    (``know-what-a-result-measures``) and reads the public evidence others measured (``public-evidence``)."""

    def components(self, project: str) -> List[str]:
        from esoi.optimization.measurement_harness import component_folder
        cfg, found = load_project(project)
        return component_folder.discover_components(cfg)

    def stale(self, project: str) -> Dict[str, Dict[str, str]]:
        """Per staleness rule, which implementations' recorded rows a change has made stale (what ``esoi stale --count`` prints)."""
        from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import ownership_index, staleness
        cfg, found = load_project(project)
        return {rule: staleness.count_stale(cfg, rule) for rule in ownership_index.RULES}

    def public_evidence(self, project: str) -> int:
        """How many rows of public evidence the project holds beside its own measurements."""
        from esoi.optimization.when_metrics_are_run.public_evidence import evidence_records
        cfg, found = load_project(project)
        return len(evidence_records.load_for(cfg))
