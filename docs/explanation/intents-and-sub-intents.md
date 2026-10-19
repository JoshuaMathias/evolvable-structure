# Intents and sub-intents

An **intent** is a container. In the author's words, "An intent is like a folder containing the files of the other five
specification types": problems, solutions, implementations, ideals and metrics. It has a name and a vision statement in
present tense (for example "The world is ..."), from the [intent template](../templates/intent.md). It is not a general
category like "parenting", and not an organization itself, but the container that says why something exists.

## The top intent and its single top solution

Every project, repository, organization or big goal is a top intent. It has a single top solution, and everything
implemented falls under a solution. The top solution's implementations are the ways of carrying it out: some are plain
implementations, and some are big or interesting enough to be intents of their own (sub-intents). A top solution may also
build on solutions in other intents.

## Sub-intents are folders

In a repository, an intent is a folder.

```text
structure/                  the top intent
  intent.csv                its record: name, vision statement
  problems.csv  solutions.csv  implementations.csv  ideals.csv  metrics.csv
  network.md                optional prose view
  review-sheets/            a sub-intent: a folder with its own intent.csv
    intent.csv              its record, plus `implements` and `opportunity`
    solutions.csv ...
```

- The top intent is the configured structure folder.
- A sub-intent is a subfolder of its parent intent's folder that contains an `intent.csv`. Folders without one (a
  generated tracker, for example) are not intents.
- A sub-intent's `intent.csv` has `implements`, the full id of the implementation in the parent intent that it arises
  from, and `opportunity`, the opportunity that justifies it. The top intent leaves both empty.
- The parent's `implementations.csv` names the sub-intent in an optional `sub_intent` column, so the link can be followed
  from either side, and lists in `uses_solution_ids` the solutions, anywhere in the tree, that the implementation builds
  on through their interfaces.
- Ids are unique across the whole tree, so any link column can name a record in another intent.

When to create one is in [when-to-create-a-sub-intent.md](when-to-create-a-sub-intent.md).

## What has no children

Problems, solutions, implementations, ideals and metrics have no direct children, except as a way to elaborate: a
problem can describe areas as sub-problems, an ideal can have sub-ideals, and a metric can have parts (the optional
`parent_problem_ids`, `parent_ideal_ids` and `parent_metric_ids` columns). There is no solution under a solution.
Structure between solutions is a dependency, written as `uses_solution_ids` on the implementation that builds on another
solution's interface.

## Reading the "Start with one at the top" bullet

The quoted bullet says the single top solution "encapsulates sub-solutions for more specific components". In the current
terms, the more specific components are what the top solution's implementations are made of: sub-intents (each with
solutions of its own) and the solutions those implementations build on. The words are the author's; the structure that
carries them is intents.

## The legacy two-level layout

Earlier versions of ESOI described two levels: a short **overall solution network** written first from the owner's intent
(problems, ideals, one overall solution with areas, alternatives and top metrics), and **detailed records** that named the
part of it they served in `parent_problem_ids`, `parent_ideal_ids`, `overall_solution_ids` and `parent_metric_ids`.
Repositories that use `overall` in their configuration still load and check that way. It maps to intents like this:

| Legacy | Intent model |
|---|---|
| The overall network (a folder of records) | The top intent |
| The overall solution and its areas | The top solution; areas become implementations, sub-intents, or separate solutions in the intent |
| A detailed solution with `overall_solution_ids` | A solution of the top intent (same intent) or of a sub-intent (in a subfolder), with `uses_solution_ids` where it builds on another |
| Detailed problems and ideals with `parent_problem_ids` and `parent_ideal_ids` | Unchanged: sub-problems and sub-ideals elaborate a problem or an ideal |
| A top metric fed by `parent_metric_ids` | Unchanged: a metric's part |

A migration, step by step, is in [migrate-to-intents.md](../guides/migrate-to-intents.md).
