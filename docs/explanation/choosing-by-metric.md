# Choosing by metric

The point of keeping alternatives is that the authoritative metric, chosen by the solution's definition, picks the one
that runs, so nobody has to settle it by reading and debating each alternative. Judgment and other perspectives still
matter: they define the problems, ideals and metric, and they propose and improve the alternatives the metric compares.

The metric is one number that says which alternative is best across all factors, and a cascade estimates that same number at rising
cost: [a cascade runs one criterion](a-cascade-runs-one-criterion.md) ([how to write one](../how-to/write-a-cascade-that-stays-one-number.md)).

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

## Who beats whom: the highest result wins, and the verdict says how sure we are

The authoritative metric decides, and it is responsible for everything that matters to the solution. If cost, speed or simplicity
matter, they belong inside the metric (a balanced score with written weights is one way), not in a separate rule here.

The library's rule is one sentence: **the arm with the highest result on the authoritative metric at the latest comparable stage
wins and is selected, significant or not.** A new solution with no end users yet should still use the best thing it has, and so
should a solution whose lead is measured at a cheap stage because the costly stages have not been reached. Exactly equal results
keep the selected arm. What changes with the evidence is the wording of the verdict, never the choice:

- **Significant lead.** "b is better than a (exact McNemar test, Holm-adjusted p=0.004, 12 of 40 cases disagree)".
- **Best guess.** "best guess, not yet significant: b leads a (b 0.7 against a 0.55; exact McNemar test, Holm-adjusted p=0.0625,
  4 of 30 cases disagree); more cases would settle it".

When both arms have per-case results on the same cases (`esoi run --record` keeps them in `per_case.csv`), the leaderboard asks
the question a scientist would:

1. **Look only at the cases where the two arms differ.** A case both handle the same way says nothing about which is better.
2. **Does the leader win those cases more often than a fair coin would?** For pass or fail per case this is the exact paired
   McNemar test. For a metric that is a score per case (the balanced score), it is the exact sign test on the paired scores. The
   test is one-sided: the question is only "is the challenger better?". With several rivals, Holm's correction raises the
   p-values so that looking at many rivals does not manufacture a significant lead. The default significance level is 0.05.
3. **Only totals?** If per-case rows are missing but both arms have pass counts on the same cases and sample, Fisher's exact
   one-sided test on the two totals is used instead. It is weaker than the paired test (it cannot use the fact that both arms
   saw the same cases), so it needs a bigger gap, but it is still a test. The verdict names the test it used.
4. **No test possible?** A figure with no case counts (a balanced score recorded as one number, a public figure, one judgement) is
   compared on the point estimate and labelled a best guess.

Every pass rate is shown with its 95% Wilson interval, which shows how little a small sample says.

### Size the highest stage so a difference can reach significance

A best guess turns into evidence by measuring more cases, never by a margin. So size the highest cascade stage so that a meaningful
difference between arms could be significant there. The library invents no power threshold: the verdict's p and its count of
disagreeing cases show when a stage cannot settle it. If a stage keeps returning "4 of 30 cases disagree", the stage is too small
for the differences that matter, and the next stage should be larger. A solution whose highest stage always reads "best guess"
is telling you its metric cannot yet separate its arms. For a new solution that is fine: it uses the leader meanwhile.

### Stricter policy for production, optional

A solution with production end users may not want to move on a best guess. In `esoi.toml`, a `[switching]` table sets the project's
policy and a `[switching.<solution id>]` table sets one solution's, which overrides the project:

```
[switching]
alpha = 0.01                  # what counts as significant (a lower level than 0.05)
[switching.my-solution]
require_significance = true   # the selected arm stays until a rival is significantly better
min_cases = 30                # shared cases needed before a lead can count as significant
require_stage = "whole"       # a cascade stage the winner must have a result at (checked when promoting)
```

`require_significance = true` is the opt-in: with it, a lead that is not significant is a TIE and the verdict says so ("b is not
shown better than a (p=0.0625, 4 of 30 cases disagree); more cases would settle it"). `alpha` and `min_cases` set what counts as
significant, so by themselves they only change the wording of a verdict; with `require_significance` they decide whether the
selected arm stays. A value looser than the library default is read as the default. The verdict names the requirement that kept the
selected arm, for example "it is significant at alpha 0.05 but the solution requires alpha 0.01". `best_guess_switch = false` from
earlier versions is still read, as an alias of `require_significance = true`; it is deprecated.

A slice verdict for one circumstance (see [measure per circumstance](../how-to/measure-per-circumstance.md)) always requires
significance, because an add-on must show its marginal value over the baseline.

`esoi select --promote` follows the same verdict. `esoi evidence-table --file README.md` writes a table of every arm (interval,
cost per passing case and seconds for information, the verdict and its p-value) between two marker lines
(`<!-- esoi:evidence-table:begin -->` and `<!-- esoi:evidence-table:end -->`), with what others measured beside it and never
added to it. The mathematics is in `esoi/stats.py`, standard library only.

Whether a consumer takes a new selection the day it ships is the consumer's choice, not the library's: see
[pin selections for production and update on your schedule](../how-to/pin-selections-for-production.md).

## Verdicts

For a selected implementation, comparing it with its rivals on the same cases gives one of four verdicts.

| Verdict | Meaning |
|---|---|
| WIN | It has the highest result; the verdict says whether the lead is significant or a best guess |
| TIE | Exactly equal to a rival, or the policy requires significance and no lead is significant; the selection stays, and the verdict says what would settle it |
| LOSS | A rival has a higher result (significant, or a best guess); adopt it or write down why not |
| UNMEASURED | No rival was measured on the same cases |

## Adopting the winner

A LOSS is a decision, and `esoi select --promote` makes it from the evidence: it switches the solution's `selected`, the metric's
command and the reason, or prints exactly that for a person, by the solution's `promotion` cell. It only acts on rows with a
`cases_sha`, scored on the same cases and sample, whose results are current. See
[declare, call, measure, promote](graceful-selection.md).

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

A stage with `kind=idea` and a `scale` needs no implementation: qualitative questions about an idea are answered and converted to
a number by ratings or weights, and `scale` says where the meaning of every rating value is written. It evaluates ideas before
anything is built; like `public` it claims no results row and needs no gate.

### Expiration

A metric's optional `expiration` field answers "when do metrics need to be rerun?": `never` (the default when nothing is set) or
a number of days such as `90 days`. A project sets a default for all its metrics in `esoi.toml`, which a metric overrides:

```
[expiration]
default = "180 days"
```

Precedence, most specific first: the stage's `max-age-days`, the metric's `expiration`, the project's `[expiration] default`, and
with none of them a result never expires by age (`cascade.load_stages` applies it). A metric can say `never` against a project
default. Expiration is not staleness: a result whose implementation, cases or measured code changed is stale and counts as not run
whatever the expiration says (which files count as measured code is the staleness rule, see
[When metrics are run](when-metrics-are-run.md#staleness-and-expiration)); a stale row informs and is re-run when a decision depends on it. Expiration only decides when a result that
is still current is asked for again, and it applies through the cascade (a metric with no `cascading_conditionals` has no stages to
expire). Expiring the costly later stages lets an improved implementation be selected quickly from the earlier, cheaper ones; that
is not recommended for a high-stakes production system, which should instead require a significant gain
(`require_significance`, above) and pin its selections with [`esoi lock`](../how-to/pin-selections-for-production.md).

Guidance: the expected order of the stages is in [the first stage needs no model](first-stage-needs-no-model.md).

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
