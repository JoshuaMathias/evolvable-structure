# ESOI: Evolvable Structure that Optimizes Intent

ESOI is a framework that ensure every aspect of your ideas or code can measurably improve over time, while maintaining "evolvable structure." You declare a solution interface, implement alternatives, run them on metrics, and the esoi library ensures the best implementation is what's used at any given time.

The same records (problems, ideals, solutions, implementations, metrics) work for code, business, and life.

# Quick Start

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git@v0.3.0#subdirectory=implementations/python"
```

```python
from esoi import implementation, solution

@solution("greet-a-person", kind="event", entry="greet", example="Ada")   # the interface
def greet(name: str) -> str: ...

@implementation("greet-a-person", "plain")                                # one implementation, beside its code
def plain(name: str) -> str:
    return f"Hello, {name}!"
```

```bash
esoi run greet_a_person --impl plain --record   # measure each implementation on the same cases
esoi select --promote                           # make the measured leader the default
esoi lock                                       # pin it
```

## One call for any solution or intent

```pycon
>>> import esoi
>>> esoi.run("implementation-selection", "structure-check").name   # which implementation serves a solution now
'rule-script'
>>> esoi.run("structure-check", ".")                                # this folder's structural problems
[]
```

`esoi.run(id, input)` reaches any solution or intent the same way, and `esoi.run(Interface)` returns a typed handle. Your package gets the same function with one line, `run = esoi.runtime.assemble_by_name.entry.runner(<your Assembler>)`: a user picks one of your parts by id, overrides one implementation (`arms=`), changes its parameters (`arm@option=value`) or registers their own, and every other part keeps its measured default. 

## Start here

1. **[What ESOI is](https://github.com/JoshuaMathias/evolvable-structure/wiki/What-ESOI-is)**: The idea in five minutes.
2. **[The ESOI steps](https://github.com/JoshuaMathias/evolvable-structure/wiki/The-ESOI-steps)**: What to do, in order,
   from your purpose to choosing by a measurement.
3. **[Apply ESOI by hand](https://github.com/JoshuaMathias/evolvable-structure/wiki/Apply-ESOI-by-hand)**: A first pass
   in about an hour, with fill-in templates and no tools.
4. **[The order of building with structure](https://github.com/JoshuaMathias/evolvable-structure/wiki/The-order-of-building-with-structure)**: The whole
   sequence from the hierarchy and vision statements to the loop of continual improvement.

The wiki is generated from [docs/](docs/README.md) in this repository, so the same pages are here too.

## Give the principles to an AI agent

The author's `evolvable-structure` skill carries the principles and the steps for Claude Code and similar agents.
[Install the skill](https://github.com/JoshuaMathias/evolvable-structure/wiki/Install-the-skill) as a plugin, a folder
download or with `esoi`.

## Check, measure and select with Python (optional)

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git#subdirectory=implementations/python"
esoi init            # scaffold a small example repository that already passes (its specifications are in esoi/)
esoi check           # run every structural rule
```

The graceful path: declare once where the code is, call, measure, promote.

```python
from esoi import implementation, solution

@solution("greet-a-person")                  # declare: the interface
def greet(name: str) -> str: ...

@implementation("greet-a-person", "plain")   # declare: an alternative, beside its code
def plain(name: str) -> str:
    return f"Hello, {name}!"

greet("Ada")                                 # call: runs the project default (the records' "selected")
greet("Ada", using="plain")                  # or by name for one call; `with override(...)` for a block
```

```bash
esoi records sync                                # the records follow your declaration
esoi run greet_a_person --impl plain --record    # measure it beside the others
esoi select --promote                            # promote the winner of its own metric (or print the proposal)
```

The selection table is the advanced layer underneath, for a project that wants every choice as data.

More in [Apply ESOI with the Python tools](https://github.com/JoshuaMathias/evolvable-structure/wiki/Apply-ESOI-with-the-Python-tools)
[Declare, call, measure, promote](docs/explanation/graceful-selection.md) and [the package's README](implementations/python/README.md). When one solution needs another, see [Assemble the parts of a program by name](docs/how-to/assemble-by-name.md) and [what belongs in the library and what in an application](docs/explanation/what-belongs-where.md). It needs Python 3.11 or later and has no dependencies in
its core; Google Sheets sync is an optional extra (`esoi[sheets]`).

## What is in this repository

| Folder | What it holds |
|---|---|
| [`docs/`](docs/README.md) | The main feature: explanation, guides and templates, all non-code. The wiki is generated from it |
| [`skill/`](skill/) | The author's `evolvable-structure` skill as a self-contained folder and Claude Code plugin, generated from his own skill |
| [`implementations/python/`](implementations/python/) | The `esoi` package and command: checks, measuring, a leaderboard, a review tracker. One example implementation |
| [`examples/`](examples/) | Repositories that adopted ESOI, as short testimonials |
| [`esoi/`](esoi/) | ESOI applied to this repository: its top intent and its records |
| [Records beside the code](docs/reference/records-beside-code.md) | The standard for keeping each solution's records in the folder that holds its code, with a generated README in each |

## Contributing and licence

How to propose a change: [CONTRIBUTING.md](CONTRIBUTING.md). Edit pages in `docs/`, not on the wiki: the wiki is regenerated on
every push. Apache-2.0, see [LICENSE](LICENSE).
