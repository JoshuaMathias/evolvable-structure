# ESOI Behaviour Judge

**Purpose:** Grade whether one reply acts by the principles when a pattern match cannot tell, and show how far the grading agrees with people.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../../README.md) > [ESOI Applied to AI Behaviour](../README.md) > ESOI Behaviour Judge

Part of [ESOI Applied to AI Behaviour](../README.md)

## ESOI Behaviour Judge (`esoi-behaviour-judge`)

- Out of scope: Grading general quality, and being the behaviour measure itself.
- Delegates to: esoi-for-ai
- Entry call: `esoi.run("esoi-behaviour-judge", '.')`
- Selected implementation: Model judge on the rubric (`model-judge-on-the-rubric`)
- Metric: Judge agreement
- Implemented by: [`implementations/python/esoi/understanding/esoi_for_ai/behaviour.py`](../behaviour.py), [`implementations/python/esoi/understanding/esoi_for_ai/command_provider.py`](../command_provider.py), [`implementations/python/esoi/understanding/esoi_for_ai/esoi_behaviour_judge/behaviour_judge.py`](behaviour_judge.py), [`implementations/python/esoi/understanding/esoi_for_ai/esoi_behaviour_judge/interface.py`](interface.py), [`implementations/python/esoi/understanding/esoi_for_ai/interface.py`](../interface.py), [`implementations/python/evaluation/components/judge_esoi_behaviour/__init__.py`](../../../../evaluation/components/judge_esoi_behaviour/__init__.py), [`implementations/python/evaluation/components/judge_esoi_behaviour/broken/__init__.py`](../../../../evaluation/components/judge_esoi_behaviour/broken/__init__.py), [`implementations/python/evaluation/components/judge_esoi_behaviour/broken/always_pass.py`](../../../../evaluation/components/judge_esoi_behaviour/broken/always_pass.py) and 24 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Model judge on the rubric | `esoi-behaviour-judge:model-judge-on-the-rubric` | A model grades each reply against the case's expected behaviour and failure mode in words, never seeing the patterns or the recorded replies, with the patterns as a prefilter. | [`implementations/python/esoi/understanding/esoi_for_ai/esoi_behaviour_judge/interface.py`](interface.py) | selected |
| Regex checks only | `esoi-behaviour-judge:regex-checks-only` | Patterns that every reply must match and that none may match. | [`implementations/python/evaluation/components/judge_esoi_behaviour/impls/regex_only.py`](../../../../evaluation/components/judge_esoi_behaviour/impls/regex_only.py) |  |
| Human review of every reply | `esoi-behaviour-judge:human-review-of-every-reply` | A person reads and marks every reply. | no code yet |  |

## Metrics

- Judge agreement (`metric-esoi-judge-agreement`): leader `regex_only`, 100 of 100 cases

## Problems

- Behaviour verdicts uncalibrated (`prob-behaviour-verdicts-uncalibrated`): A model that grades whether a reply acts by the principles can disagree with the people whose intent the principles express, can favour its own phrasing when it wrote the reply, and can pass a reply that uses the right words while doing the opposite.

## Ideals

- Calibrated judging (`ideal-calibrated-judging`): A judge's verdicts agree with the human verdicts they stand in for, and where they disagree is known.

## Where to go next

- Up: [implementations/python/esoi/understanding/esoi_for_ai](../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
