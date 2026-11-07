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
from esoi.structure.intent_registry.template_sync.versioning import __version__


# Flat public names, one per line: ``name module attribute`` (the attribute is left out when it is the name; it may differ from the name when
# the attribute alone would be unclear). Public namespaces, one line per module: ``namespace module attribute,attribute``;
# ``from esoi import harness`` gives an object with just these attributes.
PUBLIC_TABLE = """
AFTER esoi.optimization.keep_metric_record.metric_meter
Assembler esoi.runtime.assemble_by_name.assemble
Assembly esoi.runtime.assemble_by_name.assembly
AssemblyConfig esoi.runtime.assemble_by_name.assembly_config
AssemblyError esoi.runtime.assemble_by_name.assembly_errors
BEFORE esoi.optimization.keep_metric_record.metric_meter
BudgetExceeded esoi.optimization.when_metrics_are_run.paid_gating
CallMeter esoi.optimization.measurement_harness.call_meter
Config esoi.structure.intent_registry.config
ConsumerOptions esoi.runtime.consumer_check.consumer Options
EVERY_MOMENT esoi.optimization.keep_metric_record.metric_meter
EntryError esoi.runtime.assemble_by_name.entry_types
FileMetricLedger esoi.optimization.keep_metric_record.metric_results
Lazy esoi.runtime.assemble_by_name.lazy_need
MAX_METRICS esoi.optimization.keep_metric_record.metric_results
MetricIteration esoi.optimization.keep_metric_record.iteration
MetricLedger esoi.optimization.keep_metric_record.metric_results
MetricMeter esoi.optimization.keep_metric_record.metric_meter
MetricResult esoi.optimization.keep_metric_record.metric_results
NOT_RECORDED_LINE esoi.optimization.keep_metric_record.metric_results
Offline esoi.runtime.assemble_by_name.offline_guard
Pending esoi.runtime.assemble_by_name.entry_types
READING_STATUS esoi.optimization.keep_metric_record.iteration
Registry esoi.structure.intent_registry.registry
RepoSliceSource esoi.optimization.keep_metric_record.spec_slice
RequirementEntry esoi.runtime.assemble_by_name.environment_needs.declarations Entry
RuleContext esoi.structure.structure_check.rules.base Context
RuleGroup esoi.structure.structure_check.rules.base
RunError esoi.optimization.measurement_harness.run_errors
RunFiles esoi.optimization.keep_metric_record.metric_results
SOURCES esoi.optimization.keep_metric_record.metric_results
SOURCE_MEASURED esoi.optimization.keep_metric_record.metric_results
SOURCE_NOT_APPLICABLE esoi.optimization.keep_metric_record.metric_results
SOURCE_RECORDED esoi.optimization.keep_metric_record.metric_results
SliceSource esoi.optimization.keep_metric_record.spec_slice
SpecSlice esoi.optimization.keep_metric_record.spec_slice
TagTable esoi.understanding.spec_search.spec_search
assess_structure_quality esoi.structure.structure_check.rules.structure_quality_rules assess_path
assembly_plan esoi.runtime.assemble_by_name.installation.assembly_plan
call_entry esoi.runtime.assemble_by_name.entry
check_consumer esoi.runtime.consumer_check.consumer
check_headers esoi.structure.intent_registry.records
check_records esoi.structure.intent_registry.records
check_structure esoi.structure.structure_check.check check
compare_structure_quality esoi.structure.structure_check.rules.structure_quality_rules compare_refs
consumer_cases_hash esoi.runtime.consumer_check.consumer cases_hash
consumer_library_dir esoi.runtime.consumer_check.consumer library_dir
declared_entry esoi.runtime.assemble_by_name.target_lookup declared
describe_metric esoi.optimization.keep_metric_record.spec_slice
environ_declared esoi.runtime.assemble_by_name.environ_options
environ_fill esoi.runtime.assemble_by_name.environ_options
environ_lacking esoi.runtime.assemble_by_name.environ_options
first_arm esoi.structure.intent_registry.registry
format_value esoi.optimization.keep_metric_record.metric_results
harness_arms esoi.structure.intent_registry.registry
index_tokens esoi.understanding.spec_search.spec_index tokens
load esoi.structure.intent_registry.registry
load_cases esoi.optimization.measurement_harness.case_loading
load_template esoi.structure.intent_registry.records
meters_from_names esoi.optimization.keep_metric_record.metric_meter
own_code_paths esoi.optimization.measurement_harness.code_provenance
parse_tags esoi.structure.intent_registry.fields
payload_of esoi.optimization.keep_metric_record.metric_results
read_csv esoi.structure.intent_registry.tables
read_tree esoi.structure.intent_registry.intents
reconcile esoi.optimization.keep_metric_record.metric_results
record_fields esoi.structure.intent_registry.records fields
render_line esoi.optimization.keep_metric_record.metric_results
run_entry esoi.runtime.assemble_by_name.entry run
served_by_solution esoi.understanding.spec_search.spec_search
split_ids esoi.structure.intent_registry.tables ids
stratified_sample esoi.optimization.measurement_harness.case_loading
tables_of esoi.structure.intent_registry.records
targets esoi.runtime.assemble_by_name.entry
terms_of esoi.understanding.spec_search.spec_search
views_from_index esoi.understanding.spec_search.spec_search
views_from_items esoi.understanding.spec_search.spec_search
without_line esoi.optimization.keep_metric_record.metric_results
"""

