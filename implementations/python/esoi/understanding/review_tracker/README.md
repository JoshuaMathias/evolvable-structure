# Review Tracker

**Purpose:** Put the whole intent network and its current results in front of a reviewer, and carry their edits back to the records.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../README.md) > Review Tracker

Part of [How People and Agents Come to Apply ESOI](../README.md)

## Review Tracker (`review-tracker`)

- Out of scope: Holding truth beyond the review columns; calling verdicts.
- Delegates to: intent-registry, leaderboard
- Entry call: `esoi.run("review-tracker", '.')`
- Selected implementation: Tracker and sheet (`tracker-and-sheet`)
- Metric: Review coverage
- Implemented by: [`implementations/python/esoi/__main__.py`](../../__main__.py), [`implementations/python/esoi/structure/structure_check/rules/generated.py`](../../structure/structure_check/rules/generated.py), [`implementations/python/esoi/understanding/review_tracker/interface.py`](interface.py), [`implementations/python/esoi/understanding/review_tracker/sheets.py`](sheets.py), [`implementations/python/esoi/understanding/review_tracker/tracker.py`](tracker.py), [`implementations/python/evaluation/components/review_tracker/__init__.py`](../../../evaluation/components/review_tracker/__init__.py), [`implementations/python/evaluation/components/review_tracker/broken/__init__.py`](../../../evaluation/components/review_tracker/broken/__init__.py), [`implementations/python/evaluation/components/review_tracker/broken/overwrite.py`](../../../evaluation/components/review_tracker/broken/overwrite.py) and 5 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Tracker and sheet | `review-tracker:tracker-and-sheet` | `esoi tracker build` generates the tracker tables from the registry and results; `esoi sheet-sync` merges them two-way with the Google Sheet by record id, keeping reviewer columns. | [`implementations/python/esoi/understanding/review_tracker/interface.py`](interface.py) | selected |
| Review in the pull request | `review-tracker:pull-request-review` | Shows a generated summary of the changed records and results as a comment on each pull request, and the reviewer answers there. | no code yet |  |

## Metrics

- Review coverage (`metric-review-coverage`): leader `live_tracker`, 10 of 10 cases

## Problems

- Review needs implementations (`prob-review-needs-implementations`): A person who wants to steer quality has to read implementations, because ideals, metrics and current results are not gathered anywhere they can read and correct.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
