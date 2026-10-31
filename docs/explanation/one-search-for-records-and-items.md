# One search for records and items, written once

A system that picks the specifications (or any other items, such as notes, cards or documents) a request concerns needs
the same stages every time: score by words, optionally score by meaning, fuse the two lists, decide whether the cheap
stages are enough, ask a model only when they are not, and bring each result's linked records. None of those stages knows
what the product is for. When each product writes them itself, the stages drift from the library's index, are measured in
one place only, and are copied by the next product.

## What is here and what is not

`esoi.spec_search` holds the stages. It holds no embedding, no vector store, no prompt and no model call. The caller injects
the two things that are its own:

| Injected by the caller | Why it stays out |
|---|---|
| `vector_search(text, k)`: view keys best first, or `(key, cosine)` pairs | an embedding model and a store are a dependency every adopter would otherwise carry |
| `judge(task, lines, limit)`: the keys it chose, as a list or as the reply text `{"ids": [...]}` | the prompt and the model are the product's; the library only offers the candidate lines and reads the answer |

Everything else is the library's: the lexical formula (the one `esoi.spec_index.weighted_tfidf` uses), reciprocal rank
fusion, the confidence gate, batching, the rule that a judge which fails keeps the candidates, links and the cue "no solution
yet".

## Why a gate

A model call per request is the costly way to choose. The gate answers from the two searches' agreement: when both rank the
same record first with strong evidence the answer needs no call, when neither finds anything credible the answer is nothing
and needs no call, and only the rest are judged, in one call over the best candidates. The thresholds are a `Gate` you can
change. The defaults were tuned for one product's records and embedding model, so measure them on yours: a cosine of 0.7
means different things for different embedding models.

## One ranking across sources

A `View` is read in place and keeps the key of its source: a record's key is its own id, any other item's is `kind:id`, so
an item can never shadow a record. Items and records compete in one list; the records among them bring their linked records
(`link_kinds` decides which kinds are brought, one of each kind before a second of any).

## "No solution yet"

When the top ranked record is a problem, or an intent, that no solution serves, `Selection.no_solution_yet` names it. It is
the cue to define a solution rather than to look for one.

## Not the same as choosing an implementation

This module finds records. Choosing among implementations by their measured result is `esoi select`, `esoi cascade` and
`esoi.runtime`; circumstance slices and `name@key=value` variants belong to that side (`esoi.circumstances`,
`esoi.variants`). The two meet only in that the strategies here are implementations of the solution `spec-search`, chosen
the same way as any other.

See [Search records and items together](../guides/search-specs-and-items.md) to use it, and
[what belongs where](what-belongs-where.md) for why it is here.
