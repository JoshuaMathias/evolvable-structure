# Assemble the parts of a program by name

Use `esoi.assemble` when one solution's implementation needs another solution, and you want the two to meet by name instead of by
import. A configuration file, a database row or an environment variable can then say which implementation to use, a missing
or circular need fails when the program starts, and nothing is loaded that nobody vouched for. Why it is built this way is in
[Depend on other solutions by name](../explanation/cross-dependency-by-name.md).

## Declare the solutions once

A solution is a Protocol class declared with `@solution`. Importing it runs nothing. Put the solutions of a package in one module.

```python
# mylib/solutions.py
from typing import Protocol, runtime_checkable
from esoi import solution

@solution("store")
@runtime_checkable
class Store(Protocol):
    def get(self, key: str) -> str: ...

@solution("report")
@runtime_checkable
class Report(Protocol):
    def render(self) -> str: ...
```

## Write implementations; a typed parameter is a need

```python
# mylib/arms.py
from esoi import implementation
from .solutions import Store

@implementation("store", "memory")
class Memory:
    def get(self, key): return key

@implementation("report", "plain")
class Plain:
    def __init__(self, store: Store, prefix: str = ""):   # a parameter typed with a solution IS a need of that solution
        self.store, self.prefix = store, prefix
    def render(self): return self.prefix + self.store.get("k")
```

`Plain` imports the solution (`Store`), never `Memory`. Which store it gets is decided at assembly.

## Assemble at startup

```python
# mylib/system.py
from pathlib import Path
from esoi.assemble import Assembler, AssemblyConfig

# once, in the package: its scope, its folder, and the modules that declare its solutions and arms
parts = Assembler("mylib", Path(__file__).parent, modules=("mylib.solutions", "mylib.arms"))

config = AssemblyConfig(solutions=("report",), selections={"store": "memory", "report": "plain"},
                        options={"report": {"prefix": "> "}})
system = parts.assemble(config)
assert system["report"].render() == "> k"            # store was built first and handed to report
print(*system.reasons, sep="\n")                     # store -> memory (layer: consumer selections, package version ..., config hash ...)
```

- `modules` are imported by `parts.prepare()` (which `assemble` calls), so the Assembler knows the arms before it checks a name.
  A module of the package that only a record names (an arm with an optional dependency) is not listed: it is imported when that
  arm is chosen.
- A consumer chooses an arm by name: `AssemblyConfig(selections={"store": "acme-memory"})`, after
  `parts.register("store", "acme-memory", MyStore)`. A name matches `^[a-z0-9][a-z0-9_-]*$` and must be one the solution lists
  (`parts.names("store")`). Dots and colons are refused so that a name can never be read as an import path; a dotted model name
  such as `gpt-4.1` is data for `options`, or an arm named `gpt-4-1`.
- A consumer can hand over a ready object: `parts.assemble(config, provided={"store": my_store})`. It must have every method
  and attribute the solution's Protocol names (presence by name, not signatures, with or without `@runtime_checkable`). A
  solution declared without a Protocol class cannot be checked, so providing for it is an error.
- Leave a solution out of `selections` and the package default decides: the `selected` cell of the solution's record (from the
  `records` folder you give the Assembler, or the `esoi_selection.json` beside the package when it is installed).
- The cascade is: explicit name, the consumer's `selections`, `selection_environ`, then the package default. A name a layer
  supplies that is not listed is an error, never a fall-through. `selection_environ` is a mapping you pass in; only
  `ESOI_SELECT_<SCOPE>_<SOLUTION_ID>` is read from it.
- A cycle or a need with no arm fails at startup and names the chain: `report (plain) needs store: no arm, not provided (chain: report -> store)`.
- The result is frozen: `system.choice("report")` and `system.implementation("report")` are what was chosen and loaded when
  `assemble` ran. `parts.choice` and `parts.resolve` look up when called.

## What an Assembler refuses

It is strict where plain `esoi.runtime` is permissive. It never searches a parent folder for an `esoi.toml`, never runs a
selection table, never reads the deployment table, `override()` or the process environment, never changes `sys.path`, and
raises where the runtime falls through. A module is imported only if a record of the package names it, it starts with the scope,
and its file lies inside the package folder. `parts.register` refuses the package's own arm names; so does a later
`runtime.register(..., replace=True)` over one, when the arm is loaded. Register through `parts`.

## Keep the records in step

`implementations.csv` already has a `uses_solution_ids` column. The needs the code declares are the truth, so write the
column from them and check it in a test:

```python
from pathlib import Path
parts.sync_uses(Path("esoi"))                 # rewrite the column from the constructor parameters
assert parts.uses_problems(Path("esoi")) == []   # needs match the column; no default arm cycles; every need is met
```

`uses_problems` also reports a need on a solution that has no default arm unless it is tagged `consumer-provided` (the
consumer supplies it), and the reverse: a `consumer-provided` solution that has a default arm. An arm that cannot be
imported (an optional extra is not installed) is reported as a finding, and `sync_uses` leaves its row alone and returns the
finding.

## What the library does not do

It reads no environment: the only environment `esoi` sees is `AssemblyConfig.selection_environ`, a mapping you pass in. It does
not import your application, install anything, or choose the best arm; the metric does that (`esoi select --promote`).
What belongs in `esoi` and what stays in your application is in
[What belongs where](../explanation/what-belongs-where.md).

## Build on another package's defaults

A package that builds on another gives `Assembler(..., parent=other)`; the cascade then ends in the child's default and the parent's, a
choice that differs can carry `reasons`, and `explain` shows every layer. See
[Build on another package's defaults and say why you differ](hierarchical-defaults.md).
