# What ESOI is

ESOI, Evolvable Structure that Optimizes Intent, is a way of working. You write down the intent behind a thing as
records, build the thing as one of several possible implementations, measure the implementations against a metric
chosen to reflect the intent, and let the metric choose which one runs. The records, the measurements and the choice
live in a structure that stays stable while the implementations, and even the intent, change.

The author's own definitions and principles are quoted in [from-the-skill.md](from-the-skill.md). They are the
authority; this page only orients you.

## The loop

1. **Say why.** Write the problem someone has and the ideal state that opposes it. See
   [intent-types.md](intent-types.md).
2. **Say what.** Write a solution: what it is for, what it must do, how you will know it works, and its interface.
   The solution does not say how.
3. **Build alternatives.** Each way of doing it is an implementation. Having a second one is what makes a choice
   possible.
4. **Measure.** A metric measures the distance between an implementation and the ideal. Run every implementation on the
   same cases and record the result with the commit and the cases it was run on. See
   [choosing-by-metric.md](choosing-by-metric.md).
5. **Choose and review.** The best implementation by the metric is the one used. People review the problems, ideals,
   metrics and results, not the implementations.
6. **Evolve.** When the intent changes, or a better implementation appears, or the metric turns out to be wrong, change
   the record and run the loop again. The structure is itself a solution with its own records.

## Where it applies

Anywhere there is an intent and more than one way to serve it: code, a data pipeline, a course, a coaching program, a
team process, a document. See [beyond-code.md](beyond-code.md).

## What a small start looks like

One problem, one ideal, one solution with two implementations, one metric with a handful of cases. The
[guide for applying it by hand](../guides/apply-by-hand.md) takes about an hour, and everything after that is
adding to it when the work asks for it.
