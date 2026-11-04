# A cascade runs one criterion

A cascade is one question asked at rising cost and fidelity: *which alternative is best across all the factors we care about?*
The answer is one number. Every stage estimates that same number, each more faithfully than the one before it (more cases, real
inputs, a live model). A cascade is never a sequence of different questions.

Joshua, 2026-11-04, after an AI laid a cascade out as three different questions: "that's not how cascade is used, that could cause
huge problems, every stage metric must be a single number which represents what alternative is best across all factors".

## The mistake, as it happened

The work was choosing how to build context cards (a topic's information, grouped from many files and sources). The cascade was
written as three sequential stages, each with its own cases and its own pass test:

1. **File finding.** Can the card system find the file a task needs? Pass test: the right file is among the first results.
2. **Topic needs.** Does a card cover what a topic needs? Pass test: the needed facts are in the card.
3. **Real inputs.** Does it work on the requests users actually make? Pass test: the answer is acceptable.

Each stage was run, and each produced its own leaderboard, so the report had three leaderboards and no single best. What went wrong:

- **The criterion changed at every stage.** A stage that decides by "finds the file" and a stage that decides by "covers the topic" are
  two questions. An alternative that wins one can lose the next, and nothing says which counts.
- **Scoring on what was easy to score picked the wrong thing.** Single-file lookup is the easiest to score, and the arm that wins it is
  one card per file, which is a file index. Context cards group a topic from many files and sources. Judged on lookup alone, the
  file index won, and it would have put a card per file in the product's database. The metric was aimed at what is easy to score, not at
  what the solution is for.
- **A guard carried the second criterion in.** "Must not regress on file finding" between stages looks careful. It is a second
  criterion in disguise, since an alternative that is better overall but regresses on lookup is excluded.
- **A trivial arm could win.** The one-card-per-file and one-card-for-everything arms are cheap to build and easy to score. When one wins,
  the metric is wrong (it does not count what a card per file costs), and the fix is in the number, not a mark that hides the arm.

## The correct shape

- **One metric, one number.** The number is a balanced score across all factors: accuracy, cost, time, size. The weights and budgets
  are written down (`[balance.<component>]`, see `esoi/balance.py`) before any alternative is scored. Changing them afterwards ranks
  earlier rows on another criterion, so a change means re-recording the arms.
- **Stages are fidelity, not topics.** Stage one may be a free proxy or a handful of cases, the last stage the most objective measure,
  and every stage reports the same balanced score. A cheap stage may exclude an alternative only on that number.
- **Kinds of cases are case sources of the one metric.** File lookups, topic needs and real requests are three sources of cases,
  mixed in proportion to how real inputs occur. Use real inputs to calibrate the mix. They are not stages with their own pass tests and
  they are not separate leaderboards. The solution has one authoritative metric (`authoritative_metric_id`), and the others, if any,
  are inputs to it.
- **Aim the metric at what the solution is for.** Ask whether the cases look like the real inputs, whether the unit scored is the thing the
  solution produces (a topic card, not a file entry), and whether a mistake that matters in production would move the number.
- **No arm is excluded; the metric decides.** Every implementation competes on the one balanced metric and the selection rule (highest wins,
  labelled significant or best guess) applies to all of them. There is no baseline mark. If a trivial arm scores best, the metric lacks a
  factor (cost, size, efficiency, accessibility): put it into the balanced score. `[balance.<component>.diagnostics.<column>]` lets the
  metric declare what degenerate looks like (a `min` and `max` for a column of the result row, or a `name=number` in its details), and rule
  S45 informs when the arm that scores best crosses a bound. It informs; it never excludes.

## What esoi checks

All advisory: they inform with the next action and never fail `esoi check`.

| Rule | Fires when |
|---|---|
| S41 | a metric's cascade has two or more stages and its command scores more than one component (the cascade decides on one component's rows, so the others are a second criterion beside it) |
| S42 | a solution has two or more metrics, each with recorded results for the same arms, ranked in separate leaderboards |
| S44 | a `[balance.<component>]` table changed in a commit dated after the first row scored with it |
| S45 | the arm that scores best has a value outside the bounds the metric declares degenerate in `[balance.<component>.diagnostics.<column>]` (it informs; no arm is excluded) |

S43 (a selected arm marked `BASELINE` or `FLOOR`) is retired: Joshua, 2026-11-04, "a metric should determine whether something is used,
not marking as baseline".

A solution with several metrics and no `authoritative_metric_id` is already rule R6. Whether the metric is aimed at what the solution is
for, and whether a stage's pass test hides a second criterion, cannot be read from the records: they need a person to look at the cases.

How to write one: [write a cascade that stays one number](../how-to/write-a-cascade-that-stays-one-number.md).

## A checklist

1. Can I say the one number in a sentence, and does it cover accuracy, cost, time and size?
2. Are the weights and budgets written down, and were they written before the first alternative was scored?
3. Does every stage report that same number, estimated on more, or more real, cases?
4. Is each kind of case a source in the one case set, mixed in proportion to real inputs, rather than a stage with a pass test?
5. Is there a gate that is really a second criterion ("must not regress on X")? If X matters, it belongs in the number.
6. Do the cases look like the real inputs, and is the unit scored the thing the solution produces?
7. If a trivial arm (one card per file) won, what factor is missing from the number, and is it declared in `diagnostics`?
