# Discriminating Cases

**Purpose:** Prove that a solution's cases can tell a sound implementation from a naive one, even when only one implementation exists.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [Implementations Chosen on Evidence](../../README.md) > [Measurement Harness](../README.md) > Discriminating Cases

Part of [Measurement Harness](../README.md)

## Discriminating Cases (`discriminating-cases`)

- Out of scope: Inventing rivals that exist only to lose a comparison.
- Entry call: `esoi.run("discriminating-cases", '.')`
- Selected implementation: Broken baselines (`broken-baselines`)
- Metric: Case discrimination
- Implemented by: [`implementations/python/esoi/optimization/measurement_harness/discriminating_cases/interface.py`](interface.py)

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Broken baselines | `discriminating-cases:broken-baselines` | Each solution with a single implementation keeps naive implementations in its `broken/` folder, and one test proves each fails the cases. | [`implementations/python/esoi/optimization/measurement_harness/discriminating_cases/interface.py`](interface.py) | selected |
| Mutants of the selected implementation | `discriminating-cases:mutation-testing` | Changes the selected implementation automatically, one small mutation at a time, and counts the mutants the cases fail to catch. | no code yet |  |

## Metrics

- Case discrimination (`metric-case-discrimination`)

## Where to go next

- Up: [implementations/python/esoi/optimization/measurement_harness](../README.md)
- Intent: [Implementations Chosen on Evidence](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