NAMESPACES_TABLE = """
access esoi.optimization.measurement_harness.access violation
cascade esoi.optimization.leaderboard.cascade_stages load_stages,parse
cascade esoi.optimization.leaderboard.stage_standings stage_index
config esoi.structure.intent_registry.config load
declarations esoi.structure.intent_registry.specify_from_code.declarations code_files,drift,scan
entry esoi.runtime.assemble_by_name.entry build_handle,prepare,runner
entry esoi.runtime.assemble_by_name.entry_types Pending
entry esoi.runtime.assemble_by_name.intent_map snapshot
entry esoi.runtime.assemble_by_name.offline_guard Offline
entry esoi.runtime.assemble_by_name.readme_example run_block
evidence esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading estimates,lines_for_implementation
evidence esoi.optimization.when_metrics_are_run.public_evidence.evidence_ranking rank
evidence esoi.optimization.when_metrics_are_run.public_evidence.evidence_records EvidenceError,implementation_candidates,load,load_for
evidence_table esoi.optimization.leaderboard.evidence_table cell,cost_label,public_label,rate_label,seconds_label
expect esoi.optimization.measurement_harness.expect aggregate_by_kind,check,score_kind_case
foundation esoi.runtime.consumer_check.foundation declared,declared_arms,problems
harness esoi.optimization.leaderboard.case_identity cases_digest
harness esoi.optimization.measurement_harness.arm_loading load_impl
harness esoi.optimization.measurement_harness.call_meter CallMeter
harness esoi.optimization.measurement_harness.case_loading load_cases
harness esoi.optimization.measurement_harness.code_provenance current_sha
harness esoi.optimization.measurement_harness.component_folder prepare_path
harness esoi.optimization.measurement_harness.record_result record_result
harness esoi.optimization.measurement_harness.record_slices record_slices
harness esoi.optimization.measurement_harness.run_component run_component
harness esoi.optimization.when_metrics_are_run.paid_gating declares_paid,price_for
hermetic esoi.optimization.measurement_harness.hermetic from_config
hygiene esoi.structure.structure_check.hygiene repo_files,scan_repo,scan_text
intents esoi.structure.intent_registry.intents RECORD_FILES,discover,folders,read_rows,read_tree,tree_folders
leaderboard esoi.optimization.leaderboard.arm_kinds arm_kind,invariant_reason
leaderboard esoi.optimization.leaderboard.arm_selection selected_impls
leaderboard esoi.optimization.leaderboard.case_identity cases_digest
leaderboard esoi.optimization.leaderboard.held_out_parts part_of,part_row,selection_leader
leaderboard esoi.optimization.leaderboard.ranking pass_rate,passes,rank
leaderboard esoi.optimization.leaderboard.results_log all_results,is_partial,per_case_rows,slice_results
leaderboard esoi.optimization.leaderboard.rival_decisions best_guess,challengers,decisions
leaderboard esoi.optimization.leaderboard.switching_policy Policy,holdout_fraction,policies
leaderboard esoi.optimization.leaderboard.verdict_labels slice_verdicts
lock esoi.runtime.implementation_selection.lock diff,status,update,write
registry esoi.structure.intent_registry.registry load
requirements esoi.runtime.assemble_by_name.environment_needs.checking UNMET,check
requirements esoi.runtime.assemble_by_name.environment_needs.closure members_pairs
requirements esoi.runtime.assemble_by_name.environment_needs.declarations Api,Binary,Download,Entry,Env,Isolate,Python,Resource,Service,api,binary,declared,download,env,gather,isolatable,network,python,resource,service
requirements esoi.runtime.assemble_by_name.environment_needs.generated_files env_template
requirements esoi.runtime.assemble_by_name.environment_needs.report describe
scaffold esoi.understanding.the_standard.scaffold init
selection esoi.runtime.implementation_selection.declare override,register,resolve
selection esoi.runtime.implementation_selection.selection_cascade choose,env_name,names,snapshot
selection esoi.runtime.implementation_selection.selection_registry REGISTRY,SelectionError,entry_for
spec_index esoi.understanding.spec_search.spec_index build,cached,find_specs,of_intent,related,show,tokens
spec_search esoi.understanding.spec_search.spec_search Found,Gate,RECORD_CANDIDATE_KINDS,RECORD_SOURCE,Selection,TagTable,VectorSearch,View,fuse,gate_decision,gated,lexical_scored,render,search,terms_of,views_from_index,views_from_items
standards_nav esoi.understanding.spec_search.standards_nav MAX_SHOWN,lint,select_for_task
"""


def read_public(table: str) -> Dict[str, Tuple[str, str]]:
    """The flat names: name -> (module, attribute)."""
    rows = [line.split() for line in table.splitlines() if line.strip()]
    return {row[0]: (row[1], row[2] if len(row) > 2 else row[0]) for row in rows}


def read_namespaces(table: str) -> Dict[str, Dict[str, Tuple[str, ...]]]:
    """The namespaces: name -> {module: attributes}."""
    found: Dict[str, Dict[str, Tuple[str, ...]]] = {}
    for line in table.splitlines():
        if line.strip():
            space, module, attributes = line.split()
            found.setdefault(space, {})[module] = tuple(attributes.split(","))
    return found


PUBLIC: Dict[str, Tuple[str, str]] = read_public(PUBLIC_TABLE)
NAMESPACES: Dict[str, Dict[str, Tuple[str, ...]]] = read_namespaces(NAMESPACES_TABLE)

__all__ = sorted(["SelectionError", "implementation", "override", "register", "resolve", "solution", "run", "__version__", *PUBLIC, *NAMESPACES])


def run(target, input=None, **overrides):
    """One line for any solution or intent of esoi itself: ``esoi.run("structure-check", ".")``. Packages bind the same function
    to their own Assembler (``entry.runner``)."""
    from esoi.runtime.assemble_by_name.interface import own_runner
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
