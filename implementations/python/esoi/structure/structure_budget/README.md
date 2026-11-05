# Structure Budget

**Purpose:** Keep the structure's own cost in view: admit a rule, record or sub-intent only with what it prevents, and prune what stops paying.

Breadcrumb: [Top](../../../../../esoi/README.md) > [A Project's Records and Code as One Structure](../README.md) > Structure Budget

Part of [A Project's Records and Code as One Structure](../README.md)

## Structure Budget (`structure-budget`)

- Out of scope: Removing what still catches real mistakes; running the rules.
- Delegates to: structure-check
- Entry call: `esoi.run("structure-budget", '.')`
- Selected implementation: Written weighing rule (`written-weighing-rule`)
- Metric: Structure cost against catches
- Implemented by: [`implementations/python/esoi/structure/structure_budget/interface.py`](interface.py)

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Written weighing rule | `structure-budget:written-weighing-rule` | Before adding a sub-intent, rule or record, weigh its build and upkeep cost against what comparing alternatives and defining it clearly would gain, counted to the next highest priority milestone (docs/explanation/when-to-create-a-sub-intent.md), and weigh it again at each milestone. | [`implementations/python/esoi/structure/structure_budget/interface.py`](interface.py) | selected |
| Measured cost and catches | `structure-budget:measured-cost-and-catches` | A tool records the time the check adds and which rules, records and checks caught a real violation, and proposes removing those that catch nothing over a period. | no code yet |  |

## Metrics

- Structure cost against catches (`metric-structure-cost-against-catches`)

## Problems

- Structure costs more than it returns (`prob-structure-costs-more-than-it-returns`): Every rule, record and check adds work to each change, and past a point contributors spend more time satisfying the structure than improving the code.
- Rules unjustified (`prob-rules-unjustified`): A rule is kept in code with no record of the mistake that justified it or of what it has caught since, so whether it still earns its place, or why its limit has its value, cannot be told without asking its author.

## Ideals

- Proportionate structure (`ideal-proportionate-structure`): The structure costs less than it returns, and a small change carries a small cost.
- Rules earn their place (`ideal-rules-earn-their-place`): Every rule can say which mistake it prevents, and is removed when it stops catching any.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [A Project's Records and Code as One Structure](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
