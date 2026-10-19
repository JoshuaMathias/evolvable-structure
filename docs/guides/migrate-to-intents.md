# Migrate a two-level layout to intents

Older ESOI repositories wrote an **overall solution network** (configured as `overall`) and **detailed records** that
named their parents in `overall_solution_ids`, `parent_problem_ids`, `parent_ideal_ids` and `parent_metric_ids`. That
layout still loads and checks. This guide moves it to the intent model, where an intent is a folder and hierarchy is
between intents (see [intents-and-sub-intents.md](../explanation/intents-and-sub-intents.md)). Do it in small commits,
running `esoi check` after each.

## 1. Make the overall network the top intent

1. Pick the folder that will be the top intent (usually the configured structure folder). Move the overall network's
   problems, ideals, solutions, implementations and metrics into it, beside the detailed records, keeping the ids
   unchanged. Ids are unique across the whole tree, so nothing that links to them breaks.
2. Add `intent.csv` there with one row: `intent_id`, `name`, `vision_statement`, and empty `implements` and `opportunity`.
   Write the vision statement in present tense ("The world is ..."; see the [intent template](../templates/intent.md)).
   The overall network's prose can be kept as `network.md`.
3. Check that the intent has a single top solution that everything implemented falls under. If the overall network had
   several overall solutions, either choose the one that encapsulates the rest or write a new one.

## 2. Turn the overall solution's areas into implementations, solutions or sub-intents

Each area of the overall solution, and each detailed solution that named it in `overall_solution_ids`, is one of three
things. Decide by the opportunity test from
[when-to-create-a-sub-intent.md](../explanation/when-to-create-a-sub-intent.md):

| If the part | Then it becomes |
|---|---|
| Is another way of carrying out the top solution | An implementation of it |
| Has a different definition of best from its neighbours that could impact the success of the intent | A separate solution in the same intent |
| Is an implementation of a solution that brings an opportunity not emerging from the parent intent or that solution, and is worth the cost within the timeframe to the next milestone | A sub-intent: a subfolder with its own `intent.csv` |

Reasons that are only risks or uncertainties do not make a sub-intent: record a risk as a disadvantage of the
implementation (or metric), and an uncertainty in the solution's metric. When in doubt, keep the part in the parent
intent; it can become a sub-intent later.

For each sub-intent:

1. Create the subfolder, move its records into it, and add its `intent.csv`.
2. Set `implements` to the full id of the implementation in the parent intent it arises from. If no such implementation
   exists yet, add one to the parent's `implementations.csv` first.
3. Write the `opportunity` in one line.
4. Put the sub-intent's id in the parent implementation's `sub_intent` column, so the link reads both ways.

## 3. Replace `overall_solution_ids` with `uses_solution_ids`

`overall_solution_ids` said a detailed solution sat under an overall area. In the intent model a solution has no parent
solution, and what remains true is a dependency: an implementation builds on another solution's interface. For each
detailed record that had it:

1. If the solution is now in the same intent or sub-intent as its former area, delete the column value; its place in the
   folder says it.
2. If an implementation of the old area actually calls, or depends on, the detailed solution, write the solution's id in
   that implementation's `uses_solution_ids` (`;`-separated if several), wherever the solution is in the tree.
3. Remove the `overall_solution_ids` column when empty everywhere, and drop `overall = ...` from the configuration.

Keep `parent_problem_ids`, `parent_ideal_ids` and `parent_metric_ids` where they still elaborate a problem, an ideal or a
metric into parts; they now resolve anywhere in the tree.

## 4. Check

```bash
esoi check --strict
```

The checks cover: every sub-intent's `implements` resolves to an implementation in its parent intent, that
implementation names the sub-intent back, every sub-intent has an `opportunity`, intent ids and record ids are unique
across the tree, and `uses_solution_ids` resolve. Fix what it names, commit, and add the project to your
[local index](../explanation/local-index.md) if you keep one.
