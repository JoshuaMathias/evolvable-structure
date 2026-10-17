# What ESOI is

ESOI, Evolvable Structure that Optimizes Intent, is a way of working. You write down the intent behind a thing as
records, build the thing as one of several possible implementations, measure the implementations against a metric
chosen to reflect the intent, and let the metric choose which one runs. The records, the measurements and the choice
live in a structure that is relatively stable while the implementations, and even the intent, change. The structure
is not final either: it helps you specify the intent, and the intent and the structure evolve together.

Which parts stay stable and which stay changeable is a deliberate choice, made from the structure's purpose and a
prediction of what will be useful to change. The aim is progress over time, judged by the farthest future you can
reasonably plan for; fast progress now can be right for that future, but is not assumed to be.

Intent starts in a person's consciousness, and some of its context is lost when it is written down, so the records
are a limited translation of it. Automation can create intents of its own, but a conscious intent takes priority.

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
5. **Choose and review.** The best implementation by the authoritative metric is used automatically. To steer, people
   need only review the problems, ideals, metrics and results, not the implementations. They can still read, review
   and improve an implementation, and that still adds value; what changes is that choosing no longer depends on it.
6. **Evolve.** When the intent changes, or a better implementation appears, or the metric turns out to be wrong, change
   the record and run the loop again. The structure is itself a solution with its own records.

## Where it applies

Anywhere there is an intent and more than one way to serve it: code, a data pipeline, a course, a coaching program, a
team process, a document. See [beyond-code.md](beyond-code.md).
That includes an AI agent's own behaviour: the skill that carries these principles is one implementation among several,
and how well an agent acts by them can be measured. See [esoi-for-ai.md](esoi-for-ai.md).

## What a small start looks like

One problem, one ideal, one solution with two implementations, one metric with a handful of cases. The
[guide for applying it by hand](../guides/apply-by-hand.md) takes about an hour, and everything after that is
adding to it when the work asks for it.
