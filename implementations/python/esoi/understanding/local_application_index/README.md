# Local ESOI Index

**Purpose:** Find which projects ESOI is applied to, how they relate and where to look first in each.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../README.md) > Local ESOI Index

Part of [How People and Agents Come to Apply ESOI](../README.md)

## Local ESOI Index (`local-application-index`)

- Out of scope: Anything about a project beyond a pointer and its relations; which records inside a project bear on a request.
- Delegates to: spec-search
- Entry call: `esoi.run("local-application-index", '.')`
- Selected implementation: Index folder in the user's home (`live_index`)
- Metric: Local index lookup cases
- Implemented by: [`implementations/python/esoi/understanding/local_application_index/interface.py`](interface.py), [`implementations/python/esoi/understanding/local_application_index/projects.py`](projects.py), [`implementations/python/evaluation/components/index_projects/__init__.py`](../../../evaluation/components/index_projects/__init__.py), [`implementations/python/evaluation/components/index_projects/broken/__init__.py`](../../../evaluation/components/index_projects/broken/__init__.py), [`implementations/python/evaluation/components/index_projects/broken/guess_by_folder.py`](../../../evaluation/components/index_projects/broken/guess_by_folder.py), [`implementations/python/evaluation/components/index_projects/cases.json`](../../../evaluation/components/index_projects/cases.json), [`implementations/python/evaluation/components/index_projects/impls/__init__.py`](../../../evaluation/components/index_projects/impls/__init__.py), [`implementations/python/evaluation/components/index_projects/impls/live_index.py`](../../../evaluation/components/index_projects/impls/live_index.py) and 4 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Index folder in the user's home | `local-application-index:live_index` | A folder named by an environment variable, else a hidden folder in the home directory, holding one row per project and an index page generated from the rows between markers. | [`implementations/python/esoi/understanding/local_application_index/interface.py`](interface.py) | selected |
| Routing rows in the skill's index | `local-application-index:skill_rows` | Rows written into the skill's own index that say, for named projects, where to start and what they use. | [`implementations/python/evaluation/components/index_projects/impls/skill_rows.py`](../../../evaluation/components/index_projects/impls/skill_rows.py) |  |
| Each project's own records only | `local-application-index:records_only` | From a path, climb to the nearest configuration and read that project's own records. | [`implementations/python/evaluation/components/index_projects/impls/records_only.py`](../../../evaluation/components/index_projects/impls/records_only.py) |  |

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

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
