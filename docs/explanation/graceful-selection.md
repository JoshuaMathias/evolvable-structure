# Declare, call, measure, promote

The graceful way to make a part of a program swappable, measured and improving: state each fact once, where the code is, and
let the tools derive or check the rest. A second copy of a decision, held in step by a check, is upkeep, not structure.
Joshua's ideal is *declared once*, and the author's earlier tools set the bar: one decorator declares a stage and the same
function then runs as a pipeline step, a standalone test, a command and a notebook cell; one call swaps an implementation by
passing its name and records what it ran.

The structure is the one in [choosing by metric](choosing-by-metric.md). The principle it serves is the fourth of the author's
principles: "Humans need only review metrics, not implementations (but they can still add value to implementations)". So the
person reviews the metric and the evidence, and the tools do the switching.

## 1. Declare

```python
from esoi import implementation, solution

@solution("greet-a-person")                      # the interface: its signature is the contract
def greet(name: str) -> str:
    ...                                          # the body is never run

@implementation("greet-a-person", "plain")       # one alternative, beside its code
def plain(name: str) -> str:
    return f"Hello, {name}!"

@implementation("greet-a-person", "loud")
def loud(name: str) -> str:
    return f"HELLO, {name.upper()}!"
```

For a class that lives in another package, register it instead: `register("greet-a-person", "theirs", "otherpkg.mod:Greeter")`
(imported only when chosen). A Protocol class can be the interface too (`@solution` on the class, reached with
`esoi.resolve("greet-a-person")`).

Then let the records follow. `esoi records sync` reads the declarations from the source (it imports nothing) and writes the
rows the records lack: the solution's id, the file, the signature as its parameters and outputs, the docstring as its purpose.
It fills only what the code knows and never touches a cell that has text; what only a person can write (the problem, the ideal,
the metric and their words) stays empty, and `esoi check` names it. Until you sync, `esoi check` reports the gap (rule S30).
To start a whole new solution in one command, `esoi new solution voice-greeting` writes its records, a code skeleton with the
decorators, and an evaluation folder with a scorer and one example case.

## 2. Call

```python
greet("Ada")                                    # runs the selected implementation
greet("Ada", using="loud")                      # this call only, by name
```

Which implementation runs is decided by one cascade; the innermost layer that names one wins.

| Layer | How it is given | Use it for |
|---|---|---|
| per call | `greet(..., using="loud")` | one call |
| context | `with override("greet-a-person", "loud"): ...` | a block, a test, a request |
| environment | `ESOI_SELECT_GREET_A_PERSON=loud` | a process |
| deployment | `[selection]` in `esoi.toml`: `greet-a-person = "loud"` | a deployment |
| project default | the solution's `selected` in the records | everyone else |

The project default is read from the records, so the choice is made once, where the metric decides it; it is never written a
second time in code. An unknown name raises `SelectionError` listing the choices and the layer that supplied the bad name, so a
typo fails loudly. `esoi select greet-a-person` prints what would run and which layer chose it.

A package installed without its records reads `esoi_selection.json` beside its top package instead; `esoi select --snapshot
esoi_selection.json` writes it from the records, with the module of each implementation, so the lazy import still works.

## 3. Measure

```bash
esoi run greet_a_person --impl loud --record
```

An implementation the code declares needs no wrapper file: the harness imports the module the record names and calls the
implementation with each case's `args` as keyword arguments (a `score.py` may define `adapt(implementation, meter)` to say
otherwise). Wrapper files in `impls/` stay for baselines and reference arms, and for anything that needs the call meter. An arm
that meters a deterministic stand-in for a model (it counts the calls a real model would make and spends nothing) declares
`SIMULATED = True`: its runs record model `simulated` and cost 0.0, `esoi run --stale` never treats it as paid, and the
leaderboard compares it on model calls. Free is never inferred from a missing price; the arm says so.

## 4. Promote

```bash
esoi select --promote           # only the solutions a rival clearly beats
```

When a rival beats the selected implementation on the same cases beyond the noise, `esoi select --promote` either switches
the solution's `selected`, the metric's command and the evidence in `selected_by` (the dates of the runs, the commit, the
cases hash, the pass counts), or prints that exact proposal for a person. Which it does is the solution's `promotion` cell:
`automatic` lets the metric decide; empty or anything else asks a person. It never promotes on a row without a `cases_sha`, on
rows of different cases, on a stale result, on a solution that is not an evaluated one, or while a selection table still holds
its own default. `--dry-run` prints without writing.

## The table, underneath

The selection table and `Selector` are the lower layer and keep working:

```python
selector = Selector.from_config(config)          # the table named by `selection`, defaults from the records
selector.resolve("greet", overrides={"greet": "loud"})
```

A table entry no longer needs a `default`. Leave it out and the default is the solution's `selected` in the records, so there
is nothing to keep in step; rule S23 compares only a table that still holds its own default. Names in a table and names
declared in code are one set. Write `[selection]` in `esoi.toml` when the deployment layer is wanted, with `table = "pkg/sel.py:SELECTION"`
inside it for an existing table.

The Python layer is `esoi.runtime`; the records and the rules behind it are `esoi.declarations` (rule S30), `esoi.promote` and
`esoi.select`. Moving an existing project: [migrate-to-intents.md](../guides/migrate-to-intents.md).
