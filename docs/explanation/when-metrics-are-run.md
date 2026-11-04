# When metrics are run

A Metric is what gets run. A set of cases, a scorer and a harness are only how a particular metric is implemented. Running
a metric costs time and sometimes money, and a result is only worth deciding from while it is current. So *when* each metric
is run is a design question with the same shape as any other: it is a solution, with a problem, ideals, alternative
implementations and a metric of its own. This page writes it that way, using the records described in
[intent-types.md](intent-types.md); the questions each record must answer are in [the templates](../reference/templates/), in the
author's words, and are not repeated here. A fill-in version for your own repository is
[metric-run-policy.md](../reference/templates/metric-run-policy.md).

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

A written policy per repository (the template is [metric-run-policy.md](../reference/templates/metric-run-policy.md)) that names, for
every Metric it governs, when it is run, in what stages, with what limit, who approves, and when its result stops counting.
The practice that has worked is below; each repository records its own version.

### Run a metric when what it teaches is worth what it costs

Metrics are not run for their own sake. A run is worth making when what it will teach (whether a change helped, which
alternative is better, whether a decision still stands) is worth the time and money it takes; the metric's cascading
conditionals are where that is written down. Code can change many times a day when an AI is working, and a metric re-run after
every change measures an implementation that is about to change again. So the default is to improve first and measure when a
choice turns on the number, and a changed file only informs: it says which recorded results no longer describe the code, it
does not order a run.

A metric whose implementations call no paid service and touch no live system is cheap, so while you work run the part that
covers what you changed, not everything, and run the rest when you are about to rely on the result. No commit hook and no step of
continuous integration runs metrics: a hook or a pipeline would turn every commit into a measurement nobody asked for. Continuous
integration runs the tests, the structure check and the hygiene scan.

An offline arm that counts the calls of a deterministic stand-in for a model declares itself (`SIMULATED = True`) so that it is
run with the offline arms. Its cost is then known to be zero; a missing price alone never makes an arm free, and never makes it
paid.

**Offline means no model.** The harness refuses to start a model command (`claude`, `codex`, `gemini`) in a run of an arm that is not
declared live (`PAID = True`, a `paid_arms` entry, or a run given `--max-calls`): the attempt raises an error in the case, is counted in
the row's details beside the metered calls, and `ESOI_OFFLINE=1` is set for a provider that wants to refuse by itself. A provider
that falls back to a binary found on the machine cannot make an offline run spend money.

**A cassette run can be a free stage.** With `--cassette DIR --cassette-only` the harness answers every wrapped model call from a
file of earlier responses and errors on a call it does not hold, so the run cannot spend anything. A change to scoring or parsing of
a paid arm is therefore checked first against the recorded responses (a free stage), and the paid stage runs only when that passes.
A cassette hit in an offline run is allowed (no process starts); a miss there is refused. How:
[Iterate on an LLM arm without repeating model calls](../how-to/iterate-on-an-llm-arm-without-repeating-model-calls.md).

The contract for a provider of models, in any package: **`ESOI_OFFLINE=1` in the environment means no model process may start.** A
provider that launches a model program (a command-line client, a local server, a subprocess of any kind) checks the variable before it
launches and refuses with an error that says so; it neither falls back to another binary nor reads a missing variable as permission to
go on. ESOI sets it for the length of an offline harness run (restoring the earlier value afterwards) and for the whole of
`esoi.entry`'s offline check, which also blocks sockets and every child program that is not local. The variable is a second guard
beside the harness's own refusal: the first stops the common launch paths, the second lets a provider stop itself.

### Results are recorded on committed code

