# Structure Check

*ESOI records kept beside the code in `implementations/python/esoi/structure/structure_check`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

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

## Structure Check (`structure-check`)

Run every structural rule on each change and report each finding by rule and path with its next action, quickly enough that nobody skips it.

- Entry call: `esoi.run("structure-check", '.')`
- Selected implementation: Rule script (`rule-script`)
- Metric: Violation detection, Check dependability
- Implemented by: [`implementations/python/conftest.py`](../../../conftest.py), [`implementations/python/docs/configuration.md`](../../../docs/configuration.md), [`implementations/python/docs/evaluation-components.md`](../../../docs/evaluation-components.md), [`implementations/python/docs/rules.md`](../../../docs/rules.md), [`implementations/python/esoi/__main__.py`](../../__main__.py), [`implementations/python/esoi/esoi_selection.json`](../../esoi_selection.json), [`implementations/python/esoi/runtime/assemble_by_name/arm_inspection.py`](../../runtime/assemble_by_name/arm_inspection.py), [`implementations/python/esoi/runtime/assemble_by_name/arm_ranking.py`](../../runtime/assemble_by_name/arm_ranking.py) and 159 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Rule script | `structure-check:rule-script` | [`implementations/python/esoi/structure/structure_check/interface.py`](interface.py) | selected |
| Rules as linter plugins | `structure-check:linter-plugins` | no code yet |  |
| Rules in prose | `structure-check:prose-rules` | no code yet |  |

## Metrics

- Violation detection (`metric-violation-detection`): leader `live_checker`, 61 of 76 cases
- Check dependability (`metric-check-dependability`): leader `live_checker`, 61 of 76 cases

## Problems

- Structure rules decay (`prob-structure-rules-decay`): Rules written in prose (where files go, which way imports point, what must be documented) are followed by whoever read them and broken by the next agent, and generated documents drift from what they describe.

## Ideals

- Self-evolving structure (`ideal-self-evolving-structure`): The structure notices where it falls short and improves itself at the moment a change makes it worse.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [A Project's Records and Code as One Structure](../README.md)
- Repository: [top README](../../../../../README.md)
