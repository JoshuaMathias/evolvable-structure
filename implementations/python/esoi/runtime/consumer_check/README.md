# Consumer Check

**Purpose:** Let a system built on the library show which library solution each part serves, score its parts on the library's cases by building on the library's metric, and see how far its pins trail.

Breadcrumb: [Top](../../../../../esoi/README.md) > [ESOI Inside Other People's Running Code](../README.md) > Consumer Check

Part of [ESOI Inside Other People's Running Code](../README.md)

## Consumer Check (`consumer-check`)

- Out of scope: Copying the library's checks; putting the consumer's private data in the library; switching the consumer's selection for it.
- Delegates to: implementation-selection, measurement-harness
- Entry call: `esoi.run("consumer-check", 'esoi')`
- Selected implementation: Consumer command (`consumer-command`)
- Metric: Consumer soundness
- Implemented by: [`implementations/python/esoi/__main__.py`](../../__main__.py), [`implementations/python/esoi/command_table.py`](../../command_table.py), [`implementations/python/esoi/runtime/consumer_check/consumer.py`](consumer.py), [`implementations/python/esoi/runtime/consumer_check/interface.py`](interface.py), [`implementations/python/evaluation/components/check_a_consumer/__init__.py`](../../../evaluation/components/check_a_consumer/__init__.py), [`implementations/python/evaluation/components/check_a_consumer/broken/__init__.py`](../../../evaluation/components/check_a_consumer/broken/__init__.py), [`implementations/python/evaluation/components/check_a_consumer/broken/columns_only.py`](../../../evaluation/components/check_a_consumer/broken/columns_only.py), [`implementations/python/evaluation/components/check_a_consumer/cases.json`](../../../evaluation/components/check_a_consumer/cases.json) and 21 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Consumer command | `consumer-check:consumer-command` | `esoi consumer check` reads the consumer's own registry, requirements and results, and the library's cases score the consumer's stores through `--impl module:build`. | [`implementations/python/esoi/runtime/consumer_check/interface.py`](interface.py) | selected |
| Contract tests the consumer installs | `consumer-check:contract-test-plugin` | Ships the library's cases as a test plugin that the consumer's own test suite runs against its stores. | no code yet |  |

## Metrics

- Consumer soundness (`metric-consumer-soundness`): leader `live_consumer_check`, 22 of 22 cases

## Problems

- Embedding soundness unknown (`prob-embedding-soundness-unknown`): A system builds on a library's solutions with its own stores and prompts, but cannot see which library solution each of its parts serves, whether its parts meet the library's own cases, or how far its pinned version lags.

## Ideals

- Sound integration (`ideal-sound-integration`): A system built on a library meets the same standard as the library, through the library's own checks and cases.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [ESOI Inside Other People's Running Code](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
