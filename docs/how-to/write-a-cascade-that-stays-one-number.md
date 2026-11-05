# Write a cascade that stays one number

Why: [a cascade runs one criterion](../explanation/a-cascade-runs-one-criterion.md). Steps:

1. **Write the number.** In `esoi.toml` add `[balance.<component>]` with `weights` for accuracy, cost and time (they sum to 1) and the
   budgets `cost_per_case_usd` and `seconds_per_case`. If size matters, make it part of what the scorer counts as a miss. Commit this
   before the first run; every row records `balanced`.
2. **Pool the cases.** Put every kind of case (single-file lookup, topic needs, real requests) in the component's case set, one `source`
   per kind, in the proportion real inputs occur. Take the proportion from a sample of real inputs, not from what is easy to write.
3. **List the stages as fidelity.** In the metric's `cascading_conditionals`, order stages by cost: a free proxy or a unit test
   (`real=no`), then a sample, then the whole set with a live model. Every stage is the same component and the same balanced score.
   ```
   free [sample=full | real=no | gate=all-pass] > sample [sample=sample:30 | real=yes | gate=competitive] > whole [sample=full | real=yes]
   ```
   Do not give a stage its own component, its own cases or a "must not regress" gate on a different measure.
4. **Let the metric judge every arm.** No arm is excluded by a mark. If a trivial arm (one that does nothing, or returns a fixed answer)
   scores best, the metric is missing a factor the solution cares about: add it to the balanced score, and declare the diagnostics that
   show a degenerate arm so S45 can point at it.
5. **Name one authoritative metric.** If the solution has other metrics, set `authoritative_metric_id` and feed the others in as case sources.
6. **Check.** `esoi check --findings` lists S41, S42, S44 and S45 with the next action. `esoi cascade` shows each stage's number and the chosen arm.

Change the weights later only by re-recording the arms (`esoi run --stale --plan`), and say why in a comment beside the table.
