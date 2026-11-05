# When Metrics Are Run

*ESOI records kept beside the code in `implementations/python/esoi/optimization/when_metrics_are_run`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

Solution implementations continuously improve through a pragmatic balance of measurement and efficient iteration.

These are the solutions of [Implementations Chosen on Evidence](../README.md).

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

## When Metrics Are Run (`when-metrics-are-run`)

Decide when each metric is run, in what stages, with what limit, who approves the spend, and when its result stops counting.

- Entry call: `esoi.run("when-metrics-are-run", '.')`
- Selected implementation: On a decision (`on-a-decision`)
- Metric: Decisions backed by current results
- Implemented by: [`.github/workflows/check.yml`](../../../../../.github/workflows/check.yml), [`implementations/python/esoi/optimization/when_metrics_are_run/interface.py`](interface.py), [`implementations/python/evaluation/components/assemble_fixture.py`](../../../evaluation/components/assemble_fixture.py), [`implementations/python/evaluation/components/consumer_fixture.py`](../../../evaluation/components/consumer_fixture.py), [`implementations/python/evaluation/components/glance_fixture.py`](../../../evaluation/components/glance_fixture.py), [`implementations/python/evaluation/components/harness_fixture.py`](../../../evaluation/components/harness_fixture.py), [`implementations/python/evaluation/components/index_world.py`](../../../evaluation/components/index_world.py), [`implementations/python/evaluation/components/know_stale_results/__init__.py`](../../../evaluation/components/know_stale_results/__init__.py) and 14 more

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["When Metrics Are Run<br/><i>when-metrics-are-run</i>"]
    s1["Know What a Result Measures<br/><i>know-what-a-result-measures</i>"]
    s2["Grade Public Evidence<br/><i>public-evidence</i>"]
    s1 -->|"Stale or current for the row, the reason naming the changed file and its owner, and the files that were ignored with their owners"| s0
    s2 -->|"Dict(Tuple(str, str), Estimate)"| s0
```

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| On a decision | `when-metrics-are-run:on-a-decision` | [`implementations/python/esoi/optimization/when_metrics_are_run/interface.py`](interface.py) | selected |
| On every change | `when-metrics-are-run:on-every-change` | no code yet |  |
| On a schedule | `when-metrics-are-run:on-a-schedule` | no code yet |  |
| On drift | `when-metrics-are-run:on-drift` | no code yet |  |

## Metrics

- Decisions backed by current results (`metric-decisions-backed-by-current-results`): leader `live_checker`, 10 of 16 cases

## Problems

- Metrics run at the wrong time (`prob-metrics-run-at-the-wrong-time`): Results are stale when a choice depends on them, or paid runs happen with no decision behind them, so people either decide on numbers that no longer describe the code or stop running the metrics at all.

## Ideals

- Timely affordable evidence (`ideal-timely-affordable-evidence`): Every choice between alternatives is backed by a current result, and what it cost to get was proportionate to the choice and approved.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [Implementations Chosen on Evidence](../README.md)
- Down: [implementations/python/esoi/optimization/when_metrics_are_run/know_what_a_result_measures](know_what_a_result_measures/README.md)
- Down: [implementations/python/esoi/optimization/when_metrics_are_run/public_evidence](public_evidence/README.md)
- Repository: [top README](../../../../../README.md)
