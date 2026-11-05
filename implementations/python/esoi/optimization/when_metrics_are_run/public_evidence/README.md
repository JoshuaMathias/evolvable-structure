# Grade Public Evidence

*ESOI records kept beside the code in `implementations/python/esoi/optimization/when_metrics_are_run/public_evidence`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

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

## Grade Public Evidence (`public-evidence`)

Grade what others have measured about a candidate, so a measurement that costs money is made only when outside evidence cannot settle the question.

- Entry call: `esoi.run("public-evidence", {'evidence': []})`
- Selected implementation: Letter grades by weighted evidence (`graded`)
- Metric: Public evidence graded
- Implemented by: [`implementations/python/esoi/optimization/when_metrics_are_run/public_evidence/evidence_grading.py`](evidence_grading.py), [`implementations/python/evaluation/components/public_evidence/__init__.py`](../../../../evaluation/components/public_evidence/__init__.py), [`implementations/python/evaluation/components/public_evidence/broken/__init__.py`](../../../../evaluation/components/public_evidence/broken/__init__.py), [`implementations/python/evaluation/components/public_evidence/broken/trust_the_number.py`](../../../../evaluation/components/public_evidence/broken/trust_the_number.py), [`implementations/python/evaluation/components/public_evidence/cases.json`](../../../../evaluation/components/public_evidence/cases.json), [`implementations/python/evaluation/components/public_evidence/impls/__init__.py`](../../../../evaluation/components/public_evidence/impls/__init__.py), [`implementations/python/evaluation/components/public_evidence/impls/graded.py`](../../../../evaluation/components/public_evidence/impls/graded.py), [`implementations/python/evaluation/components/public_evidence/impls/live.py`](../../../../evaluation/components/public_evidence/impls/live.py) and 2 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Letter grades by weighted evidence | `public-evidence:graded` | [`implementations/python/esoi/optimization/when_metrics_are_run/public_evidence/evidence_grading.py`](evidence_grading.py) | selected |
| A model summarizes the sources | `public-evidence:model-summary` | no code yet |  |

## Metrics

- Public evidence graded (`metric-public-evidence`): leader `graded`, 11 of 11 cases

## Where to go next

- Up: [implementations/python/esoi/optimization/when_metrics_are_run](../README.md)
- Intent: [Implementations Chosen on Evidence](../../README.md)
- Repository: [top README](../../../../../../README.md)
