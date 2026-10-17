# When this repository's metrics are run

The filled-in [metric run policy](../docs/templates/metric-run-policy.md) for this repository. The records are in this folder
(`overall/` for the overall network, the other files for the detailed ones); this page is the readable version.

## Problem and ideal

The problem is `prob-metrics-run-at-the-wrong-time` and the ideal is `ideal-timely-affordable-evidence`, both in
`overall/`. The detailed solution is `py-metric-run-policy`; it governs every other detailed Metric through
`governs_metric_ids`, and each of them names it in `run_policy_ids`.

## The decision

| Alternative | Used here | Why |
|---|---|---|
| On every change | yes | Every metric here is offline and takes seconds |
| On a schedule | no | No metric depends on a model or a price |
| On a decision | not needed yet | There is no paid metric; this is what a live arm would use |
| On drift | no | Nothing here drifts with the world |

## The metric runs

| Metric | Arm | Trigger | Stages | Call budget | Cost | Approver | Stale when |
|---|---|---|---|---|---|---|---|
| every detailed metric in `metrics.csv` | offline | every change to the measured code or its cases | the whole set | none, no model is called | none | none needed | the cases changed, the measured code changed since the recorded commit, or it was run on uncommitted code |

## In practice

- While working: run the cases for the part you changed (`esoi run <component> --impl live_checker`), and the tests
  (`python -m pytest implementations/python/tests`).
- Before committing: `esoi check`.
- After committing a change to measured code or cases: `esoi run --stale`, then commit the results log. The strict check
  (`esoi check --strict`) is how anyone confirms that every recorded result is current.
- In continuous integration: the tests, the check and the hygiene scan on every pull request and push, and the strict check on
  the default branch (`.github/workflows/check.yml`).
- If a paid metric is ever added: estimate its cost first, run a stratified sample of 3, then 10, then 30 cases with a call
  budget, and have Joshua approve the spend before the run.

## Speed

The check itself is a metric run on every change, so its run time is part of the structure check's metric: the
`check_the_structure` component includes a case that generates a repository of hundreds of modules and bounds the time the
check takes, cold and with a warm cache.
