# Build on another package's defaults and say why you differ

Use this when one package (a *hub*) ships ESOI-informed defaults for its solutions and another package (a *child*) builds on it. A
person who only uses the hub writes one line. The child states only the choices that differ, and each of those says why. The reasoning
is in [Override only what differs, and say why](../explanation/override-only-what-differs.md); the base mechanics are in
[Assemble the parts of a program by name](assemble-by-name.md).

## One line for an end user

```python
system = hub.assemble_defaults()      # every solution the hub declares, each built from its default arm
```

`system.pending` lists, with one line each, anything that cannot be built from defaults alone (an option to pass, an object to
provide). `system.explain("store")` says which layer chose each arm.

## A child with a parent

```python
hub = Assembler("hub", hub_dir, modules=("hub.solutions", "hub.arms"))
child = Assembler("child", child_dir, modules=("child.arms",), parent=hub)
system = child.assemble_defaults()    # the hub's solutions with the child's defaults laid over them
```

The child declares only the arms it adds (`@implementation("store", "cached")` in its own module) and records its own `selected` for a
solution it changes. Everything else is inherited. A parent may have a parent.

## The order of the layers

Highest priority first; the first layer that names an arm and applies wins.

| # | Layer | Who sets it |
|---|---|---|
| 1 | explicit name (`choice(sid, name)`, `AssemblyConfig.names`) | the caller of one call |
| 2 | consumer selections (`AssemblyConfig.selections`) | the program that assembles |
| 3 | selection environ (`AssemblyConfig.selection_environ`, only `ESOI_SELECT_<CHILD SCOPE>_<SOLUTION>`) | a deployment |
| 4 | the child's default (its own `selected`, in its records or snapshot) | the child's records |
| 5 | the parent's default, then the parent's parent's | the hub's records |

Layers 1 to 3 are the caller's and may name any arm that exists for the solution in the child or a parent (`names(sid)` lists them).
Layer 4 may only choose among those names too. A name that no scope lists raises, naming the scope, the layer and the choices; a typo
never falls through. A parent never sees the child's arms: `hub.choice(...)` is unchanged by the child. With no `parent` the order is
the one in the assemble guide.

## Say why a choice differs

A choice of an arm other than the parent's default is an override. Give `reasons` for a selection:

```python
config = AssemblyConfig(
    selections={"store": "cached"},
    reasons={"store": ["slow-disk-problem", "unconfirmed: waiting for a measurement."]},   # ids of the child's own records
)
system = child.assemble_defaults(config)
system.choice("store").reasons       # ("slow-disk-problem", "unconfirmed: waiting for a measurement.")
```

A reason is the id of one of the child's own problem, ideal or metric records, or `unconfirmed: <text>`. The marker is recorded and
shown but does not count as justification. For the child's own default (layer 4), put the ids in `overrides.csv` in its records
(columns `solution_id`, `reason_ids`, ids joined by `;`); `Assembler` reads it with the records and shows the ids in `explain`.
`child.overrides(config)` returns every solution that differs from a parent, with `justified` true when a record id is cited.

## One explain across the hierarchy

```python
print(child.explain("store", config=config))
# store: cached (layer: consumer selections)
#   -> consumer selections: cached; reasons: slow-disk-problem, unconfirmed: waiting for a measurement.
#      child default: disk [the packaged snapshot]
#      hub default: memory [the packaged snapshot]
#   overrides the parent default memory
# ("child default" and "hub default" are written with the scopes' names, such as "child default")
```

`Explanation.layers` has one `Layer` per entry (value, source, kind, scope, condition, reasons, why it was skipped); `.winner` is the
layer `choice` returns. `system.explain(sid)` does the same for a built assembly.

## Choose by circumstance

A layer value may be `name@key=value,...`, or a list of them for selections and the explicit name. In an Assembler the parameters are
conditions on `AssemblyConfig.circumstances`, the caller's mapping (keys and values as in `esoi.variants`, compared as
`esoi.circumstances` compares: numbers as numbers, text ignoring case). The first entry whose conditions all hold wins; one that does
not hold stays in `explain`, marked skipped, and a key the caller did not give never matches.

```python
config = AssemblyConfig(selections={"store": ["cached@size=large", "memory"]}, circumstances={"size": "large"})
child.choice("store", config=config)     # cached; Choice.when == "size=large"
```

The condition is not passed to the arm: use `options` for constructor arguments. (`esoi.runtime.choose` still treats `name@k=v` as
parameters of the arm.) Defaults are not conditional.

## Check that every override says why: rule S35

Add a `[parent]` table to the child's `esoi.toml` and rule S35 compares its `selected` arms with the parent's defaults:

```toml
[parent]
records = "../hub"                  # the parent's records folder (its own esoi.toml), or
# snapshot = "hub/esoi_selection.json"
```

Each solution whose `selected` differs from the parent's default needs, in `overrides.csv`, the id of a problem, ideal or metric of its
own records, or a waiver (`rule` S35, `path` the solution id) whose reason names the pending decision. A reason id that no record has
is reported too. A repository with no `[parent]` table is never checked; `disable = ["S35"]` turns it off.
