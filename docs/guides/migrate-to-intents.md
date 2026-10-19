# Migrate a two-level layout to intents

Older ESOI repositories wrote an **overall solution network** (configured as `overall`) and **detailed records** that
named their parents in `overall_solution_ids`, `parent_problem_ids`, `parent_ideal_ids` and `parent_metric_ids`. That
layout still loads and checks. This guide moves it to the intent model, where hierarchy is between intents and a
repository records an intent as a folder (the selected implementation of the `intent-registry` solution; see [intents-and-sub-intents.md](../explanation/intents-and-sub-intents.md)). Do it in small commits,
running `esoi check` after each.

## 1. Make the overall network the top intent

1. Pick the folder that will be the top intent (the configured structure folder, `esoi/` by default). Move the overall network's
   problems, ideals, solutions, implementations and metrics into it, beside the detailed records, keeping the ids
   unchanged. Ids are unique across the whole tree, so nothing that links to them breaks.
2. Add `intent.csv` there with one row: `intent_id`, `name`, `vision_statement`, and empty `implements` and `opportunity`.
   The top intent's name and vision statement are the project's purpose, why the project exists, in its own words
   (present tense, "The world is ..."; see the [intent template](../templates/intent.md)). Do not copy them from the
   overall network when that network was written about the structure ("the structure that ..."): the evolvable structure
   the project applies is a solution inside the top intent, not the top intent. The overall network's ideals are a place
   to look for the purpose, not to copy. The network's prose can be kept as `network.md`.
3. Check that the intent has a single top solution that everything implemented falls under. If the overall network had
   several overall solutions, either choose the one that encapsulates the rest or write a new one. A top solution that
   only describes the structure is a solution inside the intent; the top solution says what the project is for.

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

1. Create the subfolder, named by the sub-intent's `intent_id` (the check requires it), move its records into it, and add
   its `intent.csv`.
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

# Move to the graceful layer

A project that already has a selection table (say `selection = "pkg/core/selection_table.py:SELECTION"`) and a configured
`structure_dir = "docs/structure"` needs no change to keep working: the table, `Selector` and every configured folder behave as
before. These steps are what to do to gain the graceful layer, in small commits, running `esoi check` after each. Install the
new version first (`pip install -U` with the same command as before).

1. **The specifications folder (optional).** New projects get `esoi/`. To follow, `git mv docs/structure esoi`, set
   `structure_dir = "esoi"` (or delete the line, `esoi` is the default), change the path glob of the component that owns the
   folder in `components.csv` (`docs/structure/**` becomes `esoi/**`), and change any `docs/structure/...` path in your own
   configuration (a `[sheets.tabs]` csv, for example). Leaving it as it is works.
2. **Write the project default once.** Delete the `"default": "..."` key from each entry of the selection table. The default is
   now the solution's `selected` in `solutions.csv`, rule S23 has nothing to compare for that entry (it still compares an entry
   that keeps its `default`, so you can move one entry at a time), and `esoi select --promote` can change it. Where your code builds a
   `Selector` itself, build it with `Selector.from_config(config)`, or `Selector(table, defaults)` with `defaults` from
   `esoi.select.records_defaults(config)`. A package that is installed without the records cannot read them: keep the `default`
   in the table (S23 keeps checking it), or write `esoi select --snapshot esoi_selection.json`, ship that file beside the top
   package and pass `esoi.select.snapshot_defaults(path)` as `defaults`.
3. **Declare alternatives where they are (optional).** Put `from esoi import implementation, solution` in the module, `@solution("id")` on
   the interface function and `@implementation("id", "name")` on each alternative (or `register` for a class of another
   package), run `esoi records sync` to write the rows, and fill the text it leaves empty. Table names and declared names are
   one set. An evaluation wrapper `impls/<name>.py` is then needed only for a baseline or reference arm: delete the others and
   point the metric's command at the declared name (`esoi run <component> --impl <name>`).
4. **Deployment choices.** If the deployment layer is wanted, turn `selection = "..."` into a table, after the top-level keys:
   `[selection]`, then `table = "pkg/core/selection_table.py:SELECTION"` and one line `solution-id = "name"` per choice. A
   string and a table cannot both be written.
5. **Offline stand-ins.** An arm that counts the calls of a deterministic stand-in for a model gets `SIMULATED = True` at the top
   of its module. Re-record it (`esoi run --stale`): it records model `simulated` and cost 0.0, is no longer skipped as paid, and
   is compared on calls.
6. **Promotion.** Put `automatic` in a `promotion` column of `solutions.csv` (add the column) for each solution whose policy lets
   the metric decide; leave it empty to review each proposal printed by `esoi select --promote`.
7. **Generated READMEs.** Run `esoi check --write-docs` once and commit the `README.md` it writes in each intent folder (rule S8
   keeps them current). A hand-kept summary of the records beside them can go; your own prose about the network stays.
8. **Check.** `esoi check --strict`.
