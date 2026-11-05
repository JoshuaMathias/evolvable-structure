# Migrate a program from esoi 0.3 to 0.4

Version 0.4.0 moved every module of the package under four containers (`understanding`, `structure`, `optimization`, `runtime`) and
split the modules that were over 500 lines or did two jobs. A program that embeds esoi imports from the **public API**, `esoi/__init__.py`, which names
everything it may use and keeps those names stable when a module moves again. There are no aliases for the old paths, so each import
changes once.

## 1. Import from the public API

Replace each `from esoi.<module> import <name>` with `from esoi import <name>`, and each `from esoi import <module>` with the same name
(a namespace) unless the table below says otherwise:

| Was | Is |
|---|---|
| `from esoi import solution, implementation, override, register, resolve` | unchanged |
| `from esoi import runtime` | `from esoi import selection` (`selection.choose`, `selection.REGISTRY`, ...) |
| `from esoi.assemble import Assembler, AssemblyConfig, AssemblyError, Lazy` | `from esoi import Assembler, AssemblyConfig, AssemblyError, Lazy` |
| `from esoi.entry import Pending, Offline, EntryError` | `from esoi import Pending, Offline, EntryError` |
| `from esoi.entry import run` | `from esoi import run_entry` |
| `from esoi.entry import declared` | `from esoi import declared_entry` |
| `from esoi.requirements import env, api, binary, ...` | `from esoi import requirements`, then `requirements.env`, `requirements.api`, ... |
| `from esoi.tables import ids` | `from esoi import split_ids` |
| `from esoi.registry import load` | `from esoi import registry`, then `registry.load` |
| `from esoi.config import Config` | `from esoi import Config` |
| `from esoi.consumer import Options, cases_hash, library_dir` | `from esoi import ConsumerOptions, consumer_cases_hash, consumer_library_dir` |
| `import esoi.check` (`esoi.check.check`) | `from esoi import check_structure` |

`from esoi import config, registry, harness, leaderboard, cascade, evidence, evidence_table, intents, spec_search, spec_index, declarations, expect, hygiene, foundation,
access, lock, scaffold, standards_nav, entry` keep their names as namespaces; the attributes each one carries are listed in `esoi.NAMESPACES`.
The complete mapping, one line per name a known consumer imports, is in the release notes of the change.

If a name you need is not public, it is internal: ask for it to be added to `PUBLIC` in `esoi/__init__.py` (with a case in
`tests/test_public_api.py`) instead of importing the module that holds it.

## 2. Commands

| Was | Is |
|---|---|
| `python -m esoi.coherence` | `python -m esoi.structure.structure_check.coherence` |
| `python -m esoi.standards_nav` | `python -m esoi.understanding.spec_search.standards_nav` |
| `python -m esoi.entry` | `python -m esoi.runtime.assemble_by_name.entry_cli` |
| `python -m esoi (the esoi command)` | unchanged |

The `esoi` console script is now `esoi.__main__:main`; reinstall (`pip install -e implementations/python`, or upgrade the wheel) so the script
is regenerated, or run `python -m esoi` meanwhile.

## 3. Where each module went

For code that reads esoi's own files, or documents that name them:

