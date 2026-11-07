# Where each part of esoi lives

The top of `implementations/python/esoi/` shows four folders, the public entry points and the registry of the root and the
containers. Everything else sits beneath the solution it implements, next to the records that describe it.

```
implementations/python/esoi/
  understanding/     Understanding: how ESOI reaches the people and agents who apply it
  structure/         Structure: a project's records and code as one true and lean structure
  optimization/      Optimization: running the implementation the evidence shows is best
  runtime/           Runtime: ESOI inside other people's running programs
  apply_esoi.py      the root solution apply-esoi: its interface and its two arms
  __init__.py        the public API (solution, implementation, override, register, run, Assembler, ...)
  __main__.py        the `esoi` command: it collects the commands.py of each container
  data/              the bundled skill copy, the template CSV and the version stamp
  solutions.csv implementations.csv metrics.csv problems.csv ideals.csv   the root and the four container solutions
```

## The rule

A container folder holds one folder for each of its second-level solutions, an `intent.csv` (the container is a sub-intent of
the top intent), its own `solutions.csv` and the other record files where they have rows, the generated `README.md` (an intent page lists its children with their kinds; a leaf solution page lists only its implementations) and
`diagram.md`, its `interface.py` (the Protocol of the container, entry `review`) and its `flow.py`, which holds the container's
`composition` arm: the order in which it calls its parts, each one a typed `Lazy` need on the part's interface.

A solution's folder holds its records, the generated `README.md`, its `interface.py` (the Protocol the solution declares with
`@solution`, and the arm it ships) and the code of its arms, beside the records that name them in `filepath`. A solution that a
second-level solution's selected implementation names in `uses_solution_ids` is a third-level solution and has its own folder
inside it: `the_standard/the_steps`, `the_standard/skill_distribution`, `esoi_for_ai/esoi_behaviour_judge`,
`intent_registry/template_sync`, `intent_registry/specify_from_code`, `measurement_harness/discriminating_cases`,
`when_metrics_are_run/know_what_a_result_measures` and `when_metrics_are_run/public_evidence`.

- A container's id carries the prefix `esoi-` (`esoi-understanding`, `esoi-structure`, `esoi-optimization`, `esoi-runtime`),
  because the sub-intent of the same name has the folder and the id of a record may not equal an intent id (rule S29).
- Each container has a `commands.py` that holds the command-line behaviours of its parts; `__main__.py` only collects them.
- Helper code that belongs to no arm of its own sits in the lowest folder that all its users share, with a plain name
  (`runtime/assemble_by_name/environment_needs/`, `runtime/assemble_by_name/installation/`).
- Evaluation components stay in `implementations/python/evaluation/components/`, and a record whose arm lives there stays in the
  folder of its solution. The fixtures several components share (synthetic repositories, model arms) have one home,
  `implementations/python/evaluation/components/shared_fixtures/`, with `interface.py` as the way in.
- The rules of Structure Check stay together under `structure/structure_check/rules/`, because Structure Check owns the rule
  set.

## Four merges

| Was | Is |
|---|---|
| `docs-and-templates` (Documentation and Templates) | an arm of `the-standard`, with its metric |
| `structure-rules` (Structure Rules) | `structure-check` holds the rule set, `structure-budget` holds rule admission and pruning; `structure-check` is again named Structure Check |
| `spec-index` (Specification Index) | the lexical first stage of `spec-search`, its two arms and its metric are Spec Search's |
| `runtime-selection` (Selection at Run Time) | `implementation-selection`, with its selector as an arm and its metric merged into resolution correctness |

## Where things went

Modules moved without a change of behaviour, and the single `interfaces.py` became one `interface.py` per solution, beside its
code. Modules that were later split into several files keep their first name as the main file.

