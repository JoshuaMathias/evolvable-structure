# Promote the Winner

**Purpose:** Switch the selection to the rival that clearly wins on the solution's own metric, with the evidence recorded, or propose it when a person must approve.

Breadcrumb: [Top](../../../../../esoi/README.md) > [Implementations Chosen on Evidence](../README.md) > Promote the Winner

Part of [Implementations Chosen on Evidence](../README.md)

## Promote the Winner (`promote-the-winner`)

- Out of scope: Deciding what is best; promoting on stale or incomparable results.
- Delegates to: leaderboard, review-tracker
- Entry call: `esoi.run("promote-the-winner", '.')`
- Selected implementation: Promotion on the leaderboard's verdict (`margin-promotion`)
- Metric: Promotion correctness
- Implemented by: [`implementations/python/esoi/__main__.py`](../../__main__.py), [`implementations/python/esoi/command_table.py`](../../command_table.py), [`implementations/python/esoi/optimization/promote_the_winner/interface.py`](interface.py), [`implementations/python/esoi/optimization/promote_the_winner/promote.py`](promote.py), [`implementations/python/evaluation/components/per_case.csv`](../../../evaluation/components/per_case.csv), [`implementations/python/evaluation/components/promote_the_winner/__init__.py`](../../../evaluation/components/promote_the_winner/__init__.py), [`implementations/python/evaluation/components/promote_the_winner/broken/__init__.py`](../../../evaluation/components/promote_the_winner/broken/__init__.py), [`implementations/python/evaluation/components/promote_the_winner/broken/never_promotes.py`](../../../evaluation/components/promote_the_winner/broken/never_promotes.py) and 23 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Promotion on the leaderboard's verdict | `promote-the-winner:margin-promotion` | Where a rival beats the selected implementation on the same cases beyond the noise, the solution's selected cell and the metric's command are switched and the evidence is written beside them, when the solution's promotion cell says automatic; otherwise the same edits are printed as a proposal. | [`implementations/python/esoi/optimization/promote_the_winner/interface.py`](interface.py) | selected |
| A person edits the records | `promote-the-winner:person-edits-the-records` | A person reads the board, then edits the selected cell, the metric command and the reason by hand. | no code yet |  |

## Metrics

- Promotion correctness (`metric-promotion-correctness`): leader `live_promote`, 17 of 17 cases

## Problems

- Winner not adopted (`prob-winner-not-adopted`): A rival that clearly beats the selected implementation on the solution's own metric stays unadopted until someone notices and edits the selection, the metric's command and the record of why, by hand.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [Implementations Chosen on Evidence](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
