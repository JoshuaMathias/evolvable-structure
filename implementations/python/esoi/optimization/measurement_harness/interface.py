"""The interface of MeasurementHarnessing: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project


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
