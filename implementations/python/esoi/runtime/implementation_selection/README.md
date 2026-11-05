# Implementation Selection

**Purpose:** Choose which implementation serves a call, by a per-call name, an override, the environment, the lock or the recorded default, and refuse an unknown name by listing the valid choices.

Breadcrumb: [Top](../../../../../esoi/README.md) > [ESOI Inside Other People's Running Code](../README.md) > Implementation Selection

Part of [ESOI Inside Other People's Running Code](../README.md)

## Implementation Selection (`implementation-selection`)

- Out of scope: Deciding which is best; branching at every call site.
- Delegates to: leaderboard, promote-the-winner
- Entry call: `esoi.run("implementation-selection", 'structure-check')`
- Selected implementation: Declarations in code (`declarations`)
- Metric: Resolution correctness
- Implemented by: [`implementations/python/esoi/__main__.py`](../../__main__.py), [`implementations/python/esoi/esoi_selection.json`](../../esoi_selection.json), [`implementations/python/esoi/optimization/leaderboard/arm_kinds.py`](../../optimization/leaderboard/arm_kinds.py), [`implementations/python/esoi/optimization/leaderboard/arm_selection.py`](../../optimization/leaderboard/arm_selection.py), [`implementations/python/esoi/optimization/leaderboard/board_report.py`](../../optimization/leaderboard/board_report.py), [`implementations/python/esoi/optimization/leaderboard/cascade_report.py`](../../optimization/leaderboard/cascade_report.py), [`implementations/python/esoi/optimization/leaderboard/cascade_stages.py`](../../optimization/leaderboard/cascade_stages.py), [`implementations/python/esoi/optimization/leaderboard/case_identity.py`](../../optimization/leaderboard/case_identity.py) and 71 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Declarations in code | `implementation-selection:declarations` | Each implementation is declared where its code is (`@implementation`, or `register` for an object that cannot carry a decorator), and the records list the same implementations with the path of their module, so there is no second list to keep. A call runs the implementation one cascade chooses (per call, context, environment, deployment, then the solution's selected cell in the records), importing it lazily. A selection table written by hand still works underneath. The Runtime container grows from this arm. | [`implementations/python/esoi/runtime/implementation_selection/interface.py`](interface.py) | selected |
| Entry-point plugins | `implementation-selection:entry-point-plugins` | Implementations register through Python package entry points. | no code yet |  |
| Selector class and table | `implementation-selection:select` | The selector class in `esoi/runtime/implementation_selection/select.py`: a pure-data table lists each solution's implementations and default, and a resolver turns a name, an override or the default into the class, importing it lazily. | [`implementations/python/esoi/runtime/implementation_selection/select.py`](select.py) |  |

## Metrics

- Resolution correctness (`metric-resolution-correctness`): leader `live_selector`, 32 of 32 cases

## Problems

- Selection default kept twice (`prob-selection-default-kept-twice`): The default implementation of a solution is written in the selection table and again in the records, and only a check holds the two equal.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [ESOI Inside Other People's Running Code](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
