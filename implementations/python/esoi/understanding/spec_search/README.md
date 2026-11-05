# Spec Search

**Purpose:** Find the records, standards and product items that a request concerns, cheapest first, each with the records it links to.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../README.md) > Spec Search

Part of [How People and Agents Come to Apply ESOI](../README.md)

## Spec Search (`spec-search`)

- Out of scope: Embeddings, vector stores, prompts and model calls, which the caller supplies; judging what the work is worth.
- Entry call: `esoi.run("spec-search", ...)`
- Selected implementation: Lexical vector gated (`lexical-vector-gated`)
- Metric: Spec search correctness, Specification recall at k
- Implemented by: [`implementations/python/esoi/understanding/spec_search/spec_index.py`](spec_index.py), [`implementations/python/esoi/understanding/spec_search/spec_search.py`](spec_search.py), [`implementations/python/evaluation/components/spec_index/__init__.py`](../../../evaluation/components/spec_index/__init__.py), [`implementations/python/evaluation/components/spec_index/cases.json`](../../../evaluation/components/spec_index/cases.json), [`implementations/python/evaluation/components/spec_index/impls/__init__.py`](../../../evaluation/components/spec_index/impls/__init__.py), [`implementations/python/evaluation/components/spec_index/impls/live.py`](../../../evaluation/components/spec_index/impls/live.py), [`implementations/python/evaluation/components/spec_index/impls/term_overlap.py`](../../../evaluation/components/spec_index/impls/term_overlap.py), [`implementations/python/evaluation/components/spec_index/impls/weighted_tfidf.py`](../../../evaluation/components/spec_index/impls/weighted_tfidf.py) and 12 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Lexical only | `spec-search:lexical-only` | The baseline: the lexical top three, no vector search and no judge. Free and instant; shows what the rest adds. | [`implementations/python/esoi/understanding/spec_search/spec_search.py`](spec_search.py) |  |
| Lexical vector gated | `spec-search:lexical-vector-gated` | Lexical plus vector candidates, fused, then the gate: a clear case and an empty case are answered with no judge call, any other costs one call over the best ``gate.pool`` candidates. The lexical stage is the field-weighted index. ``strategy`` ``judge-all`` and ``lexical`` run the other two stagings with the same arguments. | [`implementations/python/esoi/understanding/spec_search/spec_search.py`](spec_search.py) | selected |
| Field-weighted TF-IDF over the index | `spec-search:weighted-tfidf` | The lexical stage on its own: each entry's terms carry the weight of the heaviest field they appeared in (id and name 3, summary 2, body 1); a query term scores that weight times its inverse document frequency, taken from the index itself; hits can pull in linked records. | [`implementations/python/esoi/understanding/spec_search/spec_index.py`](spec_index.py) |  |
| Plain term overlap | `spec-search:term-overlap` | Count the terms a request shares with a record, every term and field worth the same. | [`implementations/python/esoi/understanding/spec_search/spec_index.py`](spec_index.py) |  |

## Metrics

- Specification recall at k (`metric-spec-index-recall`): leader `weighted_tfidf`, 31 of 35 cases
- Spec search correctness (`metric-spec-search`): leader `gated`, 6 of 6 cases

## Problems

- Specifications not found for new input (`prob-intent-specs-not-found-for-new-input`): A new use case or input arrives, and it is hard for a person or an AI to tell which of a project's problems, ideals, solutions, implementations and metrics apply without reading most of them.
- Specifications hard to search (`prob-spec-search`): A system that finds a repository's records for a request, or finds them together with its own notes or documents, rebuilds the same stages inside its own code: lexical scoring, a semantic search, rank fusion, a confidence gate, one judging call and the way a ranked record brings its links.

## Ideals

- Right specification at the right time (`ideal-right-spec-at-the-right-time`): For any new use case or input, whoever applies a project's specifications works from the few that bear on it, at a small fraction of the cost of reading them all.
- Shared specification search (`ideal-spec-search`): An application that finds specifications for a request writes only what is its own, and every improvement to finding them reaches it without a change on its side.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
