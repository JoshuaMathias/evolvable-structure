# Ownership Map

**Purpose:** Assign every file to exactly one component and every component to the solutions it serves, so code with no purpose cannot hide.

Breadcrumb: [Top](../../../../../esoi/README.md) > [A Project's Records and Code as One Structure](../README.md) > Ownership Map

Part of [A Project's Records and Code as One Structure](../README.md)

## Ownership Map (`ownership-map`)

- Out of scope: Describing what code does; deciding whether a part is worth its cost.
- Delegates to: intent-registry, structure-budget
- Entry call: `esoi.run("ownership-map", '.')`
- Selected implementation: Component rows (`component-rows`)
- Metric: Trace completeness
- Implemented by: [`implementations/python/esoi/structure/ownership_map/interface.py`](interface.py), [`implementations/python/esoi/structure/structure_check/rules/layout.py`](../structure_check/rules/layout.py), [`implementations/python/evaluation/components/own_every_file/__init__.py`](../../../evaluation/components/own_every_file/__init__.py), [`implementations/python/evaluation/components/own_every_file/broken/__init__.py`](../../../evaluation/components/own_every_file/broken/__init__.py), [`implementations/python/evaluation/components/own_every_file/broken/coverage_only.py`](../../../evaluation/components/own_every_file/broken/coverage_only.py), [`implementations/python/evaluation/components/own_every_file/cases.json`](../../../evaluation/components/own_every_file/cases.json), [`implementations/python/evaluation/components/own_every_file/impls/__init__.py`](../../../evaluation/components/own_every_file/impls/__init__.py), [`implementations/python/evaluation/components/own_every_file/impls/live_checker.py`](../../../evaluation/components/own_every_file/impls/live_checker.py) and 2 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Component rows | `ownership-map:component-rows` | `components.csv` lists each component's layer, path globs, role and solutions; the check matches every file to exactly one row. | [`implementations/python/esoi/structure/ownership_map/interface.py`](interface.py) | selected |
| Ownership inferred from imports and declarations | `ownership-map:inferred-from-imports` | Infers each file's solution from the declarations in the code and the import graph, with hand-written rows only for files nothing declares or imports. | no code yet |  |

## Metrics

- Trace completeness (`metric-trace-completeness`): leader `live_checker`, 12 of 16 cases

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [A Project's Records and Code as One Structure](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
