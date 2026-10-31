# Use public evidence beside your own results

Why this exists: [Judge public evidence like a scientist](../explanation/judge-public-evidence-like-a-scientist.md). No model is
called and nothing here costs money.

## 1. Record the evidence

Keep one CSV row per reported number in `esoi/evidence.csv` (or name another file with `[evidence] file = "..."` in
`esoi.toml`). The columns are fixed:

```
evidence_id,candidate,dimension,measure,value,unit,better,comparator,source_url,source_kind,run_by_independent,method_disclosed,n,benchmark_status,date_published,date_checked,confounds,note
```

| Column | Allowed values |
|---|---|
| `dimension` | `quality`, `token_efficiency`, `speed`, `cost`, `reliability`, `safety`, `maintenance` |
| `better` | `higher`, `lower` |
| `source_kind` | `independent_benchmark`, `replication`, `peer_reviewed`, `vendor_reported`, `maintainer_reported`, `community_report`, `own_run` |
| `run_by_independent` | `yes`, `no`, `unknown` (did someone with no stake run it) |
| `method_disclosed` | `yes`, `partial`, `no` |
| `benchmark_status` | `live`, `saturated`, `archived`, `contamination_risk`, `unknown` |
| `confounds` | what else differed, separated by `;` (a different harness, prompt or tool set) |

`measure` names what was measured (`pass_rate`, `latency_p50`); `comparator` names the benchmark or setting it was measured on
(leave it empty when there is none). Dates are `2026-10-31`. `n` is the number of cases or runs, empty when unstated. Every
column except `comparator`, `n`, `date_published`, `confounds` and `note` must be filled; write `unknown` where a column allows it.

```
E1,fast-retriever,quality,pass_rate,0.71,fraction,higher,bench-1,https://example.org/a,independent_benchmark,yes,yes,500,live,2026-09-01,2026-10-30,,
E2,fast-retriever,quality,pass_rate,72,percent,higher,bench-1,https://example.org/b,replication,yes,partial,200,live,2026-10-02,2026-10-30,,
E3,fast-retriever,speed,latency_p50,0.4,s,lower,,https://example.org/c,vendor_reported,no,partial,,unknown,2026-10-20,2026-10-30,,
```

A malformed file is refused with every problem named by line and column. Nothing is dropped silently.

## 2. Grade and rank

```
esoi evidence list
esoi evidence grade
esoi evidence rank --weights quality=2,speed=1,cost=1
```

```python
from esoi import evidence

rows = evidence.load(Path("esoi/evidence.csv"))
got = evidence.estimates(rows)                       # {(candidate, dimension): Estimate}
est = got[("fast-retriever", "quality")]
print(est.grade, est.flags, est.needs_own_run, est.settle)

ranking = evidence.rank(rows, {"quality": 2, "speed": 1})
for place in ranking.dimensions["quality"].ordered:
    print(place.rank, place.candidate, place.estimate.grade, place.reason)

ours = {"fast-retriever": 0.62, "plain-retriever": 0.66}          # our own recorded scores
check = ranking.agrees_with_results(ours, dimension="quality")
print(check.verdict, *check.lines, sep="\n")                      # agree, conflict, mixed or insufficient
```

A conflict is information, not an error: our cases differ from the benchmark's or the public number does not hold for us. Our
own result still decides the selection.

## The grade, in short

Each row earns points (source kind, independence, method disclosed, sample size, benchmark status, age, named confounds).
The best row gives a letter; then the letter is capped (one source: B at most; no independent source: C; vendor-side only: D),
raised one letter when two independent sources agree and lowered one when sources contradict. `esoi evidence table` prints every
weight with its reason; pass your own `evidence.Params(...)` to change one. Flags: `single_source`, `vendor_only`, `stale`,
`saturated`, `confounded`, `contradicts`, `no_method`, `unit_mismatch`, plus `contamination_risk` and, in a ranking,
`not_comparable`. `needs_own_run` is true below grade C or when `vendor_only`, `contradicts`, `unit_mismatch`, `saturated` or
`confounded` is raised, and `settle` says the one run that would settle it.

Units convert only through `evidence.UNITS` (seconds and milliseconds, percent and fraction, and so on). A unit outside the
table, or two units of different kinds for one measure, is `unit_mismatch`, never converted silently. Different measures or
different comparators are different bases and are never merged.

## 3. Show it in the cascade

`esoi cascade` prints, for each implementation of a solution that has evidence, a block labelled "public evidence for X
(others' measurements, not our result)" with the graded line per dimension. It is never counted as a result row, never enters
the standings and never chooses an implementation.

The mapping from a candidate to an implementation is the smallest honest one: the part of the implementation id after the colon,
or its `name`, equal to the candidate with case, underscores, hyphens and spaces ignored. If the public name differs, say so:

```toml
[evidence.aliases]
"vendor-model-v2" = "plain-retriever"
```

A cascade may name a stage `public`:

```
public [real=no | when=others measured it] > offline [sample=full | real=no | gate=all-pass] > ...
```

It needs `real=no`, its `when=` text is free, it needs no gate, and it holds no results. `esoi cascade` reads it as satisfied for an
implementation when evidence rows exist for it and the best grade is C or better. It never replaces our own first-stage result.
