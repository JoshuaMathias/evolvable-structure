"""esoi: Evolvable Structure that Optimizes Intent (ESOI) as a library and a command.

An adopting repository keeps its intent as records (problems, ideals, solutions, implementations, metrics),
its placement as components, and its measurements as a results log. This package checks them against each
other (``esoi check``), runs and records evaluations (``esoi run``), ranks implementations
(``esoi leaderboard``), resolves a selection table at run time and builds a review tracker (``esoi tracker``).
Everything specific to a repository is configuration (``esoi.toml``).

In code, declare a solution once where it lives and call it::

    from esoi import solution, implementation, override

    @solution("greet-a-person")
    def greet(name): ...

    @implementation("greet-a-person", "plain")
    def plain(name): return f"Hello, {name}!"

    greet("Ada")                      # the project default, from the records
    greet("Ada", using="loud")        # this call only
    with override("greet-a-person", "loud"): ...   # a block

The public API is this module. Everything a program that embeds esoi imports is named here, so a module can move inside the package without
breaking a caller: the flat names in ``PUBLIC`` (``from esoi import Assembler``) and the namespaces in ``NAMESPACES``
(``from esoi import harness`` then ``harness.load_cases``). The package is four containers (``understanding``, ``structure``,
``optimization``, ``runtime``), each one folder per solution; import from them only inside esoi. ``tests/test_public_api.py`` resolves
every name below.
"""
import importlib
import types
from typing import Any, Dict, Tuple

from esoi.runtime.implementation_selection.declare import implementation, override, register, resolve, solution
from esoi.runtime.implementation_selection.selection_registry import SelectionError

__version__ = "0.4.0"