| Was `esoi.` | Is `esoi.` |
|---|---|
| `access` | `optimization.measurement_harness.access` |
| `admit` | `structure.intent_registry.admit` |
| `assemble` | `runtime.assemble_by_name.{arm_inspection, arm_ranking, assemble, assembly, assembly_config, assembly_errors, build_parts, cascade_layers, closure, declared_needs, dependency_graph, environ_options, lazy_need, name_check, packaged_records, pending_needs}` |
| `attest` | `optimization.when_metrics_are_run.know_what_a_result_measures.attest` |
| `balance` | `optimization.measurement_harness.balance` |
| `behaviour` | `understanding.esoi_for_ai.{behaviour, command_provider, esoi_behaviour_judge.behaviour_judge}` |
| `besidecode` | `structure.intent_registry.besidecode` |
| `cascade` | `optimization.leaderboard.{cascade_report, cascade_stages, stage_standings}` |
| `cassette` | `optimization.measurement_harness.cassette` |
| `check` | `structure.structure_check.check` |
| `circumstances` | `optimization.leaderboard.circumstances` |
| `coherence` | `structure.structure_check.{coherence, coherence_code_evidence, coherence_paragraph, coherence_records}` |
| `config` | `structure.intent_registry.config` |
| `consumer` | `runtime.consumer_check.consumer` |
| `declarations` | `structure.intent_registry.specify_from_code.declarations` |
| `diagram` | `understanding.readable_records.diagram` |
| `docs` | `understanding.the_standard.docs` |
| `entry` | `runtime.assemble_by_name.{entry, entry_check, entry_cli, entry_outcome, entry_types, intent_map, offline_guard, project_runner, readme_example, seat_blockers, target_lookup}` |
| `evidence` | `optimization.when_metrics_are_run.public_evidence.{evidence_grading, evidence_ranking, evidence_records, evidence_report, grading_table}` |
| `evidence_table` | `optimization.leaderboard.evidence_table` |
| `expect` | `optimization.measurement_harness.expect` |
| `fields` | `structure.intent_registry.fields` |
| `follow` | `runtime.consumer_check.follow` |
| `foundation` | `runtime.consumer_check.foundation` |
| `harness` | `optimization.measurement_harness.harness` |
| `hermetic` | `optimization.measurement_harness.hermetic` |
| `hierarchy` | `runtime.assemble_by_name.hierarchy` |
| `hygiene` | `structure.structure_check.hygiene` |
| `implementedby` | `structure.intent_registry.implementedby` |
| `installer` | `runtime.assemble_by_name.installation.{assembly_plan, command_running, conflicts, execution, install_lock, plan, plan_report, resolution_ladder, resolvers}` |
| `intents` | `structure.intent_registry.intents` |
| `iteration` | `optimization.keep_metric_record.iteration` |
| `leaderboard` | `optimization.leaderboard.{arm_kinds, arm_selection, board_report, case_identity, held_out_parts, ranking, results_log, rival_decisions, rival_pairing, switching_policy, verdict_labels}` |
| `lock` | `runtime.implementation_selection.lock` |
| `metric_meter` | `optimization.keep_metric_record.metric_meter` |
| `metric_results` | `optimization.keep_metric_record.metric_results` |
| `migrate` | `structure.intent_registry.migrate` |
| `newsolution` | `structure.intent_registry.specify_from_code.newsolution` |
| `projects` | `understanding.local_application_index.projects` |
| `promote` | `optimization.promote_the_winner.promote` |
| `ratchet` | `structure.structure_budget.ratchet` |
| `readme` | `understanding.readable_records.{readme, readme_folder_page, readme_intent_page, readme_view}` |
| `records` | `structure.intent_registry.records` |
| `registry` | `structure.intent_registry.registry` |
| `requirements` | `runtime.assemble_by_name.environment_needs.{api_links, checking, closure, declarations, generated_files, python_specs, report, source_location}` |
| `rules` | `structure.structure_check.rules` (the whole folder) |
| `run_guards` | `optimization.when_metrics_are_run.run_guards` |
| `run_log` | `optimization.measurement_harness.run_log` |
| `runtime` | `runtime.implementation_selection.{declare, selection_cascade, selection_registry}` |
| `scaffold` | `understanding.the_standard.scaffold` |
| `select` | `runtime.implementation_selection.select` |
| `sheets` | `understanding.review_tracker.sheets` |
| `skill` | `understanding.the_standard.skill_distribution.skill` |
| `spec_index` | `understanding.spec_search.spec_index` |
| `spec_search` | `understanding.spec_search.spec_search` |
| `spec_slice` | `optimization.keep_metric_record.spec_slice` |
| `staleness` | `optimization.when_metrics_are_run.know_what_a_result_measures.{import_scan, import_world, ownership_index, stale_scope, staleness}` |
| `standards_measure` | `understanding.spec_search.standards_measure` |
| `standards_nav` | `{structure.structure_check.standards_check, understanding.spec_search.standards_nav}` |
| `stats` | `optimization.leaderboard.stats` |
| `tables` | `structure.intent_registry.tables` |
| `template` | `structure.intent_registry.template_sync.template` |
| `templates` | `structure.intent_registry.template_sync.templates` |
| `tracker` | `understanding.review_tracker.tracker` |
| `variants` | `runtime.implementation_selection.variants` |
| `versioning` | `structure.intent_registry.template_sync.versioning` |
| `interfaces` | one interface.py per solution beside its code (esoi.<container>.<solution>.interface), the root in esoi.apply_esoi |
| `cli` | esoi.__main__ (main, build_parser) plus esoi.<container>.commands (register) per container |

## 4. A repository that adopts esoi's records

Nothing changes in the records format. A repository that lists esoi's `esoi-runtime` sub-intent as a parent by id now finds it as the
container `esoi-runtime` (its folder is `runtime/`). The merged solutions are `docs-and-templates` (now `the-standard`), `structure-rules`
(`structure-check`), `spec-index` (`spec-search`) and `runtime-selection` (`implementation-selection`).
