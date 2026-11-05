# Keep a Metric Record

**Purpose:** Keep the relevant metric's value before and after each piece of work, so the change can be judged later.

Breadcrumb: [Top](../../../../../esoi/README.md) > [Implementations Chosen on Evidence](../README.md) > Keep a Metric Record

Part of [Implementations Chosen on Evidence](../README.md)

## Keep a Metric Record (`keep-metric-record`)

- Out of scope: Choosing the metric; finding the slice of the specification; calling a model.
- Delegates to: spec-search
- Entry call: `esoi.run("keep-metric-record", '.')`
- Selected implementation: Library modules (`library-modules`)
- Metric: Metric record kept
- Implemented by: [`implementations/python/esoi/optimization/keep_metric_record/interface.py`](interface.py), [`implementations/python/esoi/optimization/keep_metric_record/iteration.py`](iteration.py), [`implementations/python/esoi/optimization/keep_metric_record/metric_meter.py`](metric_meter.py), [`implementations/python/esoi/optimization/keep_metric_record/metric_results.py`](metric_results.py), [`implementations/python/esoi/optimization/keep_metric_record/spec_slice.py`](spec_slice.py), [`implementations/python/evaluation/components/keep_metric_record/__init__.py`](../../../evaluation/components/keep_metric_record/__init__.py), [`implementations/python/evaluation/components/keep_metric_record/broken/__init__.py`](../../../evaluation/components/keep_metric_record/broken/__init__.py), [`implementations/python/evaluation/components/keep_metric_record/broken/naive_claims.py`](../../../evaluation/components/keep_metric_record/broken/naive_claims.py) and 5 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Library modules | `keep-metric-record:library-modules` | The spec_slice, metric_meter, metric_results and iteration modules wired for one piece of work: a slice of the specification, meters that read the metric, a ledger of rows and MetricIteration around them. | [`implementations/python/esoi/optimization/keep_metric_record/interface.py`](interface.py) | selected |
| Values the worker reports | `keep-metric-record:worker-reported` | The worker states the metric before and after in its closing message, and a reviewer checks it later. | no code yet |  |

## Metrics

- Metric record kept (`metric-keep-metric-record`): leader `live_record`, 67 of 67 cases

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [Implementations Chosen on Evidence](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
