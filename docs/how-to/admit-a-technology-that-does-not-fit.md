# Admit a technology that does not fit the structure

Use this when you found a technology (a library, a service, a model, a product) and the records have no obvious place for it.
The reasoning behind the steps is in [Why a new technology needs a decision, not a slot](../explanation/admitting-a-technology.md).

## Decide, in this order

Stop at the first step that fits. Each step changes less of the specification than the one after it.

1. **Is it another way to do what an existing solution does, at the same seat?** Then it is an arm of that solution. Declare it with
   `@implementation("<solution>", "<name>")` against the solution's existing interface and run `esoi records sync`. No specification
   changes. The metric of the solution compares it with the other arms.
2. **Does it do the same job but only a different measure shows its worth, or a different seat?** Measure it where it competes. If the
   solution's metric cannot see what the technology is good at, add a stage or a circumstance to the metric (see
   [measure per circumstance](measure-per-circumstance.md)), and say so in the metric's record. If it only competes with a
   composition of several solutions, measure it one seat up (step 5).
3. **Is it one stage inside a bigger arm?** Then it is its own solution that a composite arm builds on: add the solution (the new
   interface), declare the technology as its first arm, and add a composite arm of the solution above that lists the new solution in
   `uses_solution_ids`. The composite arm is compared with the arms that lack the stage.
4. **Does it do the job of two solutions at once, or half of one?** Merge or split solutions. Do it only when the definitions of best
   differ, or no longer differ (principle 2 in [from-the-skill](../explanation/from-the-skill.md)), and record the reason.
5. **Does it span several solutions and have no seat?** Add the solution above them, if none exists: its arms are the composition of
   the seats below (a composite arm with `uses_solution_ids`) and the technology as a rival with no change below it.
6. **Is there nothing to run yet?** Register it as a rival with no arm. It stays on the leaderboard as `NOT MEASURED`, so what was left
   out is visible.

## The commands

```bash
# a rival with no code yet (a row with an empty filepath; the reason becomes its description)
esoi admit search "BM25 then rerank" --uses rerank --why "orders the top hits by relevance"

# a change to the specification, with its reason, written to the solution's knowledge
esoi admit search --changed "add the solution rerank that search arms may build on" \
    --why "ordering the hits has its own definition of best, precision at the top"

# once the code declares it
esoi records sync        # fills the empty filepath; a row that has code is an arm
esoi check               # the structure still holds
esoi leaderboard         # lists every candidate still with no arm, as NOT MEASURED
esoi select <solution>   # the default does not change when an arm is added
esoi lock                # the lock records the selections that now exist
```

`esoi admit` writes records only: never code, never `selected`. Choosing the new arm is the metric's decision (`esoi select --promote`).

## What a specification change may touch

| Change | Allowed when | Recorded by |
|---|---|---|
| Widen an interface (a method or parameter added with a default) | existing arms keep working, or each is updated in the same commit | `esoi admit <solution> --changed ... --why ...` and the commit |
| Add a solution | a new definition of best exists (steps 3 and 5) | the same, on the solution that uses it |
| Merge two solutions | the definitions of best have become one; keep each old arm as an arm of the merged solution | the same, on the merged solution; the old ids stay in `knowledge` |
| Split a solution | one arm set serves two definitions of best | the same, on each part |
| Reorganize the hierarchy (move a solution under another, add a parent) | the dependency really runs that way in code | the same, on the parent; `esoi check` and the diagram show the edge |
| Replace an interface so existing arms break | never silently: this is a new solution with the old one kept until its arms move | the same, and the old solution's `knowledge` |

A change with no stated reason is not recorded: `esoi admit` refuses an empty `--why`. The line written is
`<date>: <what>. Because <why>.` in the `knowledge` of the solution the change is about, which the template defines as the knowledge
that informs the solution's definition.

## Three worked examples

The test `implementations/python/tests/test_admit.py` walks each through `esoi admit`, `esoi records sync`, `esoi check`, `esoi select`,
`esoi lock` and `esoi leaderboard` over the scaffolded repository.

**A local model server (an arm).** The solution `model-call` has the arm `hosted-api`. A server that runs a model on the same machine
answers the same call. Declare `@implementation("model-call", "local-server")` with its needs (`binary(...)`, `service(...)`) and sync.
Nothing in the specification changes, and `esoi select model-call` still names `hosted-api` until a metric says otherwise.

**A reranker (a new solution, a stage).** It does not replace `search`: it reorders what `search` found. Add the solution `rerank`
with the arm `cross-encoder`, record the change on `search`, and add the composite arm `bm25-then-rerank` of `search` with
`--uses rerank`. Until its code exists the arm shows as `NOT MEASURED`; after `esoi records sync` it is an arm that the metric of
`search` compares with plain `bm25`.

**An end-to-end agent-memory product (one seat up).** It keeps, summarizes and recalls, so it spans `card-store` and `search`. Add the
solution `remember` above them, whose arm `assembled` uses both, and register the product as its rival with no arm yet. Nothing below
changes (the test compares the records of `card-store` and `search` before and after), and the product competes with the assembled
arm on the one metric that scores keeping and recalling together.

When no solution fits and none of the steps above is true, `esoi admit` stops with a message naming the next move: create the
solution (`esoi new solution <id>`) and record why with `--changed`.
