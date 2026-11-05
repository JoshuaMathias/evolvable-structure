# The ESOI Steps

**Purpose:** Give the order in which to define and apply ESOI to anything new or changed, and say where to loop back when something changes.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../../README.md) > [The Standard](../README.md) > The ESOI Steps

Part of [The Standard](../README.md)

## The ESOI Steps (`the-steps`)

- Out of scope: Restating what each record type asks, prescribing tools, and shipping the steps with the skill.
- Delegates to: the-standard, skill-distribution
- Entry call: `esoi.run("the-steps", '.')`
- Selected implementation: The ESOI steps (`esoi-steps`)
- Metric: Steps followed
- Implemented by: [`.claude-plugin/marketplace.json`](../../../../../../.claude-plugin/marketplace.json), [`docs/explanation/a-cascade-runs-one-criterion.md`](../../../../../../docs/explanation/a-cascade-runs-one-criterion.md), [`docs/explanation/a-metric-builds-on-its-foundation.md`](../../../../../../docs/explanation/a-metric-builds-on-its-foundation.md), [`docs/explanation/a-problem-says-what-is-true.md`](../../../../../../docs/explanation/a-problem-says-what-is-true.md), [`docs/explanation/a-solution-holds-alternatives-of-one-job.md`](../../../../../../docs/explanation/a-solution-holds-alternatives-of-one-job.md), [`docs/explanation/admitting-a-technology.md`](../../../../../../docs/explanation/admitting-a-technology.md), [`docs/explanation/adopting-solutions-from-a-library.md`](../../../../../../docs/explanation/adopting-solutions-from-a-library.md), [`docs/explanation/beyond-code.md`](../../../../../../docs/explanation/beyond-code.md) and 140 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| The ESOI steps | `the-steps:esoi-steps` | Twenty-three ordered steps in five parts, from purpose to selection by metric, with human steps marked, a map of where to loop back, and a section applying the steps to themselves. | [`implementations/python/esoi/understanding/the_standard/the_steps/interface.py`](interface.py) | selected |
| Project Documentation board checklist | `the-steps:board-checklist` | The eighteen-item 2020 Trello checklist the steps grew from: purpose, brainstorm, audience, problems, knowledge, ideals, coverage, difficulties, definitions, implementations, carrying out, better alternatives, keep improving. | no code yet |  |
| One-hour first pass | `the-steps:one-hour-pass` | The guide for applying ESOI by hand in about an hour (docs/how-to/apply-by-hand.md): an overall network, one detailed solution, a small metric, a recorded choice, then habits. | no code yet |  |
| No stated order | `the-steps:no-stated-order` | The record types and principles alone, applied in whatever order the person chooses. | no code yet |  |

## Metrics

- Steps followed (`metric-steps-followed`)

## Problems

- No order to follow (`prob-no-order-to-follow`): People who want to apply ESOI have the five record types and the principles but no order to follow.

## Ideals

- Followable process (`ideal-followable-process`): Anyone applying ESOI can follow one stated order from purpose to selection by metric, sized to the work, and knows where to return when something changes.

## Where to go next

- Up: [implementations/python/esoi/understanding/the_standard](../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
