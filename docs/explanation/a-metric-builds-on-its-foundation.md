# A metric builds on its foundation

A library measures what it is for: its retrievers, its builders, its gates. A service that uses the library (a consumer) is judged on the
same things plus what is its own: its real requests, its own source systems. The mistake is for the consumer to keep a copy of the library's
cases and scorer and score them again. The copy measures the same thing twice, costs the same run twice, and drifts: when the library adds a
case kind or fixes its scorer, the consumer's number does not move until somebody remembers to port the change.

## The principle

A consumer's metric BUILDS ON the library metric it depends on and measures on that foundation without re-running it separately.

1. **It declares the foundation.** A `[builds_on.<component>.<name>]` table in the consumer's configuration names the foundation's repository and
   component and a `share`: the share of the consumer's one number that the foundation's cases carry. The consumer's own cases carry the rest. A
   consumer can build on more than one foundation (a selection metric and a bootstrap metric, say); the shares together stay below 1.
2. **It reuses what the foundation recorded.** When the consumer's arm is the same implementation the foundation measured (the arm names its
   foundation arm: `FOUNDATION_ARMS = {"name": "arm"}`), and the foundation's latest whole-set row for it is current by the foundation's own rule
   (same cases digest, committed code, the arm's code unchanged since its commit), the foundation's per-case results are part of the consumer's
   case set. They are not run again. The consumer runs only its own extra cases and composes one number.
3. **It never mixes a stale result.** When the digests differ, `esoi run` says so and does one of two things, chosen by `on_stale`. `run` (the
   default) runs the foundation's cases through the foundation's own scorer, one code path and never a copy: the foundation's own build of the
   named arm, or, for an arm that names none, the consumer's `foundation_fn(name, fn)` adapter, which turns the consumer's arm into what the
   foundation's scorer calls. `report` refuses the run and names why the foundation is stale.
4. **Its row remembers the foundation.** The recorded row carries `builds_on` (`name=component:arm@git_sha/cases_sha`). The row is stale when the
   foundation's cases or the foundation arm's code changed since, so an improvement to the foundation reaches the consumer's number the next time
   it is run, with nothing ported by hand.
5. **Its copies are removed.** The consumer keeps no copy of a case or scorer the foundation owns. What stays in the consumer is what only the
   consumer can measure.

The composed number weights each part's accuracy, cost and seconds per case by its share (renormalised over the parts the arm has, so an arm
that does not build on a foundation, or a consumer with no private cases yet, is not penalised), then folds them with the consumer's own
`[balance.<component>]`. The weights of that balance stay the consumer's and are fixed before any arm is scored; the foundation's balance is not
imported. A sampled or `--only` run scores the consumer's own cases only and says so: composition is for whole sets. The per-case outcomes of the
foundation's cases join the consumer's per-case log, so the paired test of the leaderboard sees every case the number rests on.

## Inherited gates, and tightening them

A foundation guards what is risky about itself with cascade stages. A consumer should not re-prove those stages, and must not be able to skip them.
A consumer stage written `safety [inherits=safety]` is passed only when the foundation's stage of that name passed for the foundation arm, by
the foundation's own gate, floor, expiry and staleness (`esoi cascade` shows `stopped before safety: the foundation's safety stage has not passed`).
A stage with only `inherits` runs nothing and holds no result row.

A consumer may add a gate beside `inherits`, and it TIGHTENS: `all-pass` where the foundation says `competitive`, a higher `min-pass-rate`. It can
never loosen: the foundation's gate is always checked first, and rule S47 reports a consumer gate that is looser than the one it inherits. A
consumer that needs a looser gate has a different purpose than its foundation and needs a metric of its own.

## Reading source systems: cost and risk

Reading from source systems (a server's records, local files) has a cost and a risk of its own, and both are written where the balance is, as
`[balance.<component>.source_access]`, committed before any arm is scored:

    [balance.myselect.source_access]
    usd_per_record = 0.00001        # constants: also usd_per_mb and usd_per_call
    max_records_per_request = 200   # the per-request read budget: also max_mb_per_request and max_calls_per_request
    allowed_scopes = ["workspace"]  # nothing is read outside these scopes
    forbid_full_scan = true         # no request scans a whole source (the default)

An arm reports each read with `meter.read(records=.., bytes=.., calls=.., scope=.., full_scan=..)`. The read is priced at the constants and joins
the run's cost, so the cost term of the balanced number covers source access. The limits are gates, not prices: a request (one case) that scans a
whole source, spends its read budget or reads outside the allowed scopes FAILS, with the reason in its note. A consumer inherits the foundation's
table and may tighten it (a smaller budget, fewer scopes); rule S47 names every limit that is looser than the foundation's.

## When something is its own solution

The decision rule, for any capability a method needs (building and refreshing a store from source systems is the usual case):

- It is a **separate solution**, with its own problem, ideal, metric and implementations, when **several implementations share it** or **its
  cost amortizes across requests** (it is built once and read by many).
- It is **part of the implementation** when **only that one method needs it**. An implementation that owns only the index derived for its own
  method is charged for it in its own number: the build amortized over the requests it serves, plus the size of the store it keeps.

Bootstrapping a store is therefore a solution beside selection, not a sub-intent of one selection implementation: every selector reads what
the bootstrap built, and the build is paid once for all of them. A consumer then builds on BOTH foundation metrics (selection and bootstrap) and
adds, on top, only what is consumer-specific: its own source access and its own real requests.

## What it builds on

The harness (`esoi.optimization.measurement_harness.run_component`, which composes a run), the results and per-case logs it reuses, `esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness` (the foundation's own staleness
decides reuse), the cascade (`esoi.optimization.leaderboard.cascade_stages`, the `inherits` key) and the balance (`esoi.optimization.measurement_harness.balance`, `esoi.optimization.measurement_harness.access`). The mechanism is
`esoi.runtime.consumer_check.foundation`. It extends the idea of [overriding only what differs](override-only-what-differs.md) and [following the parent's check with
your own metric](follow-the-parent-check-with-your-own-metric.md) from selections to measurements. A cascade still runs one criterion
([a cascade runs one criterion](a-cascade-runs-one-criterion.md)): the foundation's cases are a case source of the consumer's one number, never a
second leaderboard.
