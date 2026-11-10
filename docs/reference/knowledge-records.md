# Knowledge records

One row per piece of knowledge a solution's definition or implementations rest on, in `knowledge.csv` in a records folder beside
`problems.csv`. A row may serve several solutions; a solution's `knowledge` cell becomes the list of its rows
(`knowledge.csv: k-cards-1;k-cards-2`).

## Template

| Field | What to write |
|---|---|
| `knowledge_id` | a stable id, `k-<solution id>-<n>` by default |
| `claim` | one sentence |
| `kind` | assumption, best guess, evidence, theory, perspective or lesson |
| `source` | `result:<component>/<arm>@<date>`, `url:<address> grade <A-D>`, `person:<who>, <date>: "<their words>"`, `mistake:<record id>`, or free text (the weakest) |
| `solution_ids` | the solutions it informs, `;`-separated |
| `status` | active, superseded, contradicted or expired |
| `status_by` | what superseded or contradicted it |
| `recorded` | the date it was recorded |
| `expiration` | the date it must be re-confirmed by (optional) |
| `investigation_id` | the investigation that found it, a row of `investigations.csv` (optional; [knowledge search standard](knowledge-search-standard.md)) |

A repository that lists its record files in a component's `path` (rule S1) and excludes them from `code_paths` (so editing a record
does not make a result stale) lists `**/knowledge.csv` the same way.

## Commands

```bash
esoi knowledge add --solution cards-from-files --kind lesson --claim "A card per file is an index, not a card set." --source "mistake:M-12"
esoi knowledge list --solution cards-from-files
esoi knowledge migrate            # dry run: the items each free-text Knowledge cell holds
esoi knowledge migrate --apply    # write the rows and leave each cell as their ids
esoi knowledge cards --solution cards-from-files   # the stable part as a managed card and each item as a card, as JSON
```

A free-text cell is read as items until it is migrated: one per `[kind] claim (source: ...)` line, else one per sentence.

## In a prompt

`esoi spec prompt` and `esoi consider` take `--knowledge`:

- `candidates` (the default): the prompt is the solution's stable part, and its items come back beside it (`knowledge`, and
  `knowledge_inactive` for superseded, contradicted and expired ones) for the caller's own retrieval to choose from for the request.
- `ranked`: the fallback with no retriever, every item written in, ordered by status, the strength of its source and recency, the
  inactive ones labelled.
- `none`: no knowledge.

`knowledge.select(items, task)` is the reference retriever a repository with none of its own can use. A consumer with a card store
turns each item into a card (`knowledge cards`): the stable part is one managed card whose writer owns its digest, items are cards
tagged `solution:<id>` with their kind and source as fields, and an inactive item is moved aside rather than deleted.

## Rule S61

Each row has a source, a known kind, status and solution; an active row past its expiration is flagged; a row sourced on a result is
flagged when a newer result of the same arm departs from it by a tenth or more. Waive one row by its id.
