# Local ESOI Index

*ESOI records kept beside the code in `implementations/python/esoi/understanding/local_application_index`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

Documentation ensures that an intent is optimally carried out.

These are the solutions of [How People and Agents Come to Apply ESOI](../README.md).

## How the solutions fit together

Understanding is how ESOI reaches the people and agents who apply it. The Standard teaches anyone how a solution is shaped and how a project adopts it, with templates to fill in by hand, and for the order of the work it relies on The ESOI Steps. The Standard also ships the author's skill through Skill Distribution, which publishes a complete public copy that cannot leak or go stale. ESOI Applied to AI Behaviour gives an agent the principles as standing instructions and measures, case by case, whether its replies act on them, asking the ESOI Behaviour Judge to grade what a pattern cannot settle. When a reader needs one part of a project, three parts help. Readable Records gives every intent folder a page made from its records. Spec Search finds the records and standards a request concerns. The Local ESOI Index says which projects apply ESOI and where to look first in each. The Review Tracker puts the whole intent network and its latest results in front of a reviewer and carries the reviewer's edits back to the records, so people steer by metrics without reading the code.

## Overview diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["ESOI Applied to AI Behaviour<br/><i>esoi-for-ai</i>"]
    s1["The Standard<br/><i>the-standard</i>"]
    s2["ESOI Behaviour Judge<br/><i>esoi-behaviour-judge</i>"]
    s3["Skill Distribution<br/><i>skill-distribution</i>"]
    s4["The ESOI Steps<br/><i>the-steps</i>"]
    s2 -->|"A verdict (pass or fail) and a one-line reason"| s0
    s3 -->|"A public skill folder, a plugin manifest and marketplace file, and an installed copy"| s1
    s4 -->|"Linked records, a checked metric, measured implementations and a recorded selection; a short summary of how the steps were applied"| s1
```

## Local ESOI Index (`local-application-index`)

Find which projects ESOI is applied to, how they relate and where to look first in each.

- Entry call: `esoi.run("local-application-index", '.')`
- Selected implementation: Index folder in the user's home (`live_index`)
- Metric: Local index lookup cases
- Implemented by: [`implementations/python/esoi/understanding/local_application_index/interface.py`](interface.py), [`implementations/python/esoi/understanding/local_application_index/projects.py`](projects.py), [`implementations/python/evaluation/components/index_projects/__init__.py`](../../../evaluation/components/index_projects/__init__.py), [`implementations/python/evaluation/components/index_projects/broken/__init__.py`](../../../evaluation/components/index_projects/broken/__init__.py), [`implementations/python/evaluation/components/index_projects/broken/guess_by_folder.py`](../../../evaluation/components/index_projects/broken/guess_by_folder.py), [`implementations/python/evaluation/components/index_projects/cases.json`](../../../evaluation/components/index_projects/cases.json), [`implementations/python/evaluation/components/index_projects/impls/__init__.py`](../../../evaluation/components/index_projects/impls/__init__.py), [`implementations/python/evaluation/components/index_projects/impls/live_index.py`](../../../evaluation/components/index_projects/impls/live_index.py) and 4 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Index folder in the user's home | `local-application-index:live_index` | [`implementations/python/esoi/understanding/local_application_index/interface.py`](interface.py) | selected |
| Routing rows in the skill's index | `local-application-index:skill_rows` | [`implementations/python/evaluation/components/index_projects/impls/skill_rows.py`](../../../evaluation/components/index_projects/impls/skill_rows.py) |  |
| Each project's own records only | `local-application-index:records_only` | [`implementations/python/evaluation/components/index_projects/impls/records_only.py`](../../../evaluation/components/index_projects/impls/records_only.py) |  |

## Metrics

- Local index lookup cases (`metric-local-index-lookup`): leader `live_index`, 10 of 10 cases

## Problems

- Applied structure is rediscovered (`prob-applied-structure-is-rediscovered`): Where ESOI is already applied, how those projects relate and where to look in each is rediscovered in every session.

## Ideals

- Found structure (`ideal-found-structure`): Structure that already exists is found and reused instead of rediscovered.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../README.md)
- Repository: [top README](../../../../../README.md)
