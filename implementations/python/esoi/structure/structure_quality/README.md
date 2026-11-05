# Structure Quality

**Purpose:** Measure how well a project divides its work into solutions and parts, as one balanced number with the worst offenders named, before and after code exists.

Breadcrumb: [Top](../../../../../esoi/README.md) > [A Project's Records and Code as One Structure](../README.md) > Structure Quality

Part of [A Project's Records and Code as One Structure](../README.md)

## Structure Quality (`structure-quality`)

- Out of scope: Running the structural rules on each change; deciding whether a rule earns its place; the correctness of what any one part produces; deciding that a solution's purpose is worth having.
- Delegates to: structure-check, structure-budget
- Entry call: `esoi.run("structure-quality", 'docs')`
- Selected implementation: Balanced static scorer (`balanced_static`)
- Metric: Structure quality agreement
- Implemented by: [`implementations/python/esoi/structure/structure_check/rules/structure_quality_rules.py`](../structure_check/rules/structure_quality_rules.py), [`implementations/python/esoi/structure/structure_quality/adopted.py`](adopted.py), [`implementations/python/esoi/structure/structure_quality/assess.py`](assess.py), [`implementations/python/esoi/structure/structure_quality/balance.py`](balance.py), [`implementations/python/esoi/structure/structure_quality/behavior.py`](behavior.py), [`implementations/python/esoi/structure/structure_quality/cochange.py`](cochange.py), [`implementations/python/esoi/structure/structure_quality/compare.py`](compare.py), [`implementations/python/esoi/structure/structure_quality/complexity.py`](complexity.py) and 23 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Balanced static scorer | `structure-quality:balanced_static` | Scores how well a project divides its work into solutions and parts as one balanced number: seven dimensions read from the code and records without a model, each a share inside a budget (graded by how far over it a part goes for size, with imports of the project's shared kernel told apart from reach-ins), folded by a geometric mean within a dimension and a fixed weighted mean across them; stage two adds co-change mined from git history to the coupling dimension. | [`implementations/python/esoi/structure/structure_quality/interface.py`](interface.py) | selected |
| File size only | `structure-quality:file_size_only` | Scores how well a project divides its work into solutions and parts as one number from the size dimension alone: functions, modules, folders and depth inside their budgets, with nothing about coupling, copies, scope or behavior. | [`implementations/python/esoi/structure/structure_quality/interface.py`](interface.py) |  |
| Expert scoping review | `structure-quality:expert_review` | Scores how well a project divides its work into solutions and parts as one number from an expert model's judgement: it reads an outline of the project (units, files, sizes, imports) and scores each dimension with offenders in the same report shape; it needs a provider, costs a call per project and is run only with Joshua's approval. | [`implementations/python/esoi/structure/structure_quality/interface.py`](interface.py) |  |

## Metrics

- Structure quality agreement (`metric-structure-quality-agreement`): leader `balanced_static`, 41 of 41 cases

## Problems

- Scope and modularity drift (`prob-scope-and-modularity-drift`): Code and records that were divided well when written lose their shape as people and AI add to them: a package tree reached about a thousand files in one folder, a solution list of 74 records held 33 functions over 150 lines, a merge left a family of arms that define no method of their solution's interface, a library came to name its one consumer, and the same due-date arithmetic was written out in six places.

## Ideals

- Well-divided work (`ideal-well-divided-work`): Each solution has one job, each part is small enough to read whole, and parts connect only through what they declare.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [A Project's Records and Code as One Structure](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
