# Implementation Leaderboard

**Purpose:** Decide from recorded results which implementation is best, or whether they tie.

Breadcrumb: [Top](../../../../../esoi/README.md) > [Implementations Chosen on Evidence](../README.md) > Implementation Leaderboard

Part of [Implementations Chosen on Evidence](../README.md)

## Implementation Leaderboard (`leaderboard`)

- Out of scope: Running; switching the selection.
- Delegates to: measurement-harness, promote-the-winner
- Entry call: `esoi.run("leaderboard", '.')`
- Selected implementation: Margin leaderboard (`margin-leaderboard`)
- Metric: Ranking correctness
- Implemented by: [`implementations/python/esoi/__main__.py`](../../__main__.py), [`implementations/python/esoi/command_table.py`](../../command_table.py), [`implementations/python/esoi/optimization/leaderboard/arm_kinds.py`](arm_kinds.py), [`implementations/python/esoi/optimization/leaderboard/arm_selection.py`](arm_selection.py), [`implementations/python/esoi/optimization/leaderboard/board_report.py`](board_report.py), [`implementations/python/esoi/optimization/leaderboard/cascade_report.py`](cascade_report.py), [`implementations/python/esoi/optimization/leaderboard/cascade_stages.py`](cascade_stages.py), [`implementations/python/esoi/optimization/leaderboard/case_identity.py`](case_identity.py) and 36 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Margin leaderboard | `leaderboard:margin-leaderboard` | Compares the result of each implementation on the same case hash (the pool of its repeated runs of the same code on those cases, else its latest run), calls a win only beyond a pass-rate margin or spend tolerance, and labels ties, losses, unmeasured and comparison-only arms. | [`implementations/python/esoi/optimization/leaderboard/interface.py`](interface.py) | selected |
| Probability each arm is best | `leaderboard:posterior-ranking` | Ranks the arms by the probability, given their per-case results, that each is the best, instead of calling a winner past a margin. | no code yet |  |

## Metrics

- Ranking correctness (`metric-ranking-correctness`): leader `live_leaderboard`, 57 of 57 cases

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [Implementations Chosen on Evidence](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
