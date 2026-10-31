# Search records and items together

Why this exists: [One search for records and items, written once](../explanation/one-search-for-records-and-items.md).

## Build the views

```python
from pathlib import Path

from esoi import config, spec_index, spec_search

index = spec_index.cached(config.load(Path(".")), "spec_index.json")      # or json.load a file `esoi spec index --out` wrote
records = spec_search.views_from_index(index)
notes = spec_search.views_from_items(
    {"runbook": {"name": "Invoice batch runbook", "summary": "Restart the nightly batch.", "keywords": ["invoice"]}},
    kind="note", source="notes")
views = notes + records
```

An item is a dict with optional `name`, `description` or `summary`, `keywords` and `tags`; pass `text_of=` to say what its
search text is. Nothing is copied: a view points at the item's own fields.

## Search

```python
def my_vector_search(text, k):          # optional; return keys best first, or (key, cosine) pairs
    ...

def my_judge(task, lines, limit):       # optional; one line per candidate; return keys, or the reply text {"ids": [...]}
    ...

found = spec_search.search("invoices arrive late", views, judge=my_judge, vector_search=my_vector_search,
                           ranked_kinds=("note", "solution", "problem"), link_kinds=("ideal", "metric", "intent", "implementation"),
                           max_ranked=5, expand=3)
found.ids                # keys, ranked items first, each followed by what it brought
found.linked             # linked key -> the ranked key that brought it
found.route              # sure, nothing, judged, unjudged or lexical
found.calls              # judge calls made
found.no_solution_yet    # key of a top problem or intent no solution serves, else ""
print(spec_search.render(found))
```

A judge that raises or answers unreadably keeps the best candidates (`found.failed_batches` counts it). A vector search that
raises leaves the lexical answer. With no judge the fused candidates are the answer.

## Choose a strategy

| `strategy` | Does | Judge calls |
|---|---|---|
| `gated` (default) | the gate answers clear and empty cases; one call judges the rest | 0 or 1 |
| `judge-all` | the judge sees every candidate in parallel batches of `batch_size` | one per batch |
| `lexical` | the best `lexical_top` lexical matches | 0 |

`search` is the solution `spec-search`; call `search(..., using="lexical-only")` to pick an implementation by name like any
other, and `esoi select` chooses the default by the metric `metric-spec-search`.

## Filter or boost by tag

Give `views_from_index` a `TagTable` (tag -> the problems it mitigates, solution -> its tags), then pass `tags=[...]` to
`search`: `tag_mode="boost"` (default) ranks tagged views higher, `"filter"` keeps only them.

## Measure it on your records

The library's cases use its own records and no stand-ins. Measure your vector search, judge and `Gate` on yours with
labelled requests, following [Choosing by metric](../explanation/choosing-by-metric.md) and [The first stage needs no model](../explanation/first-stage-needs-no-model.md):
first the free offline stage over your records, then the paid arms with their approval.
