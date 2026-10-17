# When metrics are run

A Metric is what gets run. A set of cases, a scorer and a harness are only how a particular metric is implemented. Running
a metric costs time and sometimes money, and a result is only worth deciding from while it is current. So *when* each metric
is run is a design question with the same shape as any other: it is a solution, with a problem, ideals, alternative
implementations and a metric of its own. This page writes it that way, using the records described in
[intent-types.md](intent-types.md); the questions each record must answer are in [the templates](../templates/), in the
author's words, and are not repeated here. A fill-in version for your own repository is
[metric-run-policy.md](../templates/metric-run-policy.md).

## The problems

- **Results are stale when a decision is made.** The code or the cases changed after the number was recorded, or the number
  was recorded on code nobody can reproduce, and the choice rests on it anyway.
- **Paid runs happen without a decision behind them.** A full run of a model-calling metric is started out of habit, and the
  money is gone before anyone asked whether the answer was needed.
- **Runs are so heavy that nobody runs them.** A metric that takes an hour or a thousand calls is skipped, and then nothing
  is measured.
- **The world moves under a good result.** A model version or a price changes, and an old number quietly stops describing
  what ships.

## The ideals

- **A decision is always backed by a current result.** Anyone about to choose between alternatives can see when each was
  measured, on which commit and on which cases, and whether that still holds.
- **Spend is proportionate to the decision.** Cheap questions are asked often and expensive ones only when something depends
  on the answer.
- **Spend is approved before it happens.** The person who bears the cost knows the estimate and has said yes.

## The solution

A written policy per repository (the template is [metric-run-policy.md](../templates/metric-run-policy.md)) that names, for
every Metric it governs, when it is run, in what stages, with what limit, who approves, and when its result stops counting.
The practice that has worked is below; each repository records its own version.

### Offline arms run on every change

A metric whose implementations call no paid service and touch no live system can run whenever the measured code or its
cases change: before committing, and again in continuous integration. It is cheap, deterministic, and it is what keeps the
structure honest. Run the part that covers what you changed, not everything, while you work; run all of it before you rely
on the result.

### Results are recorded on committed code

A recorded result carries the commit it was run on and a hash of the case files. Re-record after any change to the measured
code or the cases, from committed code, so that the number can be reproduced by anyone. A result recorded on uncommitted code
is shown but not trusted.

### Live, paid arms run only when a decision depends on them

Run a metric that spends money, or touches a live service, when a choice turns on it: a new alternative to try, a selection to
change, or a suspected regression. Do not run it because it is Tuesday. Work up in stages:

1. **Estimate the cost first**, from the number of calls and the price per call, and write it down.
2. **Stage the sample:** a handful of cases (3), then a larger spread (10), then more (30), moving on only when the last stage
   looked right. Choose the cases as a small stratified sample, so every kind of case is represented, rather than the first few
   in the file. The same sample every time, so a smaller run is a prefix of a larger one.
3. **Set a call budget** the run cannot exceed; the run stops when it reaches it.
4. **Run the full set** only if a decision still depends on it after the staged runs.

### Someone approves spend

A paid run is approved by the person or role that bears its cost, before it starts, against the estimate. A run that stays
inside an already-approved budget (the staged sample on a development system, say) may be pre-approved in the policy. Write
down who, so nobody has to guess.

### Staleness

A recorded result is **stale** when any of these holds:

- it has no commit, or was recorded on uncommitted code;
- the case files are not the ones it was run on (their hash differs);
- the measured code, or the implementations that drive it, changed since the commit it was recorded on;
- the model, the price or the service behind it changed.

The first three can be checked by a tool and should be. The last needs a person or a scheduled run.

### Re-measure when the world moves

Models and prices change under results that were once true. Re-measure on a schedule that matches how fast they move, and
immediately when a change is announced. A re-measurement is a decision-triggered run: the question is "is the selected
alternative still the best one?"

### Offline cases are a proxy, not the whole measure

Cheap offline cases make frequent measurement possible, but what matters is the problem solved in the real system, in the
wild: a test of the real thing outranks a unit test, and an outcome measure outranks task completion. So a solution whose
intent is about live behaviour keeps a measure of the real outcome as its authoritative metric where one is practical. The
policy decides how often that live measure is run and what it may spend, not whether it counts.

## The alternatives

The same question has several answers, and a repository can keep two alive to compare them.

| Alternative | Runs the metric | Good when | Costs |
|---|---|---|---|
| On every change | whenever measured code or cases change | the metric is offline and fast | nothing, until the metric gets slow |
| On a schedule | at a fixed interval | the world moves on its own clock (models, prices) | runs that change nothing |
| On a decision | when a choice depends on the result | the metric is paid or slow | a decision made late if nobody asks |
| On drift | when a signal says something moved | a cheap probe can detect the change | a probe to build and maintain |

A typical policy combines them: offline metrics on every change, paid metrics on a decision, and a scheduled re-measurement of
the selected alternatives.

## The metric of the policy

How would you know the policy works? Three records of it are worth keeping: the share of decisions that were backed by a
current result, the spend per decision, and the number of stale results found late (at a release, say, rather than at the
change). The first two are counted by hand or from the results log; the third is what a strict check reports.

## Tools

The Python implementation reports a stale result (`esoi check --strict`), re-runs and re-records what is stale
(`esoi run --stale`), runs a staged sample with a budget (`esoi run <component> --impl <name> --sample 3 --max-calls N`), and
records the time the check itself takes. See [apply-with-tools.md](../guides/apply-with-tools.md).
