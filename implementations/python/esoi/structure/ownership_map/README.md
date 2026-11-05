# Ownership Map

*ESOI records kept beside the code in `implementations/python/esoi/structure/ownership_map`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

A project's structure enables the continuous evolution of interdependent parts to optimize its intent.

These are the solutions of [A Project's Records and Code as One Structure](../README.md).

## How the solutions fit together

Structure keeps a project's records and code one true and lean whole. The Intent Registry holds every problem, solution, implementation, ideal and metric as linked records beside the code they describe. It takes its fields from the author's template through Template Sync and fills the rows the code already declares through Specify from the Code, leaving a person's words untouched. The Ownership Map ties every file to the solution it serves, so code that serves nothing has nowhere to hide. Structure Check runs every rule on each change, reading the files the Ownership Map assigns and the fields Template Sync reads from the template, and reports each finding by rule and path with the next action. Structure Budget weighs what the rules that Structure Check runs cost each change against the real mistakes they catch, admits a new rule only with the mistake that justifies it, and prunes what stops paying.

## Overview diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Intent Registry<br/><i>intent-registry</i>"]
    s1["Ownership Map<br/><i>ownership-map</i>"]
    s2["Structure Budget<br/><i>structure-budget</i>"]
    s3["Structure Check<br/><i>structure-check</i>"]
    s4["Specify from the Code<br/><i>specify-from-code</i>"]
    s5["Template Sync<br/><i>template-sync</i>"]
    s1 -->|"File-to-solution links and the generated component index"| s3
    s3 -->|"A list of violations, each led by its rule id, and an exit code"| s2
    s4 -->|"Findings (rule S30), the rows written, and for a new solution the records, a code skeleton and an evaluation folder"| s0
    s5 -->|"A committed field list per type"| s0
    s5 -->|"A committed field list per type"| s3
```

## Ownership Map (`ownership-map`)

Assign every file to exactly one component and every component to the solutions it serves, so code with no purpose cannot hide.

- Entry call: `esoi.run("ownership-map", '.')`
- Selected implementation: Component rows (`component-rows`)
- Metric: Trace completeness
- Implemented by: [`implementations/python/esoi/structure/ownership_map/interface.py`](interface.py), [`implementations/python/esoi/structure/structure_check/rules/layout.py`](../structure_check/rules/layout.py), [`implementations/python/evaluation/components/own_every_file/__init__.py`](../../../evaluation/components/own_every_file/__init__.py), [`implementations/python/evaluation/components/own_every_file/broken/__init__.py`](../../../evaluation/components/own_every_file/broken/__init__.py), [`implementations/python/evaluation/components/own_every_file/broken/coverage_only.py`](../../../evaluation/components/own_every_file/broken/coverage_only.py), [`implementations/python/evaluation/components/own_every_file/cases.json`](../../../evaluation/components/own_every_file/cases.json), [`implementations/python/evaluation/components/own_every_file/impls/__init__.py`](../../../evaluation/components/own_every_file/impls/__init__.py), [`implementations/python/evaluation/components/own_every_file/impls/live_checker.py`](../../../evaluation/components/own_every_file/impls/live_checker.py) and 2 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Component rows | `ownership-map:component-rows` | [`implementations/python/esoi/structure/ownership_map/interface.py`](interface.py) | selected |
| Ownership inferred from imports and declarations | `ownership-map:inferred-from-imports` | no code yet |  |

## Metrics

- Trace completeness (`metric-trace-completeness`): leader `live_checker`, 12 of 16 cases

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [A Project's Records and Code as One Structure](../README.md)
- Repository: [top README](../../../../../README.md)
