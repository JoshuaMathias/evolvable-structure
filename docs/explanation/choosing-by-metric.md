# Choosing by metric

The point of keeping alternatives is that a metric, not an opinion, picks the one that runs.

## Run alternatives on the same cases

A metric is a set of cases and a way to score an implementation on them. Each implementation is run on the same cases and
the result is recorded with the commit and a hash of the case files. Only results with the same case hash are
compared: a score on different cases is not evidence.

## Say whether best can vary

- An **eval** solution has implementations that differ on the metric: a cheaper way, a more accurate way. They are ranked.
- An **invariant** solution is a rule that holds or does not, such as "a write stays inside its folder". It is not
  ranked. It keeps its cases and a recorded run, and a deliberately naive baseline that its cases must fail, which proves
  the cases can tell good from naive.

## Verdicts

For a selected implementation, comparing it with its rivals on the same cases gives one of four verdicts.

| Verdict | Meaning |
|---|---|
| WIN | It beats every rival, by pass rate or by clearly lower spend at the same pass rate |
| TIE | A rival is inside the noise; the selection is kept for a stated reason, not decided by the number |
| LOSS | A rival beats it; adopt the rival or write down why not |
| UNMEASURED | No rival was measured on the same cases |

## Noise

Runs that call a model move between repeats of the same code, so a small gap between two of them is noise. Use exact
counts when nothing was sampled, and a pass-rate margin and a spend tolerance when something was. State the margin where
the comparison is made rather than reading differences into it.

## Reference arms

Some implementations are not rivals. A **baseline** is a floor someone might plausibly ship and is compared. An
**ablation** is part of a candidate measured alone, and a **validity** arm checks the metric itself, so neither is offered
as the thing to adopt. Mark each by the first word of its description.

## When to run

Running a metric costs time and sometimes money, and a result only supports a decision while it is current. See
[when-metrics-are-run.md](when-metrics-are-run.md).

## Humility

A metric is a limited approximation of an intent that words express imperfectly. When the metric and your judgment
disagree, treat the disagreement as information about the metric: refine it, and keep the old version so past results
stay comparable.
