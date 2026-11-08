# Solution Consideration

**Purpose:** Give each relevant solution its own consideration, with a prompt formed from the records it connects to, for any pass of AI that judges work against it.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../README.md) > Solution Consideration

Part of [How People and Agents Come to Apply ESOI](../README.md)

## Solution Consideration (`solution-consideration`)

- Out of scope: Calling a model or judging the matter, which the caller does with one pass per prompt; deciding which solutions a text concerns (Solution Relevance does that); finding records for a request (Spec Search does that).
- Delegates to: solution-relevance, spec-search
- Entry call: `esoi.run("solution-consideration", {'project': '.', 'solution_id': ''})`
- Selected implementation: Network by tiers (`network_tiered`)
- Metric: Deciding records reach the pass
- Implemented by: [`implementations/python/esoi/structure/structure_check/rules/consideration_rules.py`](../../structure/structure_check/rules/consideration_rules.py), [`implementations/python/esoi/understanding/solution_consideration/fan_out.py`](fan_out.py), [`implementations/python/esoi/understanding/solution_consideration/knowledge.py`](knowledge.py), [`implementations/python/esoi/understanding/solution_consideration/network_records.py`](network_records.py), [`implementations/python/esoi/understanding/solution_consideration/solution_prompt.py`](solution_prompt.py), [`implementations/python/evaluation/components/consideration_verdicts/__init__.py`](../../../evaluation/components/consideration_verdicts/__init__.py), [`implementations/python/evaluation/components/consideration_verdicts/ask.py`](../../../evaluation/components/consideration_verdicts/ask.py), [`implementations/python/evaluation/components/consideration_verdicts/cases.json`](../../../evaluation/components/consideration_verdicts/cases.json) and 15 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Network by tiers | `solution-consideration:network_tiered` | The solution's definition, recorded results and selection first; then its metric and cascade, problems, ideals, queued findings, public evidence and implementations; then its parent briefly, its children and dependencies by purpose, interface and selected arm, and its dependents by what they rely on. A solution with children adds how they combine. Sections fill a budget in tier order and a cut is named. Knowledge items are offered beside the prompt as candidates; without a retriever of the caller's own, the reference retriever (knowledge.select) picks those the situation bears on. | [`implementations/python/esoi/understanding/solution_consideration/fan_out.py`](fan_out.py) | selected |
| The solution's record alone | `solution-consideration:definition_only` | BASELINE: the solution's own row and nothing connected to it, cut to the budget. It is what a pass reads when no network forms its prompt. | [`implementations/python/evaluation/components/solution_consideration/impls/definition_only.py`](../../../evaluation/components/solution_consideration/impls/definition_only.py) |  |
| Every knowledge item written in | `solution-consideration:all_knowledge` | BASELINE: the same prompt with every knowledge item of the solution written into it in the no-retriever order, inactive ones labelled. | [`implementations/python/evaluation/components/solution_consideration/impls/all_knowledge.py`](../../../evaluation/components/solution_consideration/impls/all_knowledge.py) |  |
| No knowledge | `solution-consideration:no_knowledge` | BASELINE: the same prompt with no knowledge item at all. | [`implementations/python/evaluation/components/solution_consideration/impls/no_knowledge.py`](../../../evaluation/components/solution_consideration/impls/no_knowledge.py) |  |

## Metrics

- Deciding records reach the pass (`metric-solution-consideration`): leader `network_tiered`, 17 of 17 cases

## Problems

- A solution's own records skipped in a broad pass (`prob-solution-skipped-in-a-broad-pass`): One pass of AI judges a change, a candidate or a finding across many solutions from general knowledge, and the records a solution already holds (a measured result that lost, a finding, its Knowledge) are not in front of it.

## Ideals

- Each solution considered on its own records (`ideal-each-solution-considered`): Every solution a matter concerns receives its own consideration, against its own records, and no level of the hierarchy is skipped.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
