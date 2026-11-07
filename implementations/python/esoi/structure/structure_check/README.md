# Structure Check

**Purpose:** Run every structural rule on each change and report each finding by rule and path with its next action, quickly enough that nobody skips it.

Breadcrumb: [Top](../../../../../esoi/README.md) > [A Project's Records and Code as One Structure](../README.md) > Structure Check

Part of [A Project's Records and Code as One Structure](../README.md)

## Structure Check (`structure-check`)

- Out of scope: Deciding whether a rule earns its place; judging quality beyond the rules.
- Delegates to: structure-budget, ownership-map
- Entry call: `esoi.run("structure-check", '.')`
- Selected implementation: Rule script (`rule-script`)
- Metric: Violation detection, Check dependability
- Implemented by: [`implementations/python/conftest.py`](../../../conftest.py), [`implementations/python/docs/configuration.md`](../../../docs/configuration.md), [`implementations/python/docs/evaluation-components.md`](../../../docs/evaluation-components.md), [`implementations/python/docs/rules.md`](../../../docs/rules.md), [`implementations/python/esoi/__main__.py`](../../__main__.py), [`implementations/python/esoi/command_table.py`](../../command_table.py), [`implementations/python/esoi/esoi_selection.json`](../../esoi_selection.json), [`implementations/python/esoi/runtime/assemble_by_name/arm_inspection.py`](../../runtime/assemble_by_name/arm_inspection.py) and 171 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Rule script | `structure-check:rule-script` | `esoi check` runs every registered rule group, the numbered rule modules, over the tree, registry and results, with strict mode, disabled ids, plugins and waivers; each finding is led by its rule id and path and says its next action. | [`implementations/python/esoi/structure/structure_check/interface.py`](interface.py) | selected |
| Rules as linter plugins | `structure-check:linter-plugins` | Runs each rule as a plugin of a linter people already use, so violations show in the editor and in existing hooks. | no code yet |  |
| Rules in prose | `structure-check:prose-rules` | The rules written in the standard document and followed by whoever read it, with code review as the check. | no code yet |  |

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

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