# Flat public names: name -> (module, attribute). A name here may differ from the attribute when the attribute alone would be unclear.
PUBLIC: Dict[str, Tuple[str, str]] = {
    "AFTER": ("esoi.optimization.keep_metric_record.metric_meter", "AFTER"),
    "Assembler": ("esoi.runtime.assemble_by_name.assemble", "Assembler"),
    "Assembly": ("esoi.runtime.assemble_by_name.assembly", "Assembly"),
    "AssemblyConfig": ("esoi.runtime.assemble_by_name.assembly_config", "AssemblyConfig"),
    "AssemblyError": ("esoi.runtime.assemble_by_name.assembly_errors", "AssemblyError"),
    "BEFORE": ("esoi.optimization.keep_metric_record.metric_meter", "BEFORE"),
    "BudgetExceeded": ("esoi.optimization.when_metrics_are_run.paid_gating", "BudgetExceeded"),
    "CallMeter": ("esoi.optimization.measurement_harness.call_meter", "CallMeter"),
    "Config": ("esoi.structure.intent_registry.config", "Config"),
    "ConsumerOptions": ("esoi.runtime.consumer_check.consumer", "Options"),
    "EVERY_MOMENT": ("esoi.optimization.keep_metric_record.metric_meter", "EVERY_MOMENT"),
    "EntryError": ("esoi.runtime.assemble_by_name.entry_types", "EntryError"),
    "FileMetricLedger": ("esoi.optimization.keep_metric_record.metric_results", "FileMetricLedger"),
    "Lazy": ("esoi.runtime.assemble_by_name.lazy_need", "Lazy"),
    "MAX_METRICS": ("esoi.optimization.keep_metric_record.metric_results", "MAX_METRICS"),
    "MetricIteration": ("esoi.optimization.keep_metric_record.iteration", "MetricIteration"),
    "MetricLedger": ("esoi.optimization.keep_metric_record.metric_results", "MetricLedger"),
    "MetricMeter": ("esoi.optimization.keep_metric_record.metric_meter", "MetricMeter"),
    "MetricResult": ("esoi.optimization.keep_metric_record.metric_results", "MetricResult"),
    "NOT_RECORDED_LINE": ("esoi.optimization.keep_metric_record.metric_results", "NOT_RECORDED_LINE"),
    "Offline": ("esoi.runtime.assemble_by_name.offline_guard", "Offline"),
    "Pending": ("esoi.runtime.assemble_by_name.entry_types", "Pending"),
    "READING_STATUS": ("esoi.optimization.keep_metric_record.iteration", "READING_STATUS"),
    "Registry": ("esoi.structure.intent_registry.registry", "Registry"),
    "RepoSliceSource": ("esoi.optimization.keep_metric_record.spec_slice", "RepoSliceSource"),
    "RequirementEntry": ("esoi.runtime.assemble_by_name.environment_needs.declarations", "Entry"),
    "RuleContext": ("esoi.structure.structure_check.rules.base", "Context"),
    "RuleGroup": ("esoi.structure.structure_check.rules.base", "RuleGroup"),
    "RunError": ("esoi.optimization.measurement_harness.run_errors", "RunError"),
    "RunFiles": ("esoi.optimization.keep_metric_record.metric_results", "RunFiles"),
    "SOURCES": ("esoi.optimization.keep_metric_record.metric_results", "SOURCES"),
    "SOURCE_MEASURED": ("esoi.optimization.keep_metric_record.metric_results", "SOURCE_MEASURED"),
    "SOURCE_NOT_APPLICABLE": ("esoi.optimization.keep_metric_record.metric_results", "SOURCE_NOT_APPLICABLE"),
    "SOURCE_RECORDED": ("esoi.optimization.keep_metric_record.metric_results", "SOURCE_RECORDED"),
    "SliceSource": ("esoi.optimization.keep_metric_record.spec_slice", "SliceSource"),
    "SpecSlice": ("esoi.optimization.keep_metric_record.spec_slice", "SpecSlice"),
    "TagTable": ("esoi.understanding.spec_search.spec_search", "TagTable"),
    "assembly_plan": ("esoi.runtime.assemble_by_name.installation.assembly_plan", "assembly_plan"),
    "call_entry": ("esoi.runtime.assemble_by_name.entry", "call_entry"),
    "check_consumer": ("esoi.runtime.consumer_check.consumer", "check_consumer"),
    "check_headers": ("esoi.structure.intent_registry.records", "check_headers"),
    "check_records": ("esoi.structure.intent_registry.records", "check_records"),
    "check_structure": ("esoi.structure.structure_check.check", "check"),
    "consumer_cases_hash": ("esoi.runtime.consumer_check.consumer", "cases_hash"),
    "consumer_library_dir": ("esoi.runtime.consumer_check.consumer", "library_dir"),
    "declared_entry": ("esoi.runtime.assemble_by_name.target_lookup", "declared"),
    "describe_metric": ("esoi.optimization.keep_metric_record.spec_slice", "describe_metric"),
    "environ_declared": ("esoi.runtime.assemble_by_name.environ_options", "environ_declared"),
    "environ_fill": ("esoi.runtime.assemble_by_name.environ_options", "environ_fill"),
    "environ_lacking": ("esoi.runtime.assemble_by_name.environ_options", "environ_lacking"),
    "first_arm": ("esoi.structure.intent_registry.registry", "first_arm"),
    "format_value": ("esoi.optimization.keep_metric_record.metric_results", "format_value"),
    "harness_arms": ("esoi.structure.intent_registry.registry", "harness_arms"),
    "index_tokens": ("esoi.understanding.spec_search.spec_index", "tokens"),
    "load": ("esoi.structure.intent_registry.registry", "load"),
    "load_cases": ("esoi.optimization.measurement_harness.case_loading", "load_cases"),
    "load_template": ("esoi.structure.intent_registry.records", "load_template"),
    "meters_from_names": ("esoi.optimization.keep_metric_record.metric_meter", "meters_from_names"),
    "own_code_paths": ("esoi.optimization.measurement_harness.code_provenance", "own_code_paths"),
    "parse_tags": ("esoi.structure.intent_registry.fields", "parse_tags"),
    "payload_of": ("esoi.optimization.keep_metric_record.metric_results", "payload_of"),
    "read_csv": ("esoi.structure.intent_registry.tables", "read_csv"),
    "read_tree": ("esoi.structure.intent_registry.intents", "read_tree"),
    "reconcile": ("esoi.optimization.keep_metric_record.metric_results", "reconcile"),
    "record_fields": ("esoi.structure.intent_registry.records", "fields"),
    "render_line": ("esoi.optimization.keep_metric_record.metric_results", "render_line"),
    "run_entry": ("esoi.runtime.assemble_by_name.entry", "run"),
    "served_by_solution": ("esoi.understanding.spec_search.spec_search", "served_by_solution"),
    "split_ids": ("esoi.structure.intent_registry.tables", "ids"),
    "stratified_sample": ("esoi.optimization.measurement_harness.case_loading", "stratified_sample"),
    "tables_of": ("esoi.structure.intent_registry.records", "tables_of"),
    "targets": ("esoi.runtime.assemble_by_name.entry", "targets"),
    "terms_of": ("esoi.understanding.spec_search.spec_search", "terms_of"),
    "views_from_index": ("esoi.understanding.spec_search.spec_search", "views_from_index"),
    "views_from_items": ("esoi.understanding.spec_search.spec_search", "views_from_items"),
    "without_line": ("esoi.optimization.keep_metric_record.metric_results", "without_line"),
}