A recorded result carries the commit it was run on and a hash of the case files. Record a result you will decide from on
committed code, so that the number can be reproduced by anyone. A result recorded on uncommitted code is shown but not trusted.
Whether to re-record after a change depends on the change: see [When a result is stale](#staleness-and-expiration).

### Live, paid arms run only when a decision depends on them

Run a metric that spends money, or touches a live service, when a choice turns on it: a new alternative to try, a selection to
change, or a suspected regression. Do not run it because it is Tuesday. Work up in stages:

1. **Estimate the cost first**, from the number of calls and the price per call, and write it down.
2. **Stage the sample:** a handful of cases (3), then a larger spread (10), then more (30), moving on only when the last stage
   looked right. Choose the cases as a small stratified sample, so every kind of case is represented, rather than the first few
   in the file. The same sample every time, so a smaller run is a prefix of a larger one.
3. **Set a call budget** the run cannot exceed; the run stops when it reaches it.
4. **Run the full set** only if a decision still depends on it after the staged runs.

### Do not run what cannot inform a decision

Two cases are known in advance to teach nothing, so the tools refuse them (`esoi.run_guards`), with the remedy in the same line.

- **A perfect arm already caps it.** If another arm of the same solution passed every case on the same cases and the same
  sample, and the result is current, an arm that may spend money cannot score higher on accuracy. A metric that is pass or fail
  only (ties broken by cost) refuses it unless its recorded cost per case is known and lower. A metric that weighs cost and
  time (`[balance.<component>]`) refuses it only when its recorded cost and seconds per case are both known and neither is lower,
  because a cheaper or faster arm can still win the balanced score; an unknown cost or time is never read as a loss. An arm that
  cannot spend money is never refused, since running it is free. `esoi run --stale` skips such an arm and says so (an arm named
  with `--include` is a person's decision and runs). `--force "reason"` runs it anyway.
- **The result is already public.** A number that an independent source published for the same candidate on the same benchmark
  need not be measured again to be known. A component declares its public benchmark, and when the project's evidence has an
  independent row for the arm on it, the run is refused and the public value is printed. A run is worth its cost only where
  something differs from what is known: the implementation or method, or the metric. So the run states what differs
  (`--differs "harness: ..."`, or `prompt`, `settings`, `corpus`, `metric`), or `--force "reason"`.

Every override is recorded in the row's `details`, so a later reader sees why a run that looked redundant was made.

### Iterate on the failing cases before the whole set

The skill says: "All runs are recorded and saved even if stopped midrun. When building or improving an implementation, improvements
are made immediately after a single failure case without needing to run the rest of the metric. The failing case or cases are rerun
by themselves and a run on all cases is not done until the failing cases are solved." The tools follow it with four small parts.

- **Every run is saved.** `esoi run` appends each case to `runs.csv`, beside the results log, the moment the case finishes, with a
  line when the run starts and one when it ends (`done`, or `stopped: ...` for Ctrl-C, a spent call budget or a crash). A killed run
  keeps what it scored. The leaderboard and the cascade never read this log; a run counts for them only when `--record` also put its
  summary in the results log.
- **An unrecorded run stops at the first failing case**, so the implementation is improved at once. A recorded run is a whole
  measurement, so it runs every case; `--keep-going` makes an unrecorded run do the same. Stopping by default (rather than only on a
  flag) is the more evolvable choice because the unrecorded run is the one used while improving, and the option that needs a flag
  should be the one that spends more.
- **`--failed` reruns only the cases that failed last** for that implementation on those cases (the latest outcome of each case in
  `runs.csv`), as a run of named cases, so it records as `only:` rows and never decides a verdict.
- **A run of every case waits for them.** While cases that failed in a development run have not passed since, a whole-set run is
  refused with the cases named; `--force "reason"` overrides it and the reason is recorded in the row's `details`. A failure inside
  a finished, recorded whole run is a measurement (a baseline that fails by design is one), so it does not block.

The cascade does not repeat itself either: a later stage that covers cases an earlier stage ran for the same implementation version
and cases reuses their rows (the run says so, and `details` records how many) and runs only the rest. A changed implementation has
another version, so nothing is reused and the stage is run in full again, which is the re-record the skill allows. Code with
uncommitted changes, or of no known version, is never reused. Pass `--fresh` to run every case anyway.

Improving comes before measuring, both for agility and to avoid the waste of reruns: improvements that are known and not blocked are
finished before a metric is run. Running without `--failed`, an unrecorded `esoi run` that finds unsolved failures reruns just those
cases and says so (pass `--force "reason"` for the whole set); a recorded run of every case is refused until they pass.

A metric that is expensive, or on a large set of cases rather than a representative sample, normally carries other conditions
that say when it is worth running, such as a weekly release frequency or a person's approval. A stage's `when=` holds that
condition in words (`when=once a week, on the release day` or `when=Joshua approved the spend`); a program reports it and never
evaluates it, so a person or an AI judges it. When approval is required is itself something to improve through the specifications:
record what the approver learned and let the condition get narrower.

`esoi check` prints a note (never an error) for a metric whose cascade departs from the skill's expected order (an idea stage first,
then a free stage, a real single case, growing sets): a first stage that
may call a model, a later model-calling stage covering fewer cases than the one before (a free full-set stage followed by a single real case is as expected: cases only need to grow among stages of the same cost kind), or a last stage narrower than an earlier model-calling stage. See
[The first stage needs no model](first-stage-needs-no-model.md).

### Someone approves spend

A paid run is approved by the person or role that bears its cost, before it starts, against the estimate. A run that stays
inside an already-approved budget (the staged sample on a development system, say) may be pre-approved in the policy. Write
down who, so nobody has to guess.

### Staleness and expiration

A recorded result is **stale** when it no longer describes what it measured:

- it has no commit, or was recorded on uncommitted code;
- the case files are not the ones it was run on (their hash differs);
- code the arm measures changed since the commit it was recorded on;
- the model, the price or the service behind it changed.

The first three can be checked by a tool and should be. The last needs a person or a scheduled run.

**What an arm measures is a choice between alternatives, measured like any other.** The staleness rule is the solution
`know-what-a-result-measures`, with three arms scored by `esoi run staleness_precision` over a fixture of commits: any file of
the repository's code paths or the evaluation folder (`repo_wide`, the baseline: safe, and every commit makes every component's
rows stale), the files the ownership map gives the arm's solution and implementation (`component_paths`), and the files the arm's
module imports, found by reading the source without running it (`import_closure`). A rule must never keep a row whose measured
code changed (a false-fresh is a hard fail that disqualifies the arm); among the rest, the one that calls a result stale for
nothing least often is selected. The measurement selected `import_closure`, and disqualified `component_paths`, because a shared
utility the arm imports may be owned by another component, which the ownership map does not say. Every arm falls back, per
component, to a safer rule: a non-Python arm or a computed import falls back to `component_paths` plus the files the scan did find, and a component with no
ownership entry keeps `repo_wide`, so a result is never silently fresh. A file in the code paths that no component owns counts for
every arm. [Choose when a result is stale](../how-to/choose-when-a-result-is-stale.md) says how to set the rule and read why a row
is stale.

