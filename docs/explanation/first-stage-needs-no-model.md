# The first stage needs no model

This is guidance, not a rule: no check enforces it. When a metric lists `cascading_conditionals`, make its first stage
one that needs no model. It costs nothing, so it can run on every change, and it proves the scorer and the cases work
before anything is spent. The paid stages come after it, and only when it passes.

The skill says it this way: "New or proposed alternative implementations are tested first in a way that has almost no
cost, such as a unit test or specific type of review" (see [the definitions and principles](from-the-skill.md)). This
page says what that first step should be for a metric.

## Why

- **It is free and runs every time.** Nobody has to decide whether it is worth running.
- **It catches the cheap failures first.** A broken scorer, a case set that does not load, a metric that cannot fail, a
  wrong command or a regression all show up before any spend.
- **It makes the paid results trustworthy.** If the scorer already passes the ideal answers and fails a no-model floor,
  a later score says something about the implementation, not about a bug in the scorer.
- **It is deterministic.** When it fails, the thing is wrong. A model was not unlucky.
- **It writes down a discipline.** "Validate the scorer offline, then 1, 3, 10, 30" is easy to skip when it lives in
  someone's head. As the first stage, a person or an AI cannot skip it.
- **It stops metrics being run for their own sake.** A failing free stage ends the ladder, so nothing is spent on a
  metric that is not ready.

## What counts as no model

No network model call of any kind, a model used as a judge included. A local, deterministic classifier, a regular
expression, a unit test, a frozen index or a checklist a person ticks are all fine.

## Examples

**A rule-based metric.** Everything can be scored without a model, so one stage is the whole cascade:

```
offline [sample=full | real=no]
```

**An answer-quality metric for a model's replies.** The first stage checks the scorer, not the model:

```
offline [sample=full | real=no | gate=all-pass | when=the scorer passes the ideal reply of every case and fails the no-model floor] > one [sample=sample:1 | real=yes | gate=all-pass] > three [sample=sample:3 | real=yes | gate=all-pass] > ten [sample=sample:10 | real=yes | gate=competitive]
```

**A retrieval metric.** Recall on a frozen index with fixed fixtures needs no model:

```
offline [sample=full | real=no | gate=all-pass | when=recall on the frozen index passes and the empty retriever fails] > live [sample=sample:10 | real=yes | gate=competitive]
```

**A metric over generated code.** Run the produced program on fixed tests. Scoring needs no model, and the first stage
runs a known-good and a known-bad program through the same tests:

```
offline [sample=full | real=no | gate=all-pass | when=the tests pass the reference program and fail a stub] > generated [sample=sample:3 | real=yes | gate=competitive]
```

**A human-judged metric.** A checklist review is the cheap first stage. A model judge or a panel comes later:

```
checklist [sample=full | real=no | gate=all-pass | when=a person ticked every item on the review sheet] > judge [sample=sample:10 | real=yes | gate=competitive]
```

**A metric over an expensive simulation.** A cheap analytic bound comes first, and it can reject a design that no run
could rescue:

```
bound [sample=full | real=no | gate=all-pass | when=the closed-form bound allows the target] > simulated [sample=sample:3 | real=yes | gate=competitive]
```

**The anti-pattern.** A first stage that calls a model "just to see":

```
try [sample=sample:1 | real=yes] > offline [sample=full | real=no]
```

It spends before the scorer is known to work, and a bad result cannot be told apart from a bad scorer. Put `offline`
first.

## What the `when` text says

Say what the stage proves, in a sentence a person or an AI can check: "the scorer passes the ideal reply of every case
and fails the no-model floor". The text is reported by `esoi cascade`, never evaluated, so it is the instruction for
whoever runs the stage.

## When no such stage exists yet

Writing it is the first piece of work, not an optional extra: a scorer validation (the ideal answers must pass) and a
no-model floor (a naive answer must fail). If that cannot be done yet, record the gap in the metric's `disadvantages`
so it is visible, and treat every paid result as unvalidated until it is closed.

## What you see

`esoi cascade [SOLUTION]` lists every stage in order with each implementation's result, and names the next stage worth
running with its `esoi run` line. A cascade that starts free shows the free stage first, then the paid one it unlocks.

## When the first stage fails

Fix the scorer or the cases. Do not climb: a paid stage run on a failing first stage measures nothing you can trust.
Change the implementation only when the first stage shows it is the implementation that fails.

See [choosing by metric](choosing-by-metric.md) for the stage keys, [when metrics are run](when-metrics-are-run.md) for
who approves spend, and [a metric must be meaningfully real](metrics-must-be-real.md).
