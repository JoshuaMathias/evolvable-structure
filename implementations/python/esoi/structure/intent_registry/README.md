# Intent Registry

*ESOI records kept beside the code in `implementations/python/esoi/structure/intent_registry`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

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

## Intent Registry (`intent-registry`)

Record every problem, solution, implementation, ideal and metric of a project as linked records that people and checks both read.

- Entry call: `esoi.run("intent-registry", '.')`
- Selected implementation: Records beside the code (`beside_code`)
- Metric: Navigable records, Record completeness
- Implemented by: [`esoi/COMPONENTS.md`](../../../../../esoi/COMPONENTS.md), [`esoi/components.csv`](../../../../../esoi/components.csv), [`esoi/esoi_template.csv`](../../../../../esoi/esoi_template.csv), [`esoi/metric-run-policy.md`](../../../../../esoi/metric-run-policy.md), [`esoi/network.md`](../../../../../esoi/network.md), [`esoi/standards/naming.md`](../../../../../esoi/standards/naming.md), [`esoi/standards/no-em-dash.md`](../../../../../esoi/standards/no-em-dash.md), [`esoi/standards/tags.csv`](../../../../../esoi/standards/tags.csv) and 33 more

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Intent Registry<br/><i>intent-registry</i>"]
    s1["Specify from the Code<br/><i>specify-from-code</i>"]
    s2["Template Sync<br/><i>template-sync</i>"]
    s1 -->|"Findings (rule S30), the rows written, and for a new solution the records, a code skeleton and an evaluation folder"| s0
    s2 -->|"A committed field list per type"| s0
```

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Records in the esoi folder | `intent-registry:esoi_folder` | [`implementations/python/esoi/structure/intent_registry/interface.py`](interface.py) |  |
| Records beside the code | `intent-registry:beside_code` | [`implementations/python/esoi/structure/intent_registry/interface.py`](interface.py) | selected |
| Sheet as source | `intent-registry:sheet-as-source` | no code yet |  |

## Metrics

- Record completeness (`metric-record-completeness`): leader `live_checker`, 11 of 14 cases
- Navigable records (`metric-navigable-records`): leader `beside_code`, 29 of 53 cases

## Problems

- Specification far from the code (`prob-spec-far-from-code`): A person reading the code of a solution cannot find its specification without leaving the code tree: the records sit in a separate folder, a code folder carries no page that says what it is for, and a change to the code and to its spec happen in two places.

## Ideals

- Navigable records (`ideal-navigable-records`): A person opening a code folder finds the specification of what it holds beside it, and a person opening a specification finds its code one folder away.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [A Project's Records and Code as One Structure](../README.md)
- Down: [implementations/python/esoi/structure/intent_registry/specify_from_code](specify_from_code/README.md)
- Down: [implementations/python/esoi/structure/intent_registry/template_sync](template_sync/README.md)
- Repository: [top README](../../../../../README.md)
