# Assemble the parts of a program by name

Use `esoi.assemble` when one solution's implementation needs another solution, and you want the two to meet by name instead of by
import. A configuration file, a database row or an environment variable can then say which implementation to use, a missing
or circular need fails when the program starts, and nothing is loaded that nobody vouched for. Why it is built this way is in
[Depend on other solutions by name](../explanation/cross-dependency-by-name.md).

## Declare the seats once

A seat is a Protocol class declared with `@solution`. Importing it runs nothing. Put the seats of a package in one module.

```python
# mylib/seats.py
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
from .seats import Store

@implementation("store", "memory")
class Memory:
    def get(self, key): return key

@implementation("report", "plain")
class Plain:
    def __init__(self, store: Store, prefix: str = ""):   # a parameter typed with a seat IS a need of that seat
        self.store, self.prefix = store, prefix
    def render(self): return self.prefix + self.store.get("k")
```

`Plain` imports the seat (`Store`), never `Memory`. Which store it gets is decided at assembly.

## Assemble at startup

```python
from pathlib import Path
from esoi.assemble import Assembler, AssemblyConfig

parts = Assembler("mylib", Path(__file__).parent, seats_module="mylib.seats", noun="mylib")   # once, in the package

config = AssemblyConfig(seats=("report",), selections={"store": "memory", "report": "plain"},
                        options={"report": {"prefix": "> "}})
system = parts.assemble(config)
system["report"].render()          # "> k": store was built first and handed to report
print(*system.reasons, sep="\n")   # store -> memory (layer: consumer selections, package version ..., config hash ...)
```

- A consumer chooses an arm by name: `AssemblyConfig(selections={"store": "acme-memory"})`, after
  `parts.register("store", "acme-memory", MyStore)`. A name must match `^[a-z0-9][a-z0-9_-]*$` and be one the seat lists
  (`parts.names("store")`); an import path such as `os:system` is rejected before anything is imported.
- A consumer can hand over a ready object: `parts.assemble(config, provided={"store": my_store})`. It must satisfy the seat's
  Protocol.
- Leave a seat out of `selections` and the package default decides: the `selected` cell of the solution's record (or the packaged
  snapshot of an installed copy), which the metric sets.
- The cascade for a seat is: explicit name, the consumer's selections, then the package default (the record's `selected`,
  or the packaged snapshot of an installed copy). A name a layer supplies that is not listed is an error, never a fall-through.
- A cycle or a need with no arm fails at startup and names the chain: `report (plain) needs store: no arm, not provided (chain: report -> store)`.
- The result is frozen. Nothing resolves at call time, so no lock is needed.

## Keep the records in step

`implementations.csv` already has a `uses_solution_ids` column. The needs the code declares are the truth, so write the
column from them and check it in a test:

```python
parts.sync_uses(Path("esoi"))                 # rewrite the column from the constructor parameters
assert parts.uses_problems(Path("esoi")) == []   # needs match the column; no default arm cycles; every need is met
```

`uses_problems` also reports a need on a solution that has no default arm unless it is tagged `consumer-provided` (the
consumer supplies it), and the reverse: a `consumer-provided` solution that has a default arm.

## What the library does not do

It reads no environment: the only environment `esoi` sees is `AssemblyConfig.selection_environ`, a mapping you pass in. It does
not import your application, install anything, or choose the best arm; the metric does that (`esoi select --promote`).
What belongs in `esoi` and what stays in your application is in
[What belongs where](../explanation/what-belongs-where.md).
