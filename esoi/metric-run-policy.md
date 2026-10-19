# When this repository's metrics are run

The filled-in [metric run policy](../docs/templates/metric-run-policy.md) for this repository. The records are in this folder
(and in its sub-intent folder); this page is the readable version.

## Problem and ideal

The problem is `prob-metrics-run-at-the-wrong-time` and the ideal is `ideal-timely-affordable-evidence`. The solution is
`when-metrics-are-run`, whose selected implementation is the continuous integration workflow; it governs every other Metric
through `governs_metric_ids`, and each of them names it in `run_policy_ids`.

## The decision

| Alternative | Used here | Why |
|---|---|---|
| On every change | yes, for every offline arm | Offline arms take seconds |
| On a schedule | no | No recorded metric drifts with a model or a price while only offline arms are recorded |
| On a decision | yes, for the arms that call a model | The ESOI behaviour arms and the model judge cost money, so they run only when a choice depends on them |
| On drift | no | Nothing here drifts with the world |

## The metric runs

| Metric | Arm | Trigger | Stages | Call budget | Cost | Approver | Stale when |
|---|---|---|---|---|---|---|---|
| every other metric in `metrics.csv` | offline | every change to the measured code or its cases | the whole set | none, no model is called | none | none needed | the cases changed, the measured code changed since the recorded commit, or it was run on uncommitted code |
| `metric-skill-copy-agreement` (sync drift and leak detection) | offline | every change to `esoi/skill.py` or its cases; the live freshness check also runs after every edit of the author's skill, where its source and private term list are reachable | the whole set | none, no model is called | none | none needed | the cases changed, `skill.py` changed since the recorded commit, or it was run on uncommitted code |
| `metric-behave-by-esoi`, arms `reference_good` and `reference_bad` (validity) | offline | every change to the cases, `esoi/behaviour.py` or the arms | the whole set | none, no model is called | none | none needed | the cases changed, the measured code changed since the recorded commit, or it was run on uncommitted code |
| `metric-judge-esoi-behaviour`, arm `regex_only` (validity) | offline | every change to its cases, which follow the behaviour cases | the whole set | none, no model is called | none | none needed | as above |
| `metric-behave-by-esoi`, arms `standing_instructions`, `skill_on_request` and `no_skill` | paid | on a decision: choosing between ways of giving an agent the principles, a change to the skill that should be checked, a new model | a stratified sample of 3, then 10, then 30; the whole set only if the 30 is not clear; stop and report after each stage | 3 calls per case for each arm (9, 30 and 90 per arm by stage) | about 1 to 3 USD for all three arms and the judge across the three stages, from the assumptions below; none on a subscription command | Joshua | the cases changed, the skill or `esoi/behaviour.py` changed since the recorded commit, the model changed, or it was run on uncommitted code |
| `metric-judge-esoi-behaviour`, arm `model_judge` | paid | on a decision: before a behaviour score judged by a model is trusted, and when the judge's model changes | a stratified sample of 3, then 10, then 30 labelled replies, then the whole set once a person has filled `human_verdict` for a sample | 1 call per reply (3, 10 and 30 by stage) | included in the estimate above | Joshua | as above, or the labels changed |

Estimate assumptions, to be replaced by the recorded token counts after the first stage: the skill is about 4,000 tokens and is sent
with every call of the two skill arms, a reply is about 450 tokens, a judge call reads about 1,100 and writes about 60, and the model
is a small tier priced near 1 USD per million input tokens and 5 per million output tokens (a mid tier costs about three times as much).
Across the three stages that is about 43 case runs per arm, about 580,000 input and 70,000 output tokens in all. Nothing paid has been run.

## In practice

- While working: run the cases for the part you changed (`esoi run <component> --impl live_checker`), and the tests
  (`python -m pytest implementations/python/tests`).
- Before committing: `esoi check`.
- After committing a change to measured code or cases: `esoi run --stale`, then commit the results log. The strict check
  (`esoi check --strict`) is how anyone confirms that every recorded result is current.
- In continuous integration: the tests, the check and the hygiene scan on every pull request and push, and the strict check on
  the default branch (`.github/workflows/check.yml`).
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
