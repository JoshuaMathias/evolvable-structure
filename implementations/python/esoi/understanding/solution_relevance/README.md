# Solution Relevance

**Purpose:** Name, for any change, candidate or request, the solutions that need their own consideration, so none is skipped.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../README.md) > Solution Relevance

Part of [How People and Agents Come to Apply ESOI](../README.md)

## Solution Relevance (`solution-relevance`)

- Out of scope: Assembling the prompt for each solution (Solution Consideration does that); ranking records rather than solutions (Spec Search does that); deciding what kind of answer a request wants.
- Delegates to: spec-search
- Entry call: `esoi.run("solution-relevance", ...)`
- Selected implementation: Lexical index (`lexical_index`)
- Metric: Relevant solutions named, recall first
- Implemented by: [`implementations/python/esoi/understanding/solution_relevance/relevance.py`](relevance.py), [`implementations/python/esoi/understanding/solution_relevance/relevance_cases.py`](relevance_cases.py), [`implementations/python/evaluation/components/solution_relevance/__init__.py`](../../../evaluation/components/solution_relevance/__init__.py), [`implementations/python/evaluation/components/solution_relevance/build_cases.py`](../../../evaluation/components/solution_relevance/build_cases.py), [`implementations/python/evaluation/components/solution_relevance/cases.json`](../../../evaluation/components/solution_relevance/cases.json), [`implementations/python/evaluation/components/solution_relevance/hand_cases.json`](../../../evaluation/components/solution_relevance/hand_cases.json), [`implementations/python/evaluation/components/solution_relevance/impls/__init__.py`](../../../evaluation/components/solution_relevance/impls/__init__.py), [`implementations/python/evaluation/components/solution_relevance/impls/index_with_links.py`](../../../evaluation/components/solution_relevance/impls/index_with_links.py) and 5 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Index with links | `solution-relevance:index_with_links` | The field-weighted lexical hits of the specification index plus the solutions and implementations each hit links to (a linked record scores half of the hit that brought it), summed per solution, keeping those near the best. | [`implementations/python/esoi/understanding/solution_relevance/relevance.py`](relevance.py) |  |
| Lexical index | `solution-relevance:lexical_index` | BASELINE: the field-weighted lexical hits of the specification index, each carried to the solution it belongs to. | [`implementations/python/esoi/understanding/solution_relevance/relevance.py`](relevance.py) | selected |
| Cheap model over every solution | `solution-relevance:model_classifier` | PAID: a cheap model reads every solution's one-line summary and the matter, and names the solutions it concerns (the prompt and the reading of the reply are relevance.classification_prompt and relevance.parse_ids; the caller supplies the model). | [`implementations/python/evaluation/components/solution_relevance/impls/model_classifier.py`](../../../evaluation/components/solution_relevance/impls/model_classifier.py) |  |
| Lexical candidates, then a cheap model | `solution-relevance:lexical_then_model` | PAID: the lexical arm's wider candidate list, then a cheap model chooses among those candidates only. | [`implementations/python/evaluation/components/solution_relevance/impls/lexical_then_model.py`](../../../evaluation/components/solution_relevance/impls/lexical_then_model.py) |  |

## Metrics

- Relevant solutions named, recall first (`metric-solution-relevance`): leader `lexical_index`, 26 of 86 cases

## Problems

- The solutions a matter concerns are not named (`prob-relevant-solutions-not-named`): A change, an outside candidate, a request or a bug report concerns some of a project's solutions, and no step of the work names which.

## Ideals

- No relevant solution skipped (`ideal-no-solution-skipped`): Every solution a matter concerns is named for its own consideration, with few that it does not concern.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
