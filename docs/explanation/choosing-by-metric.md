# Choosing by metric

The point of keeping alternatives is that the authoritative metric, chosen by the solution's definition, picks the one
that runs, so nobody has to settle it by reading and debating each alternative. Judgment and other perspectives still
matter: they define the problems, ideals and metric, and they propose and improve the alternatives the metric compares.

## Run alternatives on the same cases

A metric is a set of cases and a way to score an implementation on them. Each implementation is run on the same cases and
the result is recorded with the commit, a hash of the case files and the sample (blank for the full set). Only results
with the same case hash and the same sample are compared: a score on different cases is not evidence, and 458 of 1,137
cases is not comparable with 12 of a 40-case sample.

## Every metric outputs a number

Every metric outputs a number, so they are all the same kind. A rule that holds or does not, such as "a write stays inside
its folder", is measured as the pass rate on its cases. Implementations are ranked by the metric. When a solution has more
than one metric, its `authoritative_metric_id` names the one that decides which implementation is best; the others can be
combined with it, for example with cost or time.

A solution with a single implementation has nothing to be compared with, so its cases must be able to fail: it keeps a
deliberately naive baseline in its component's `broken/` folder, and the cases must fail it. That proves the cases can tell
good from naive.

A solution none of whose metrics has a command that records a run (`esoi run <component> --impl <name>`) is a specification: defined, with alternatives, but not measured
yet. That is derived from the missing run and never declared. Its next step is a milestone, a value of its metric.

## Verdicts

For a selected implementation, comparing it with its rivals on the same cases gives one of four verdicts.

| Verdict | Meaning |
|---|---|
| WIN | It beats every rival, by pass rate or by clearly lower spend at the same pass rate |
| TIE | A rival is inside the noise; the selection is kept for a stated reason, not decided by the number |
| LOSS | A rival beats it; adopt the rival or write down why not |
| UNMEASURED | No rival was measured on the same cases |

## Adopting the winner

A LOSS is a decision, and `esoi select --promote` makes it from the evidence: it switches the solution's `selected`, the metric's
command and the reason, or prints exactly that for a person, by the solution's `promotion` cell. It only acts on rows with a
`cases_sha`, scored on the same cases and sample, whose results are current. See
[declare, call, measure, promote](graceful-selection.md).

## Noise

Runs that call a model move between repeats of the same code, so a small gap between two of them is noise. Use exact
counts when nothing was sampled, and a pass-rate margin and a spend tolerance when something was. State the margin where
the comparison is made rather than reading differences into it.

## Stand-ins

A metric must be meaningfully real (see [a metric must be meaningfully real](metrics-must-be-real.md), rule S31): a stand-in
arm is for unit-testing plumbing and for the harness's own tests, and `esoi check` reports a metric whose arm declares
`SIMULATED = True`.

An arm that meters a deterministic stand-in for a model declares `SIMULATED = True`: it spends nothing, so it records cost 0.0
and model `simulated`, and it is compared on model calls. A missing price alone never makes an arm free or paid.

## Reference arms

Some implementations are not rivals. A **baseline** is a floor someone might plausibly ship and is compared. An
**ablation** is part of a candidate measured alone, and a **validity** arm checks the metric itself, so neither is offered
as the thing to adopt. Mark each by the first word of its description.

## Cascading conditionals

A metric that costs to run lists its stages, cheapest first, in its `cascading_conditionals` field. A stage names which
results belong to it (`sample`, `real`), what a result must show before the next stage is worth running (`gate`,
`min-pass-rate`), when a result expires (`max-age-days`) and any other condition (`when`):

```
offline [sample=full | real=no | gate=all-pass] > staged [sample=sample | real=yes | gate=competitive | max-age-days=90 | when=a person approved the spend] > whole [sample=full | real=yes]
```

`esoi cascade [SOLUTION]` shows, for every implementation, the result at each stage (a stage that was not run says so; it
is never estimated), which implementation the cascade chooses, and the next stage worth running with the `esoi run` line
that records it. Downstream users take the implementation with the highest result at the latest stage that has been run,
unless another implementation scored higher at an earlier stage the two share and has not been run at the latest one: it
stays chosen until it is. A result expires when the measured code or the cases changed, or when it is older than the
stage allows; an expired result counts as not run. Rule S32 checks that the list can be read and S33 that `selected` is the
implementation the cascade chooses.

Guidance: make the first stage one that needs no model; see [the first stage needs no model](first-stage-needs-no-model.md).

## When to run

Running a metric costs time and sometimes money, and a result only supports a decision while it is current. See
[when-metrics-are-run.md](when-metrics-are-run.md).

## Humility

We do not know what is best, so we let metrics decide, and even then a metric is a limited approximation of an intent
that words express imperfectly, and the intent itself may or may not be worthwhile. When the metric and your judgment
disagree, treat the disagreement as information: about the metric, and possibly about the intent. A metric can itself be
a solution with alternative implementations (including versions of its cases), so refine it, and keep the old version
so past results stay comparable. Perspectives are implementations too: collaboration and other points of view are how
better alternatives arrive.
