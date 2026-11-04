# What a metric includes

A metric is one number that says which alternative is best. "Best" covers more than whether the answer was right, so a metric
that counts only correct answers picks the arm that is right and slow, costly or unsafe. This page lists what to ask of any new
metric, then shows the list at work on nine different subjects. It is a checklist for the person or AI who designs the metric,
not a form to fill in: leave out an item only because it does not apply, and say so.

## The metric is the judgment, so it must hold the whole judgment

The authoritative metric of an intent, and every condition in its cascade, is applied automatically: the arm it ranks first is
selected and runs, with no person looking at the choice. So the metric is not a scoreboard beside the decision; it is the decision.
It has to say, in a form a tool can check, everything a careful, critical person would weigh when choosing what is best: the
outcome, but also cost, time, risk, reversibility, how the result is experienced by the people it serves, maintenance burden, trust
in the evidence, and whatever else would change their mind.

The test for every metric and every stage condition: **if a thoughtful person, shown the same results, would pick differently,
the metric is wrong.** Find the reason they would give and capture it:

- a reason that grades the outcome (a reply that is correct but rude, a plan that works but cannot be undone) becomes part of the
  outcome's grading;
- a reason that is a cost (an hour of a person's attention, load on a server) becomes a priced cost;
- a reason that is a line not to cross (privacy, safety, an irreversible act) becomes a gate;
- a reason about doubt (too few cases, results from someone with a stake, a benchmark unlike the real work) becomes an evidence
  condition on the stage, so a weakly supported winner is not selected.

When a person overrides an automatic selection, or disagrees with a result, treat it as a defect report against the metric: write
down their reason, add the component, gate or condition that encodes it, and re-score every arm, the old winner included. Do not
patch the selection by hand and leave the metric as it was, or the next automatic run repeats the mistake. A reason that cannot be
measured yet is still written in the metric's limits line, so the gap is visible instead of silently ignored.

## Three ways a metric can lean on other metrics

Before writing a metric from nothing, check whether someone else's work already answers part of it.

1. **Public results for public implementations.** When the arms being compared are public (a published embedder, a vendor model,
   an open-source library), their published results on public benchmarks enter at the `public` stage as graded evidence and are
   not re-run. We run only what no one has published: our own candidates, or a small confirmation sample on our cases. Grading:
   [judge public evidence like a scientist](judge-public-evidence-like-a-scientist.md); how:
   [use public evidence](../how-to/use-public-evidence.md).
2. **A generic metric that several public benchmarks fit into.** Define the metric by what matters ("the context a task needs is
   shown, in order, with little noise, at a cost"), then let each public benchmark feed it through an adapter. How:
   [fit public benchmarks into one generic metric](../how-to/fit-public-benchmarks-into-one-generic-metric.md).
3. **A consumer builds on the metric of a solution it uses and customizes.** The consumer references the foundation metric, reuses
   results whose arm and case digests match, adds only its own cases and costs, and may tighten but never loosen the foundation's
   gates. This is the "building on a foundation metric" mechanism (TODO: link its page here once it is published).

The first way saves runs, the second saves writing one metric per benchmark, the third saves a consumer from starting over.
They combine: a consumer's metric can build on a generic one whose adapters read public results.

## The checklist

- **Outcome, graded, on cases that mix the kinds that occur in reality.** Needed, helpful and irrelevant; or pass with partial
  credit. State each kind's share of the cases and fix the shares before scoring, from a sample of real inputs and not from what
  is easy to write.
- **Cost.** Model dollars, compute, source access (records, bytes or calls read from systems of record per request), human
  minutes, index or store size. Price each by a committed constant so two runs price the same work the same way.
- **Time.** Latency per request. Build or bootstrap time is amortized and charged where it is spent, so a fast arm that needs a
  slow one-off build is not shown as free.
- **Risk as gates, not weights.** Privacy scope (nothing read or shown outside the reader's scope), load on production systems
  (no full scan per request; a read budget), irreversible or outward acts, safety. A gate that is broken fails the stage whatever
  the score, because a high score must not buy back a harm.
- **Robustness across kinds.** A stage is not passed by winning one kind of case while losing another beyond a stated tolerance.
  Anything learned from data is checked on held-out cases and on a later time period.
- **Abstention.** A request that needs nothing should get nothing. Showing noise costs, and cases where the right result is to do
  less belong in the set.
- **Freshness.** When results or data age, the metric says stale instead of silently reusing (see
  [when metrics are run](when-metrics-are-run.md#staleness-and-expiration)).
- **Evidence quality.** Public results are graded. Sample sizes and intervals are stated. When a scorer mis-scores, fix the
  scorer for every arm; never tune it for one arm.
- **A cascade whose conditions can be checked.** Each stage's condition is something a tool can verify: cases per kind are
  present, pins and hashes match, the held arm and the challenger saw the same case digest, an inherited foundation stage was
  passed. See [a cascade runs one criterion](a-cascade-runs-one-criterion.md).
- **Weights fixed before scoring.** The balance between outcome, cost and time is written and committed first, with a reason, and
  changed later only by re-recording the arms. Otherwise the weights drift toward the arm someone already likes.
- **What it cannot see.** One sentence on what the metric does not cover, so a reviewer knows what its number is silent about
  (see [a metric must be meaningfully real](metrics-must-be-real.md)).

## Nine examples

The subjects differ on purpose. Notice how much is the same: an outcome, a cost, gates, and a statement of public evidence.

1. **Context retrieval (a library, generic).** Needed context shown within a token budget, in order, with little noise, and
   nothing when nothing is needed. Public adapters: an ordering benchmark for ranking, a long-term-memory benchmark (memory,
   knowledge update, abstention), commit-topic data from several public repositories for code. Public evidence: published scores
   of dense embedders, used at the `public` stage without re-running. Cost: tokens shown, index size, source reads per request.
   Gates: no live full scan; the scope fence holds.
2. **Context selection for an assistant (a consumer customizing 1).** Builds on the retrieval metric and the store bootstrap
   metric; adds private real requests with metadata (source, author, recency, grouping), the consumer's own source-access cost,
   and its grouping modes (a hard fence against soft affinity, measured by cross-grouping recall). Tightened gate: one person's
   private items never reach another person's answer.
3. **Store bootstrap (its own solution).** Cost per source item ingested, incremental refresh against a full rescan, staleness lag,
   store size. Gate: read load on the source system under a budget. Every selection arm shares it, so it is a solution of its
   own, not a part of one arm.
4. **Model tier choice.** Passing work per dollar for a tier. Public adapters: math, coding and reasoning benchmarks and vendor
   scores (graded; contamination checked); prices from price pages with a checked-on date. Run only a small confirmation sample on
   our own task cases.
5. **Speech to text for voice input.** Word error rate at a latency and a cost. Public: open leaderboards for public models. A
   consumer adds its users' own recordings (private) on top and inherits the public part.
6. **Outreach email (not code).** Reply or meeting rate per send. Cost: sends and human review minutes. Gates: unsubscribe
   present, complaint rate under a ceiling, no unapproved send. Public evidence: published industry reply rates as a prior only,
   graded low because the audiences differ.
7. **Grant proposal drafting (not code).** Reviewer score or funded rate; a leading indicator is the human edits needed per page.
   Cost: model dollars plus human hours. Public evidence: a funder's published success rates as a base rate.
8. **A personal training plan (life).** The weekly goal kept and progress toward the target distance. Gates: weekly load increase
   under a stated cap; a pain report stops progression. Public evidence: sports-science guidance, graded by study quality.
9. **A card builder (bootstrap quality).** A topic request finds its grouped card; cost is cards per file and build seconds. Its
   public adapter: co-change topics from several public repositories.

## Why a list at all

A metric is the one place people steer from, so a missing factor is a decision made silently for them. The list is short enough
to read each time and is the reason the same few parts recur above. When a factor does not fit any item, add it to the metric and
tell the reviewer; the list grows from use.
