# When this repository's metrics are run

The filled-in [metric run policy](../docs/reference/templates/metric-run-policy.md) for this repository. The records are in this folder
(and in its sub-intent folder); this page is the readable version.

## Problem and ideal

The problem is `prob-metrics-run-at-the-wrong-time` and the ideal is `ideal-timely-affordable-evidence`. The solution is
`when-metrics-are-run`, whose selected implementation runs a metric when a decision needs its result; it governs every other Metric
through `governs_metric_ids`, and each of them names it in `run_policy_ids`.

## The decision

| Alternative | Used here | Why |
|---|---|---|
| On every change | no | A changed file informs (`esoi run --stale --plan`); with code changing many times a day, rerunning each metric after each change spends time and tokens and mostly repeats what is known |
| On a schedule | no | No recorded metric drifts with a model or a price while only offline arms are recorded |
| On a decision | yes, for every metric | A metric runs when what it teaches is worth its cost: an offline arm when you want its result for the part you changed, an arm that calls a model only when a choice depends on it and Joshua approved the spend |
| On drift | no | Nothing here drifts with the world |

## One number at every stage

A cascade here is one criterion at rising fidelity: every stage of a metric reports the same number (the balanced score where the
component sets `[balance.<component>]`), kinds of cases are case sources of that number, and no arm is excluded by a mark: a trivial
arm that wins means the metric lacks a factor. See [a cascade runs one criterion](../docs/explanation/a-cascade-runs-one-criterion.md);
`esoi check --findings` lists rules S41, S42, S44 and S45.

## The metric runs

