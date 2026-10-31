# Finding the specifications a new use case needs

A project's records grow past one reading. When a new use case or input arrives (a request, a bug, a design question), the
work that follows is only as good as the specifications it finds: the problems it concerns, the ideals that decide what
"better" means, the solutions and metrics already defined. Finding them is the first step of reusing ESOI, so it gets a
structure of its own.

## What this library does, and what it leaves to a system on top

Finding the right few records out of many is a natural-language problem, and a good pipeline has stages:

1. **Narrow cheaply** with words: index the records, score a request against them, keep the top candidates.
2. **Widen by meaning** where words differ: embeddings and a vector search.
3. **Choose finally** with a model that reads one-line descriptions of the candidates, often in parallel batches.
4. **Read in full** only what was chosen.

ESOI does stage 1 and the data model that makes stages 3 and 4 cheap, using the standard library only. The orchestration of
stages 2 and 3 (fusing the lists, a confidence gate, one judging call, links) is general and is in `esoi.spec_search`; see
[One search for records and items](one-search-for-records-and-items.md). The vector store, the embedding and the model call
are AI infrastructure and stay with the system built on ESOI (an agent runner that selects context is one), which injects
them. Putting a vector store here would make every adopter carry one.

## The specification index

`esoi spec index` builds a plain-JSON map of the records. It is generated from the records and never edited, so it cannot
disagree with them.

| Part | Holds |
|---|---|
| entry `id`, `kind`, `intent` | the record's own id (stable across rebuilds), its type, the intent whose folder holds it |
| `title`, `summary` | tier 0 (one line) and tier 1 (a sentence or two), cut from fields every record already has |
| `refs` | the records it links to, and the records that link to it, so a hit's neighbours can come with it |
| `terms` | the words that identify it, weighted by field (id and name 3, summary 2, body 1) |
| `df`, `n`, `digest` | document frequencies for TF-IDF with no corpus pass, the entry count, and a hash that says when a cached copy is stale |

Nothing is added to the template: the index is derived from the fields the five record types already require, so a project
adopts it by running a command. Write records so their names and first sentences say what they are for; that is also what
makes them findable.

## Tiers: read only what the moment needs

| Tier | What | Use |
|---|---|---|
| 0 | `kind id: title` | scan every record; fits in a prompt |
| 1 | plus summary and linked ids | decide which candidates matter |
| 2 | the full record row, read from the records | work from it |

## Commands

```
esoi spec find "a rival beats the default and nobody switches"   # top records, tier-0 lines
esoi spec find "..." -k 5 --expand 2                              # plus up to 2 linked records per hit
esoi spec show prob-winner-not-adopted --tier 2                   # one record, progressively
esoi spec index --out spec_index.json                             # the JSON a consuming system reads
```

In code, `esoi.spec_index.build(config)` returns the index and `find_specs(index, text, k, expand)` is a declared solution
(`spec-index`) with two implementations, so the metric `metric-spec-index-recall` picks between them: field-weighted TF-IDF
(selected) and plain term overlap (the baseline).

## What the metric does not show

Its cases are plain-words requests written against this repository's own records, so it shows that weighting and fields help
over bare overlap and that the scan is cheap; it does not show recall on a stranger's vocabulary. The pipeline above is why
that is acceptable: a miss at stage 1 is what stage 2 is for. A consumer should measure the whole pipeline on its own requests.