# Public namespaces: name -> {module: attributes}. ``from esoi import harness`` gives an object with just these attributes.
NAMESPACES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "access": {
        "esoi.optimization.measurement_harness.access": ('violation',),
    },
    "cascade": {
        "esoi.optimization.leaderboard.cascade_stages": ('load_stages', 'parse'),
        "esoi.optimization.leaderboard.stage_standings": ('stage_index',),
    },
    "config": {
        "esoi.structure.intent_registry.config": ('load',),
    },
    "declarations": {
        "esoi.structure.intent_registry.specify_from_code.declarations": ('code_files', 'drift', 'scan'),
    },
    "entry": {
        "esoi.runtime.assemble_by_name.entry": ('build_handle', 'prepare', 'runner'),
        "esoi.runtime.assemble_by_name.entry_types": ('Pending',),
        "esoi.runtime.assemble_by_name.intent_map": ('snapshot',),
        "esoi.runtime.assemble_by_name.offline_guard": ('Offline',),
        "esoi.runtime.assemble_by_name.readme_example": ('run_block',),
    },
    "evidence": {
        "esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading": ('estimates', 'lines_for_implementation'),
        "esoi.optimization.when_metrics_are_run.public_evidence.evidence_ranking": ('rank',),
        "esoi.optimization.when_metrics_are_run.public_evidence.evidence_records": ('EvidenceError', 'implementation_candidates', 'load', 'load_for'),
    },
    "evidence_table": {
        "esoi.optimization.leaderboard.evidence_table": ('cell', 'cost_label', 'public_label', 'rate_label', 'seconds_label'),
    },
    "expect": {
        "esoi.optimization.measurement_harness.expect": ('aggregate_by_kind', 'check', 'score_kind_case'),
    },
    "foundation": {
        "esoi.runtime.consumer_check.foundation": ('declared', 'declared_arms', 'problems'),
    },
    "harness": {
        "esoi.optimization.leaderboard.case_identity": ('cases_digest',),
        "esoi.optimization.measurement_harness.arm_loading": ('load_impl',),
        "esoi.optimization.measurement_harness.call_meter": ('CallMeter',),
        "esoi.optimization.measurement_harness.case_loading": ('load_cases',),
        "esoi.optimization.measurement_harness.code_provenance": ('current_sha',),
        "esoi.optimization.measurement_harness.component_folder": ('prepare_path',),
        "esoi.optimization.measurement_harness.record_result": ('record_result',),
        "esoi.optimization.measurement_harness.record_slices": ('record_slices',),
        "esoi.optimization.measurement_harness.run_component": ('run_component',),
        "esoi.optimization.when_metrics_are_run.paid_gating": ('declares_paid', 'price_for'),
    },
    "hermetic": {
        "esoi.optimization.measurement_harness.hermetic": ('from_config',),
    },
    "hygiene": {
        "esoi.structure.structure_check.hygiene": ('repo_files', 'scan_repo', 'scan_text'),
    },
    "intents": {
        "esoi.structure.intent_registry.intents": ('RECORD_FILES', 'discover', 'folders', 'read_rows', 'read_tree', 'tree_folders'),
    },
    "leaderboard": {
        "esoi.optimization.leaderboard.arm_kinds": ('arm_kind', 'invariant_reason'),
        "esoi.optimization.leaderboard.arm_selection": ('selected_impls',),
        "esoi.optimization.leaderboard.case_identity": ('cases_digest',),
        "esoi.optimization.leaderboard.held_out_parts": ('part_of', 'part_row', 'selection_leader'),
        "esoi.optimization.leaderboard.ranking": ('pass_rate', 'passes', 'rank'),
        "esoi.optimization.leaderboard.results_log": ('all_results', 'is_partial', 'per_case_rows', 'slice_results'),
        "esoi.optimization.leaderboard.rival_decisions": ('best_guess', 'challengers', 'decisions'),
        "esoi.optimization.leaderboard.switching_policy": ('Policy', 'holdout_fraction', 'policies'),
        "esoi.optimization.leaderboard.verdict_labels": ('slice_verdicts',),
    },
    "lock": {
        "esoi.runtime.implementation_selection.lock": ('diff', 'status', 'update', 'write'),
    },
    "registry": {
        "esoi.structure.intent_registry.registry": ('load',),
    },
    "requirements": {
        "esoi.runtime.assemble_by_name.environment_needs.checking": ('UNMET', 'check'),
        "esoi.runtime.assemble_by_name.environment_needs.closure": ('members_pairs',),
        "esoi.runtime.assemble_by_name.environment_needs.declarations": ('Api', 'Binary', 'Download', 'Entry', 'Env', 'Isolate', 'Python', 'Resource', 'Service', 'api', 'binary', 'declared', 'download', 'env', 'gather', 'isolatable', 'network', 'python', 'resource', 'service'),
        "esoi.runtime.assemble_by_name.environment_needs.generated_files": ('env_template',),
        "esoi.runtime.assemble_by_name.environment_needs.report": ('describe',),
    },
    "scaffold": {
        "esoi.understanding.the_standard.scaffold": ('init',),
    },
    "selection": {
        "esoi.runtime.implementation_selection.declare": ('override', 'register', 'resolve'),
        "esoi.runtime.implementation_selection.selection_cascade": ('choose', 'env_name', 'names', 'snapshot'),
        "esoi.runtime.implementation_selection.selection_registry": ('REGISTRY', 'SelectionError', 'entry_for'),
    },
    "spec_index": {
        "esoi.understanding.spec_search.spec_index": ('build', 'cached', 'find_specs', 'of_intent', 'related', 'show', 'tokens'),
    },
    "spec_search": {
        "esoi.understanding.spec_search.spec_search": ('Found', 'Gate', 'RECORD_CANDIDATE_KINDS', 'RECORD_SOURCE', 'Selection', 'TagTable', 'VectorSearch', 'View', 'fuse', 'gate_decision', 'gated', 'lexical_scored', 'render', 'search', 'terms_of', 'views_from_index', 'views_from_items'),
    },
    "standards_nav": {
        "esoi.understanding.spec_search.standards_nav": ('MAX_SHOWN', 'lint', 'select_for_task'),
    },
}

__all__ = sorted(["SelectionError", "implementation", "override", "register", "resolve", "solution", "run", "__version__", *PUBLIC, *NAMESPACES])


def run(target, input=None, **overrides):
    """One line for any solution or intent of esoi itself: ``esoi.run("structure-check", ".")``. Packages bind the same function
    to their own Assembler (``entry.runner``)."""
    from esoi.runtime.assemble_by_name.entry import own_runner
    return own_runner()(target, input, **overrides)


def __getattr__(name: str) -> Any:
    if name in PUBLIC:
        module, attribute = PUBLIC[name]
        return getattr(importlib.import_module(module), attribute)
    if name in NAMESPACES:
        space = types.SimpleNamespace()
        for module, attributes in NAMESPACES[name].items():
            loaded = importlib.import_module(module)
            for attribute in attributes:
                setattr(space, attribute, getattr(loaded, attribute))
        return space
    raise AttributeError(f"module 'esoi' has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
