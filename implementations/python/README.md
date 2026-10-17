# esoi: the Python implementation

One example implementation of the tools that apply [ESOI](../../README.md): it checks a repository's structure against
its records, runs and records measurements, ranks alternatives, resolves a selection table, builds a review sheet, and
scans a public repository for private data. Python 3.11 or later; the core has no dependencies.

## Install

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git@<commit>#subdirectory=implementations/python"
pip install "esoi[sheets] @ git+https://github.com/JoshuaMathias/evolvable-structure.git@<commit>#subdirectory=implementations/python"   # with Google Sheets sync
```

From a checkout: `pip install -e implementations/python`.

## Quick start

```bash
esoi init                   # scaffold a small example repository that already passes
esoi check                  # every rule; --strict also rejects results recorded on uncommitted code
esoi run greet_a_person --impl live --record
esoi leaderboard
```

The full walk through is [docs/guides/apply-with-tools.md](../../docs/guides/apply-with-tools.md).

## Modules

| Module | Role |
|---|---|
| `esoi.config` | One `esoi.toml` (or `[tool.esoi]`) per repository |
| `esoi.records`, `esoi.registry`, `esoi.tables` | Loading and checking the five record files |
| `esoi.template`, `esoi.templates` | Reading the intent template from `SKILL.md` and generating the non-code templates |
| `esoi.check`, `esoi.rules` | The rule runner and the built-in rule groups; a plugin interface for your own |
| `esoi.select` | Resolve an implementation from a selection table at run time |
| `esoi.harness`, `esoi.expect`, `esoi.hermetic` | Run an implementation over a component's cases and record it with provenance |
| `esoi.leaderboard` | Rank, call a verdict, mark baselines and ablations |
| `esoi.tracker`, `esoi.sheets` | The review sheet tabs and their two-way sync |
| `esoi.consumer` | Check a repository that builds on a library |
| `esoi.hygiene` | Secret and private-data scan, working tree and history |
| `esoi.scaffold`, `esoi.cli` | `esoi init` and the command |

Reference: [configuration](docs/configuration.md), [evaluation components](docs/evaluation-components.md),
[rules](docs/rules.md).

## Using the selector from your code

```python
from esoi.select import Selector, load_table

selector = Selector(load_table("mylib/selection.py:SELECTION", root))
implementation = selector.resolve("greet", overrides={"greet": "loud"})
```

## Tests

```bash
python -m pytest implementations/python/tests          # from the repository root; offline, no network
```

`tests/test_components.py` runs this repository's own evaluation components, and `tests/test_self.py` checks the
repository against its own structure.
