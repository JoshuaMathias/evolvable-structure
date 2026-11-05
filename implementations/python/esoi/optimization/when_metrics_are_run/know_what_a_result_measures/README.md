# Know What a Result Measures

*ESOI records kept beside the code in `implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

Solution implementations continuously improve through a pragmatic balance of measurement and efficient iteration.

These are the solutions of [Implementations Chosen on Evidence](../../README.md).

## How the solutions fit together

Optimization is how a project comes to run its best implementation on evidence. The Measurement Harness runs each implementation through the shipped code on its solution's cases and records every result with its commit, cases and cost, and it shows through Discriminating Cases that those cases can fail a naive implementation. The Measurement Harness leaves the decision to run to When Metrics Are Run, which says whether a run is worth what it costs. When Metrics Are Run relies on the answer of Know What a Result Measures to tell whether the code a result measured has changed, and it consults Grade Public Evidence before paying to measure what others already have. Grade Public Evidence reads the standings of the Implementation Leaderboard to weigh what others measured. The Measurement Harness hands its rows to the Implementation Leaderboard, which turns them into an honest verdict, calling a winner only beyond the noise. Promote the Winner switches a selection when the Implementation Leaderboard shows a clear winner among the rows the Measurement Harness recorded, or proposes the switch when a person must approve it. Keep a Metric Record reads the relevant metric before and after each piece of work and keeps both readings, so progress is judged from a ledger rather than a closing message.

## Overview diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Implementation Leaderboard<br/><i>leaderboard</i>"]
    s1["Measurement Harness<br/><i>measurement-harness</i>"]
    s2["Promote the Winner<br/><i>promote-the-winner</i>"]
    s3["When Metrics Are Run<br/><i>when-metrics-are-run</i>"]
    s4["Discriminating Cases<br/><i>discriminating-cases</i>"]
    s5["Know What a Result Measures<br/><i>know-what-a-result-measures</i>"]
    s6["Grade Public Evidence<br/><i>public-evidence</i>"]
    s0 -->|"A verdict per solution and a ranked board"| s1
    s0 -->|"A verdict per solution and a ranked board"| s2
    s0 -->|"A verdict per solution and a ranked board"| s6
    s1 -->|"A results row per run"| s2
    s3 -->|"A row per run in the results log with the commit and the hash of the cases; the strict check's verdict"| s1
    s4 -->|"A pass or fail per baseline"| s1
    s5 -->|"Stale or current for the row, the reason naming the changed file and its owner, and the files that were ignored with their owners"| s3
    s6 -->|"Dict(Tuple(str, str), Estimate)"| s3
```

## Know What a Result Measures (`know-what-a-result-measures`)

Tell, for one recorded result, whether the code, cases or circumstances it measures changed since its commit, and say which changed file and which component's ownership explains the answer.

- Entry call: `esoi.run("know-what-a-result-measures", '.')`
- Selected implementation: Import closure (`import_closure`)
- Metric: Staleness precision
- Implemented by: [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/attest.py`](attest.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/import_scan.py`](import_scan.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/import_world.py`](import_world.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/ownership_index.py`](ownership_index.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/stale_scope.py`](stale_scope.py), [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py), [`implementations/python/esoi/optimization/when_metrics_are_run/public_evidence/evidence_grading.py`](../public_evidence/evidence_grading.py), [`implementations/python/esoi/optimization/when_metrics_are_run/public_evidence/evidence_ranking.py`](../public_evidence/evidence_ranking.py) and 14 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Repo wide | `know-what-a-result-measures:repo_wide` | [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py) |  |
| Component paths | `know-what-a-result-measures:component_paths` | [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py) |  |
| Import closure | `know-what-a-result-measures:import_closure` | [`implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures/staleness.py`](staleness.py) | selected |

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
