# Template Sync

**Purpose:** Derive the registry's fields from the intent template in the skill so the author's wording stays the single definition.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [A Project's Records and Code as One Structure](../../README.md) > [Intent Registry](../README.md) > Template Sync

Part of [Intent Registry](../README.md)

## Template Sync (`template-sync`)

- Out of scope: Interpreting or extending the template.
- Entry call: `esoi.run("template-sync", '.')`
- Selected implementation: Template parser (`template-parser`)
- Metric: Template agreement
- Implemented by: [`implementations/python/esoi/__main__.py`](../../../__main__.py), [`implementations/python/esoi/data/esoi_template.csv`](../../../data/esoi_template.csv), [`implementations/python/esoi/data/skill_version.json`](../../../data/skill_version.json), [`implementations/python/esoi/structure/intent_registry/template_sync/interface.py`](interface.py), [`implementations/python/esoi/structure/intent_registry/template_sync/template.py`](template.py), [`implementations/python/esoi/structure/intent_registry/template_sync/templates.py`](templates.py), [`implementations/python/esoi/structure/intent_registry/template_sync/versioning.py`](versioning.py), [`implementations/python/esoi/structure/structure_check/rules/generated.py`](../../structure_check/rules/generated.py) and 9 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Template parser | `template-sync:template-parser` | A script reads the intent template's sections and fields from `SKILL.md` and writes the committed field list. | [`implementations/python/esoi/structure/intent_registry/template_sync/interface.py`](interface.py) | selected |
| Hand-kept field list | `template-sync:hand-kept-field-list` | Someone copies the template's fields into a schema when the template changes. | no code yet |  |

## Metrics

- Template agreement (`metric-template-agreement`): leader `live_parser`, 11 of 11 cases

## Problems

- Template copies drift (`prob-template-copies-drift`): The intent template is being refined in the skill, and every registry and checker that copied its fields falls out of date.

## Ideals

- Living template (`ideal-living-template`): When the template's author refines it, every record and every tool that reads records follows.

## Where to go next

- Up: [implementations/python/esoi/structure/intent_registry](../README.md)
- Intent: [A Project's Records and Code as One Structure](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
