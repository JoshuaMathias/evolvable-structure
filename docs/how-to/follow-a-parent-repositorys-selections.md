# Follow a parent repository's selections

A child repository that builds on a parent (a hub) inherits the parent's selected arm of every solution it does not decide itself,
and overrides it where its situation differs ([Build on another package's defaults and say why you differ](hierarchical-defaults.md)).
`esoi follow` keeps both honest: it compares what the parent selects now with what the child holds, and judges the parent's arm on the
child's own metric. It is advice only.

```bash
esoi follow                                        # the parent named by [parent] in esoi.toml
esoi follow --parent ../hub                        # a records folder (or its esoi.toml), or an esoi_selection.json snapshot
esoi follow --parent hub_package                   # an importable package whose assembler() has a parent chain
esoi follow --solution greet-a-person --plan       # one solution; print only what would be run
esoi follow --run-free                             # record the missing rows of arms that need no model
esoi follow --json                                 # esoi.follow/1, for tooling
```

`--lock FILE` names the child's lock (default `esoi.lock.json`). The exit code is 0 whatever is found; it is 2 only when the parent
cannot be read.

## What is compared

For each solution the parent selects:

- **An override**: the child's own `selected` differs from the parent's arm. It is looked at again when it cites a metric of the
  child in `overrides.csv`, or when the child's metric already holds rows for both arms.
- **An inherited arm**: the child's lock holds an arm other than the parent's current one, so the parent's selection changed since the
  lock was written.

A solution whose parent selection and lock agree, with no override, is not reported. When nothing is, the output is one line,
`nothing changed`.

## The four verdicts

The parent's arm is compared with the child's current arm (the override, or the locked arm) on the child's own recorded rows, by the
child's own selection rule (`esoi.leaderboard.decisions`, with the `[switching]` policy of the child), so a child that requires a
significant lead keeps its arm until the parent's arm is shown better.

| Verdict | Means | Advice |
|---|---|---|
| `ADOPT` | the parent's arm holds: it is not worse than the child's | drop the override, or `esoi lock --update --solution ID` |
| `KEEP THE OVERRIDE` (or `KEEP THE LOCK`) | the child's metric says the parent's arm loses | keep it, with the numbers to cite in the override's reason |
| `OVERRIDE CAN BE DROPPED` | the parent's arm now beats the child's own | remove the override, or move the lock |
| `NOT MEASURED` | the child has no row for the parent's arm on the cases and sample of its own arm's row | the exact command that records it and its cost class |

A row whose measured code changed is shown as stale with the reason and the command that re-records it. Staleness is the child's
configured rule (`import_closure` by default, [Choose when a result is stale](choose-when-a-result-is-stale.md)), so a change to
unrelated code does not mark a row. A stale row still informs the verdict; it never blocks.

## Free and paid commands

A missing row is recorded with `esoi run <component> --impl <arm> --record`, on the sample the child's own arm was scored on so the
two rows compare. The report names its cost class:

- `free (offline, no model)`: the harness runs the arm offline. `esoi follow --run-free` runs it, then looks again. `--plan` prints what
  would run and runs nothing.
- `paid (...)`: the arm declares `PAID = True`, is listed in `paid_arms`, or its last row called a model. It is listed with a
  `--max-calls <budget>` placeholder and never run by `esoi follow`, whatever the flags. Estimate the cost, stage the sample and get the
  approval first ([metric run policy](../reference/templates/metric-run-policy.md)).

If the child cannot run the parent's arm at all (no `impls/<arm>.py`, no listed arm and no implementation record), the report says what
to add. A solution the child has no metric for is reported as not measured, with that reason.

## A malformed override

`overrides.csv` rows that name no solution, a solution the parent does not have, a reason that is not a record id, or a record the child
does not have are listed as `malformed override: ...`. They are advice; rule S35 is the place that fails.

Why the check is the child's own metric, and when to run it: [Follow the parent, check with your own metric](../explanation/follow-the-parent-check-with-your-own-metric.md).
