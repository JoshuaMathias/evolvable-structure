# Declare a solution's interface and call it with one function

Use this when a solution should answer one call, `<package>.run(id, input)`, whatever implementation the records select, and when
you want `esoi check --findings` to show which of your ids do not answer yet. The declaration lives next to the code; the call needs
nothing else.

## Declare it

Put `kind`, `entry` and `example` on the `@solution` decorator, not on the Protocol, so they do not become methods every
implementation must carry.

```python
# mylib/seats.py
from typing import List, Protocol, runtime_checkable
from esoi import solution

@solution("card-store", kind="store", entry="search", example="rust release")
@runtime_checkable
class CardStore(Protocol):
    def search(self, query: str) -> List[str]: ...
```

- `kind` says what the call returns: `event` (the output of the entry for the input), `evaluate` (feedback or a score on the
  artifact you pass as input) or `store` (the ready handle when you pass no input, the entry's answer when you do).
- `entry` is the method of the interface the call runs. A function solution is its own entry, and its kind is `event`.
- `example` is an input the entry accepts offline. The check runs it, and your README can show it.

Name the class or function in the solution's `interface_name` cell in `solutions.csv`, so the records and the code agree.

## Call it

Bind one function per package, beside the Assembler that lists the modules declaring your solutions:

```python
# mylib/__init__.py
from esoi.assemble import Assembler
from esoi.entry import runner

run = runner(Assembler("mylib", here, modules=("mylib.seats",), records=checkout_root_or_None))
```

Then:

```pycon
>>> import mylib
>>> store = mylib.run("card-store")            # a store with no input: the ready handle
>>> mylib.run("card-store", "rust release")    # the same solution with an input: its answer
>>> mylib.run("mylib", "what changed?")        # an intent id: its one root solution
```

Pass an interface class to get the ready handle typed as that Protocol, so your editor and type checker know its methods:

```python
store = mylib.run(CardStore)       # a CardStore
```

`environ` defaults to the process environment. Override only what differs: `arms={"card-store": "memory"}`,
`options={"card-store": {"path": "cards.db"}}`, `provided={"card-store": my_store}`, `lock=...`.

A package installed without its records (from a wheel) needs the snapshot: run `esoi select --snapshot mylib/esoi_selection.json`
before you build it, and ship that file inside the package. The snapshot also holds the map from each intent id to its root
solution, so `mylib.run("mylib", ...)` works there too.

## Read the outcomes

`python3 -m esoi.entry` runs every id's example with `environ={}` and no network, and gives each id one outcome:

| Outcome | Meaning | Answers? |
|---|---|---|
| `ok` | a value of the declared kind came back | yes |
| `pending-key` | it named the key it needs (`Pending.reasons` has kind `key`) | yes |
| `pending-install` | it named the package or program to install (kind `install`) | yes |
| `needs-option` | it asks you to pass an option or an object, so no default fills the seat | no |
| `load-error` | an arm cannot be imported | no |
| `live-attempt` | it reached for the network or a program that no declared requirement predicted | no |
| `no-entry` | no interface, kind, entry or example is declared | no |
| `fail` | it raised anything else | no |

A requirement may name a program, for example `binary("claude")`. With no PATH in `environ`, the program is not found, the line is
`pending-install`, and the program is never started.

`--gate` exits 1 unless every id answers. `--json` keeps one row per id with its reasons.

## Turn the checks on

The checks are opt-in and advisory. In `esoi.toml`:

```toml
[rules.S36]    # the overall solution network of the top intent
enabled = true
[rules.S37]    # interfaces, the one line per id, the README example
enabled = true
installed = true   # also build the wheel and run the README example from it in a temporary virtual environment
[rules.S38]    # solution coherence; floors per intent
enabled = true
[rules.S38.floors.mylib]
precision = 0.5
coverage = 0.66
[rules.S39]    # the trend of waivers and floors since a base commit
enabled = true
```

`esoi check` stays exactly as before; it adds a line, `to do: N finding(s)`. `esoi check --findings` lists each finding with
its next action and a count per rule, and exits with the same code as without it. S39 shows, against the base commit, whether the
waiver sets grew or shrank and whether a floor rose or fell; set `ESOI_RATCHET_BASE` or `[rules.S39] base` to choose the base.
