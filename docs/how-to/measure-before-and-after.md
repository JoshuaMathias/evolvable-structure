# Keep a metric's value before and after a piece of work

ESOI asks every piece of work for "the relevant metric result before and after your change". If the worker (a person, a script, a
model) states those numbers in its closing words, they are only a claim. These modules let a program take them itself: find the
slice of the specification the work serves, read the metric before the work starts, read it again when the work ends, and keep both
in a ledger the worker's own claims can sit beside. Nothing here calls a model, and no setting is read from the environment: each
one is an argument.

| Module | What it gives you |
|---|---|
| `esoi.spec_slice` | The solution a request serves, its next open milestone, its authoritative metric and the command that records it |
| `esoi.metric_meter` | Meters that turn that metric into one number, a bounded and announced reading, and the two moments a reading is taken |
| `esoi.metric_results` | One row of the record, the ledger that keeps rows per run, and the rules that fold them into what a consumer shows |
| `esoi.iteration` | `MetricIteration`: the three above, wired for one piece of work |

The examples below are run by a test, so they stay true. The first block makes a small repository with records to read.

```python
import os
import tempfile
from pathlib import Path

from esoi import scaffold

root = Path(tempfile.mkdtemp()) / "demo"
scaffold.init(root, "demo_pkg", say=lambda text: None)   # a repository with ESOI records and one recorded run
request = "make the greeting function greet a person by name in the standard form"
```

## Find the slice

```python
from esoi.spec_slice import RepoSliceSource, next_priority_block

found = RepoSliceSource().slice_for(request, working_dir=str(root))
print(found.solution_id, found.metric_id, found.milestone_number, found.target)
# greet-a-person greeting-pass-rate 1 1.0
brief = next_priority_block(found, closing="Say what the metric was before and after.")
```

`slice_for` returns `None`, never a wrong answer, when the folder is not inside a repository with records, when the request does
not clearly serve one solution, or when the lookup takes longer than its time limit. The milestone is the first one that is
neither met (`[met: DATE]`, see `esoi.fields`) nor archived (its text begins `Archived`). A milestone's `target` is the one number
in its text, a percent read as a fraction, and `None` when the text holds none or several.

The choice of records is a `Chooser`, a function from the request and the specification index to `Chosen(ids, sure)`. The default,
`lexical_choice`, takes the best lexical matches of `esoi.spec_index` and is never sure, so it gives a slice only when the best
matches belong to one solution. Pass `choose=` to use a stronger search of your own, `find_root=` to say which repository applies to
a folder, and `cache_dir=` to keep the index between calls.

## Read the metric

```python
from esoi.metric_meter import AFTER, BEFORE, meters_from_names, read_value

meters = meters_from_names("recorded_row,offline_arm", environ=os.environ)
before = read_value(meters, found, str(root), when=BEFORE, budget_seconds=30)
print(before.value, before.meter)
# 1.0 recorded_row
```

Two meters ship. `recorded_row` reads the latest row of the repository's results log, and only while that row is current; it can
answer only the reading before the work, because a row says nothing about a tree that has changed since. `offline_arm` runs the
metric's own `esoi run` command, but only for an arm that cannot spend money (it is not listed or declared as paid and its last run
called no model), with a budget of zero model calls, a time limit, its own process group, and `environ` scrubbed of anything that
looks like a credential and of the repository's `[hermetic]` names. Any failure gives `None`. A meter of your own is any object
with a `name` and `measure(spec_slice, working_dir)`; it may also say `cheap`, `serves` and `within`.

A reading has one budget, whatever the number of meters. `announce` is called once, just before the first meter that takes time,
so a person is told about a wait before it starts. A meter that has not answered when the budget is spent is left behind and the
`Reading` carries a note saying which.

## Keep it for a piece of work

```python
from esoi.iteration import MetricIteration
from esoi.metric_results import SOURCE_RECORDED, FileMetricLedger, MetricResult, render_line

ledger = FileMetricLedger(str(root / "ledger"))
work = MetricIteration(ledger, "run-1", source=RepoSliceSource(), meters=meters, request=request, working_dir=str(root))
block = work.begin()          # reads the metric BEFORE and returns the NEXT PRIORITY block for the brief
# ... the work happens; the worker may add its own rows to the same ledger under the same run id ...
ledger.record(MetricResult(source=SOURCE_RECORDED, run_id="run-1", metric_id=found.metric_id,
                          name=found.metric_name, before=1.0, after=1.0))
done = work.finish()          # reads the metric AFTER and reconciles the rows
print(render_line([r.to_dict() for r in done.results]))
# Metric: Greeting pass rate 1 -> 1 (measured); Greeting pass rate 1 -> 1 (recorded)
```

`MetricIteration` has three settings that stand for three ways to run. With no `source` it adds nothing. With a `source` and
`measures=False` the brief gets the slice and nothing is read. With a `source` and meters, the program also writes the readings
itself, as `measured` rows. `begin` and `finish` never raise, so the record cannot stop the work it records.

Each row says who vouches for it: `measured` (a meter read it), `recorded` (the worker said so) or `not_applicable` (the worker
said no metric applies, with a reason). A number is a finite int or float and nothing else; a string is rejected, never parsed.
`reconcile` folds rows of one source for one metric into one, keeps measured and recorded rows side by side and flags both when
their numbers differ (the measured value is rounded to the decimals the recorded one is written with first, so 0.38 and 0.4 agree),
and drops the `not_applicable` rows once any row holds a number. `render_line` writes one plain line from the rows, never a model.

What counts as work that changed something, whether to ask a worker once for a missing result, and where the rows are shown are the
caller's: `finish(did_work=False)` skips the reading after for work that never ran, and the ledger is a small protocol
(`record`, `for_run`) if a file per run is not what you keep.