| Metric | Arm | Trigger | Stages | Call budget | Cost | Approver | Stale when |
|---|---|---|---|---|---|---|---|
| every other metric in `metrics.csv` | offline | when code it measures or its cases changed and the result is wanted (by hand; a changed file informs and never orders a run) | the whole set | none, no model is called | none | none needed | the cases changed, code the arm measures (the files its module imports, by the `import_closure` rule; `esoi stale --explain <component>` names them) changed since the recorded commit, or it was run on uncommitted code |
| `metric-readme-glanceability` (every intent folder reads at a glance) | offline | when `esoi/understanding/readable_records/readme.py`, `esoi/understanding/readable_records/diagram.py` or its cases changed and the result is wanted | the whole set | none, no model is called | none | none needed | as above; the adopting repositories it reads are named by `ESOI_GLANCE_ADOPTERS`, and a machine without them runs this repository's cases only |
| `metric-navigable-records` (a solution's spec and code can be found from each other) | offline | when `esoi/structure/intent_registry/besidecode.py`, `esoi/understanding/readable_records/readme.py`, `esoi/structure/structure_check/rules/beside_rules.py` or its cases changed and the result is wanted | the whole set | none, no model is called | none | none needed | as above; the adopting repositories it reads are named by `ESOI_GLANCE_ADOPTERS`, and a machine without them runs this repository's cases only |
| `metric-skill-copy-agreement` (sync drift and leak detection) | offline | when `esoi/understanding/the_standard/skill_distribution/skill.py` or its cases changed and the result is wanted; the live freshness check also runs after an edit of the author's skill, where its source and private term list are reachable | the whole set | none, no model is called | none | none needed | the cases changed, `skill.py` changed since the recorded commit, or it was run on uncommitted code |
| `metric-esoi-behaviour-adherence`, arms `reference_good` and `reference_bad` (validity) | offline | when the cases, `esoi/understanding/esoi_for_ai/behaviour.py` or the arms changed and the result is wanted | the whole set | none, no model is called | none | none needed | the cases changed, code the arm measures (the files its module imports, by the `import_closure` rule; `esoi stale --explain <component>` names them) changed since the recorded commit, or it was run on uncommitted code |
| `metric-esoi-judge-agreement`, arm `regex_only` (validity) | offline | when its cases, which follow the behaviour cases, changed and the result is wanted | the whole set | none, no model is called | none | none needed | as above |
| `metric-esoi-behaviour-adherence`, arms `standing_instructions`, `skill_on_request` and `no_skill` | paid | on a decision: choosing between ways of giving an agent the principles, a change to the skill that should be checked, a new model | a stratified sample of 3, then 10, then 30; the whole set only if the 30 is not clear; stop and report after each stage | 3 calls per case for each arm (9, 30 and 90 per arm by stage) | about 1 to 3 USD for all three arms and the judge across the three stages, from the assumptions below; none on a subscription command | Joshua | the cases changed, the skill or `esoi/understanding/esoi_for_ai/behaviour.py` changed since the recorded commit, the model changed, or it was run on uncommitted code |
| `metric-esoi-judge-agreement`, arm `model_judge` | paid | on a decision: before a behaviour score judged by a model is trusted, and when the judge's model changes | a stratified sample of 3, then 10, then 30 labelled replies, then the whole set once a person has filled `human_verdict` for a sample | 1 call per reply (3, 10 and 30 by stage) | included in the estimate above | Joshua | as above, or the labels changed |
| `metric-structure-quality-agreement`, arms `balanced_static` and `file_size_only` | offline | when the structure-quality code under `esoi/structure/structure_quality/`, its cases or `[balance.score_structure_quality]` changed and the result is wanted | the whole set | none, no model is called | none | none needed | the cases changed, code the arm measures changed since the recorded commit, or it was run on uncommitted code |
| `metric-structure-quality-agreement`, arm `expert_review` | paid | on a decision: before the static scorer's judgement of scoping is trusted for a case it cannot see (whether a split fits its domain) | a stratified sample of 3, then 10, then 30 project reviews | 1 call per project (3, 10 and 30 by stage) | about 6,000 tokens in and 600 out per call, so under 0.20 USD for the 30 on a small tier by the assumptions below; none on a subscription command | Joshua | the cases changed, `expert_review.py` changed since the recorded commit, the model changed, or it was run on uncommitted code |

Estimate assumptions, to be replaced by the recorded token counts after the first stage: the skill is about 4,000 tokens and is sent
with every call of the two skill arms, a reply is about 450 tokens, a judge call reads about 1,100 and writes about 60, and the model
is a small tier priced near 1 USD per million input tokens and 5 per million output tokens (a mid tier costs about three times as much).
Across the three stages that is about 43 case runs per arm, about 580,000 input and 70,000 output tokens in all. Nothing paid has been run.

## In practice

- While working: run the cases for the part you changed (`esoi run <component> --impl live_checker`), and the tests
  (`python -m pytest implementations/python/tests`).
- While improving an arm: an unrecorded run stops at its first failing case and every run is saved in `runs.csv`; fix the arm, then
  rerun only the failing cases with `--failed`. The whole set waits until they pass (`--force "reason"` overrides).
- Known improvements that are not blocked are finished before a metric is run. A paid arm or a run on the large set also waits for
  its other condition (a weekly cadence or a person's approval, written as the stage's `when=`).
- Before committing: `esoi check`.
- After committing a change to measured code or cases: `esoi run --stale --plan` says which recorded results no longer describe the code (the
  changed file and the component that owns it) and why each is or is not re-run. A changed file only informs. Re-record when a decision or
  release depends on the result (`esoi run --stale --for-decision`) or when you name the arm (`--include`), then commit the results log.
  `esoi check` prints one information line with the count of stale results (outside its to-do count); `esoi check --findings` or `--strict` lists each, and `esoi check --for-decision` makes them to dos when a decision or release depends on them. None fails the check.
- This repository runs no continuous integration workflow (an example for other projects: `docs/how-to/run-the-check-in-ci.md`). No
  commit hook and no CI step runs metrics, and expiration is never unless a metric or the project declares one.
- Iterating on a paid arm: with a cassette (`--cassette DIR`) an unchanged prompt is replayed from the file instead of calling the
  model, and `--cassette-only` makes no call at all, so a cassette-only run counts as a free stage: run it before the paid stage
  (`docs/how-to/iterate-on-an-llm-arm-without-repeating-model-calls.md`). Replayed calls are reported apart and are not spend.
- A paid arm: estimate its cost first, run a stratified sample of 3, then 10, then 30 cases with a call budget
  (`esoi run <component> --impl <name> --sample 3 --max-calls 9 --record`), and have Joshua approve the spend before the run.
  It needs `ESOI_MODEL_COMMAND` (a command that reads a prompt on standard input and prints a reply), and `ESOI_MODEL` and
  `ESOI_JUDGE_MODEL` to name the models. `esoi run --stale` skips these arms.

## The skill copy

The cases above prove that the sync and the check catch drift and leaks. Whether the committed copy is current against the author's own skill
can only be known where that skill is reachable, so the author runs `esoi skill sync` and `esoi skill check` (with `ESOI_SKILL_SOURCE` and
`ESOI_SKILL_DENYLIST`) after each edit of it, and public continuous integration runs the generic leak scan on the committed copy.

## Speed

The check itself is a metric run on every change, so its run time is part of the structure check's metric: the
`check_the_structure` component includes a case that generates a repository of hundreds of modules and bounds the time the
check takes, cold and with a warm cache.
