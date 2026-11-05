# Assemble Parts by Name

**Purpose:** Build a program's parts from validated names in dependency order, so each part depends on a solution and never on one implementation, and check what each needs from its environment.

Breadcrumb: [Top](../../../../../esoi/README.md) > [ESOI Inside Other People's Running Code](../README.md) > Assemble Parts by Name

Part of [ESOI Inside Other People's Running Code](../README.md)

## Assemble Parts by Name (`assemble-by-name`)

- Out of scope: Choosing each part (it asks Implementation Selection); importing a module no record names.
- Delegates to: implementation-selection
- Entry call: `esoi.run("assemble-by-name", 'structure-check')`
- Selected implementation: Dependency-ordered assembler (`assembler`)
- Metric: Assembly by name cases
- Implemented by: [`implementations/python/esoi/runtime/assemble_by_name/assemble.py`](assemble.py), [`implementations/python/esoi/runtime/assemble_by_name/hierarchy.py`](hierarchy.py), [`implementations/python/esoi/runtime/assemble_by_name/interface.py`](interface.py), [`implementations/python/esoi/runtime/consumer_check/follow.py`](../consumer_check/follow.py), [`implementations/python/esoi/runtime/implementation_selection/lock.py`](../implementation_selection/lock.py), [`implementations/python/esoi/structure/structure_check/rules/hierarchy_rules.py`](../../structure/structure_check/rules/hierarchy_rules.py), [`implementations/python/evaluation/components/assemble_by_name/__init__.py`](../../../evaluation/components/assemble_by_name/__init__.py), [`implementations/python/evaluation/components/assemble_by_name/broken/__init__.py`](../../../evaluation/components/assemble_by_name/broken/__init__.py) and 6 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Dependency-ordered assembler | `assemble-by-name:assembler` | An Assembler over a package's solutions: it resolves each part by validated name through the cascade, builds the parts in dependency order and hands each typed need to the part that declares it. | [`implementations/python/esoi/runtime/assemble_by_name/interface.py`](interface.py) | selected |
| Dependency injection container | `assemble-by-name:injection-container` | An existing dependency injection library wires the parts from their types or import paths. | no code yet |  |

## Metrics

- Assembly by name cases (`metric-assemble-by-name`): leader `live_assembler`, 41 of 41 cases

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [ESOI Inside Other People's Running Code](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
