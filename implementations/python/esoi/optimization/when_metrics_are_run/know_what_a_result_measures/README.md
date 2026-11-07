# Know What a Result Measures

**Purpose:** Tell, for one recorded result, whether the code, cases or circumstances it measures changed since its commit, and say which changed file and which component's ownership explains the answer.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [Implementations Chosen on Evidence](../../README.md) > [When Metrics Are Run](../README.md) > Know What a Result Measures

Part of [When Metrics Are Run](../README.md)

## Know What a Result Measures (`know-what-a-result-measures`)

- Out of scope: Deciding when a stale result is run again, and how the metric itself is implemented.
- Delegates to: when-metrics-are-run
- Entry call: `esoi.run("know-what-a-result-measures", '.')`
- Selected implementation: Import closure (`import_closure`)
- Metric: Staleness precision
- Implemented by: [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/attest.py`](attest.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/import_scan.py`](import_scan.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/import_world.py`](import_world.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/interface.py`](interface.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/ownership_index.py`](ownership_index.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/stale_scope.py`](stale_scope.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py), [`implementations/python/esoi/optimization/when_metrics_are_run/public_evidence/evidence_grading.py`](../public_evidence/evidence_grading.py) and 16 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Repo wide | `know-what-a-result-measures:repo_wide` | Any tracked file of the repository's code paths or evaluation folder that changed since the row's commit makes every row stale. | [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py) |  |
| Component paths | `know-what-a-result-measures:component_paths` | Only the files the arm's solution and implementation own in the ownership map (path globs mapped to solutions, the implementation records' files, a records folder that holds the solution's code alone, the component's evaluation folder and the shared fixtures) make the row stale; an unowned file counts for every arm and a component with no ownership entry keeps the whole-repository rule. | [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py) |  |
| Import closure | `know-what-a-result-measures:import_closure` | For a Python arm, the repository files its implementation module imports, transitively, found by reading the source (nothing is run), plus its evaluation folder; a changed file that is not Python, a non-Python arm or a computed import falls back to the component rule. | [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py) | selected |

## Metrics

- Staleness precision (`metric-staleness-precision`): leader `import_closure`, 46 of 55 cases

## Problems

- Results called stale when what they measure did not change (`prob-results-stale-when-nothing-measured-changed`): A recorded result is called stale when any file of the repository's measured code changed, so every component's metrics are re-run after every commit although what most of them measure did not change.

## Ideals

- Stale only when what it measures changed (`ideal-stale-only-when-measured-changed`): A recorded result goes stale if and only if the code, cases or circumstances it measures changed.

## Where to go next

- Up: [implementations/python/esoi/optimization/when_metrics_are_run](../README.md)
- Intent: [Implementations Chosen on Evidence](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
