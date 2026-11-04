# Fit public benchmarks into one generic metric

Why: several public benchmarks each measure a slice of what you care about. Writing one metric per benchmark gives you several
numbers and no way to pick. Instead, write one generic metric from your intent and let each benchmark feed it through an adapter.
The overview of what the metric contains is in [what a metric includes](../explanation/what-a-metric-includes.md).

## 1. Define the generic metric by what matters

State it in your intent's words, not a benchmark's. For a retrieval component: "the context a task needs is shown, in order, with
little noise, and nothing is shown when nothing is needed; at a cost". Split it into parts you can score per case, for example
recall of the needed items, order, noise, and abstention. Add cost, time and the gates (see the checklist in
[what a metric includes](../explanation/what-a-metric-includes.md)). Its result per case is a utility, one number.

## 2. Write one adapter per benchmark

An adapter maps one benchmark's own measure into a part of the generic utility. Keep it a small function (or table) in the metric's
evaluation folder, so a reviewer reads it in a minute:

| Benchmark's own measure | Part of the generic utility it speaks to |
|---|---|
| nDCG@10 on a ranking benchmark | the ordering part |
| evidence-session recall and abstention on a memory benchmark | the recall part and the nothing-needed part |
| "the paper was found" on a literature-search benchmark | the recall part |

Each adapter states two things in one line: what it can speak to, and what it cannot. A ranking benchmark says nothing about
cost or about privacy; a memory benchmark says nothing about code. A part no adapter covers is scored on your own cases, and the
metric says so.

## 3. Fix each adapter's share before scoring

Write the share of the generic number each adapter carries (and the share left to your own cases) in the metric's record, with a
reason, and commit it before any arm is scored. Changing a share later is a new version of the metric, and old results stay
comparable only under the old shares. The cause is the usual one: shares chosen after seeing results drift toward the arm someone
already prefers.

## 4. Use public results for public arms, run your own for the rest

For an arm someone else publishes, put their published numbers into the evidence file with the `comparator` naming the benchmark,
and let the adapter convert them into the generic parts; grade them as in [use public evidence](use-public-evidence.md), and do
not re-run what an independent source has already run. An arm that is yours, or a public arm on a part with no public number,
is run on the benchmark's data or on your cases through the same adapter, so every arm is on the same footing. Declare the
benchmark a component reproduces in `evaluation/<component>/benchmark.txt` so `esoi run` points you at the public result before
spending anything.

## 5. Say what the fit cannot show

A public benchmark rarely matches your inputs. After the adapters, add a small sample of your own real cases at the top of the
cascade and report whether the public ranking and yours agree. Agreement raises confidence; a conflict is information about your
cases or about the benchmark and is recorded, not smoothed over (see
[judge public evidence like a scientist](../explanation/judge-public-evidence-like-a-scientist.md)).

## 6. Check

- Every adapter has a line saying what it can and cannot speak to.
- The shares are written, add to one, and are committed before the first score.
- Each public arm has a graded evidence row for each adapter that uses it, and none was re-run without a stated difference.
- The same arms scored on the same case digest at each stage ([a cascade runs one criterion](../explanation/a-cascade-runs-one-criterion.md)).

A consumer that customizes a solution built this way adds its own cases and costs on top and inherits the adapters: see "building
on a foundation metric" (TODO: link once that page is published).