| Was | Is |
|---|---|
| `interfaces.py` | one `interface.py` per solution, `apply_esoi.py` for the root, and `<container>/interface.py` with `<container>/flow.py` for each container |
| `esoi-runtime/` (sub-intent) | `runtime/` (the Runtime container's sub-intent) |
| `docs.py` | `understanding/the_standard/docs.py` |
| `scaffold.py` | `understanding/the_standard/scaffold.py` |
| `skill.py` | `understanding/the_standard/skill_distribution/skill.py` |
| `readme.py` | `understanding/readable_records/readme.py` |
| `diagram.py` | `understanding/readable_records/diagram.py` |
| `tracker.py` | `understanding/review_tracker/tracker.py` |
| `sheets.py` | `understanding/review_tracker/sheets.py` |
| `spec_search.py` | `understanding/spec_search/spec_search.py` |
| `spec_index.py` | `understanding/spec_search/spec_index.py` |
| `standards_nav.py` | `understanding/spec_search/standards_nav.py` |
| `standards_measure.py` | `understanding/spec_search/standards_measure.py` |
| `projects.py` | `understanding/local_application_index/projects.py` |
| `behaviour.py` | `understanding/esoi_for_ai/behaviour.py` |
| `config.py` | `structure/intent_registry/config.py` |
| `records.py` | `structure/intent_registry/records.py` |
| `registry.py` | `structure/intent_registry/registry.py` |
| `tables.py` | `structure/intent_registry/tables.py` |
| `fields.py` | `structure/intent_registry/fields.py` |
| `intents.py` | `structure/intent_registry/intents.py` |
| `besidecode.py` | `structure/intent_registry/besidecode.py` |
| `implementedby.py` | `structure/intent_registry/implementedby.py` |
| `migrate.py` | `structure/intent_registry/migrate.py` |
| `admit.py` | `structure/intent_registry/admit.py` |
| `template.py` | `structure/intent_registry/template_sync/template.py` |
| `templates.py` | `structure/intent_registry/template_sync/templates.py` |
| `versioning.py` | `structure/intent_registry/template_sync/versioning.py` |
| `declarations.py` | `structure/intent_registry/specify_from_code/declarations.py` |
| `newsolution.py` | `structure/intent_registry/specify_from_code/newsolution.py` |
| `check.py` | `structure/structure_check/check.py` |
| `coherence.py` | `structure/structure_check/coherence.py` |
| `hygiene.py` | `structure/structure_check/hygiene.py` |
| `ratchet.py` | `structure/structure_check/ratchet.py` |
| `harness.py` | `optimization/measurement_harness/harness.py` |
| `hermetic.py` | `optimization/measurement_harness/hermetic.py` |
| `expect.py` | `optimization/measurement_harness/expect.py` |
| `cassette.py` | `optimization/measurement_harness/cassette.py` |
| `run_log.py` | `optimization/when_metrics_are_run/run_log.py` |
| `balance.py` | `optimization/measurement_harness/balance.py` |
| `access.py` | `optimization/measurement_harness/access.py` |
| `run_guards.py` | `optimization/when_metrics_are_run/run_guards.py` |
| `staleness.py` | `optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py` |
| `attest.py` | `optimization/when_metrics_are_run/know_what_a_result_measures/attest.py` |
| `evidence.py` | `optimization/when_metrics_are_run/public_evidence/evidence.py` |
| `leaderboard.py` | `optimization/leaderboard/leaderboard.py` |
| `stats.py` | `optimization/leaderboard/stats.py` |
| `cascade.py` | `optimization/leaderboard/cascade.py` |
| `circumstances.py` | `structure/intent_registry/circumstances.py` |
| `evidence_table.py` | `optimization/leaderboard/evidence_table.py` |
| `promote.py` | `optimization/promote_the_winner/promote.py` |
| `metric_meter.py` | `optimization/keep_metric_record/metric_meter.py` |
| `metric_results.py` | `optimization/keep_metric_record/metric_results.py` |
| `iteration.py` | `optimization/keep_metric_record/iteration.py` |
| `spec_slice.py` | `optimization/keep_metric_record/spec_slice.py` |
| `select.py` | `runtime/implementation_selection/select.py` |
| `variants.py` | `runtime/implementation_selection/variants.py` |
| `lock.py` | `runtime/implementation_selection/lock.py` |
| `assemble.py` | `runtime/assemble_by_name/assemble.py` |
| `entry.py` | `runtime/assemble_by_name/entry.py` |
| `hierarchy.py` | `runtime/assemble_by_name/hierarchy.py` |
| `requirements.py` | `runtime/assemble_by_name/requirements.py` |
| `installer.py` | `runtime/assemble_by_name/installer.py` |
| `consumer.py` | `runtime/consumer_check/consumer.py` |
| `follow.py` | `runtime/consumer_check/follow.py` |
| `foundation.py` | `optimization/measurement_harness/foundation_parts.py`, `optimization/when_metrics_are_run/know_what_a_result_measures/builds_on.py` and `optimization/leaderboard/inherited_gate.py` |
| `runtime.py` | `runtime/implementation_selection/declare.py` |
| `rules/` | `structure/structure_check/rules/` |

## Why it is shaped this way

Records beside code (`esoi records place --apply`) put each record in the folder of the code its row names, so moving code moves
its specification with it. The four containers are the four kinds of change that move a solution's scores: the author or the
readers (Understanding), the project's own records and code (Structure), new evidence (Optimization) and the programs that embed
the library (Runtime). A reader who opens a solution's folder finds what it is for, how it is measured and what runs it, in one
place, and the top of the package shows only what an outsider meets first. The `[records] beside_code` and `arm_folders` settings
of `esoi.toml` list the nested folders.