**A stale row is information, not an order to re-run.** `esoi run --stale` reports each stale row with the changed file and the
component that owns it, and re-runs only what is worth running: a selected arm that was never measured, a selected arm whose
metric (or the project) declares an expiration that has passed, a selected arm a pending decision or release depends on
(`--for-decision`), or an arm a person names (`--include`). Rival arms and rows nothing depends on are listed as not re-run.
`--all` is the older behaviour, re-running every stale arm. `esoi check` reports a changed file or a missing row as advice: it never
fails the check and never blocks a commit.

**Expiration is a separate thing.** A result that is still current can be asked for again after a time: a metric's optional
`expiration` field (`never`, or a number of days), a project default in `[expiration]`, or a stage's `max-age-days`, the most
specific winning. Expiration is never unless a metric or the project declares one. See
[Choosing by metric](choosing-by-metric.md#expiration), which also says why expiring costly stages is not recommended for
high-stakes production systems.

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
| On every change | whenever what a metric measures changes (by hand, never from a commit hook or a CI step) | the metric is offline, fast and what changed is what it measures | runs that teach nothing when the code is about to change again |
| On a schedule | at a fixed interval | the world moves on its own clock (models, prices) | runs that change nothing |
| On a decision | when a choice depends on the result | the metric is paid or slow | a decision made late if nobody asks |
| On drift | when a signal says something moved | a cheap probe can detect the change | a probe to build and maintain |

A typical policy combines them: offline metrics when what they measure changed and a decision may depend on them, paid metrics on a decision, and a scheduled re-measurement of
the selected alternatives.

## Stages are one number, not several criteria

The stages of a cascade are the same single number (a balanced score across accuracy, cost, time and size, weights fixed before any
alternative is scored) estimated at rising cost and fidelity. Kinds of cases are case sources mixed in proportion to real inputs, not
stages with their own pass tests, and a "must not regress" guard from one stage to the next is a second criterion in disguise. See
[a cascade runs one criterion](a-cascade-runs-one-criterion.md); rules S41 to S44 advise where a repository departs from it.

## The metric of the policy

How would you know the policy works? Three records of it are worth keeping: the share of decisions that were backed by a
current result, the spend per decision, and the number of stale results found late (at a release, say, rather than at the
change). The first two are counted by hand or from the results log; the third is what a strict check reports.

## Tools

The Python implementation reports a stale result and the file behind it (`esoi check --strict` as advice, `esoi run --stale --plan`,
`esoi stale --explain <component>`), re-runs and re-records what is worth running (`esoi run --stale`), runs a staged sample with a budget (`esoi run <component> --impl <name> --sample 3 --max-calls N`), and
records the time the check itself takes. See [apply-with-tools.md](../how-to/apply-with-tools.md).
