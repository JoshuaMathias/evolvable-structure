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

```python
from esoi import implementation, solution

@solution("greet-a-person")                  # declare once, where the code is
def greet(name: str) -> str: ...

@implementation("greet-a-person", "plain")
def plain(name: str) -> str:
    return f"Hello, {name}!"

greet("Ada")                                 # call: the project default, from the records
greet("Ada", using="plain")                  # or by name for one call
```

```bash
esoi init                   # scaffold a small example repository that already passes
esoi check                  # every rule; --strict also rejects results recorded on uncommitted code
esoi records sync           # the records follow what the code declares
esoi run greet_a_person --impl plain --record   # measure
esoi leaderboard
esoi select --promote       # promote the winner of the solution's own metric
```

The full walk through is [docs/how-to/apply-with-tools.md](../../docs/how-to/apply-with-tools.md).

## Modules

| Module | Role |
|---|---|
| `esoi.structure.intent_registry.config` | One `esoi.toml` (or `[tool.esoi]`) per repository |
| `esoi.structure.intent_registry.records`, `esoi.structure.intent_registry.registry`, `esoi.structure.intent_registry.tables` | Loading and checking the five record files |
| `esoi.structure.intent_registry.template_sync.template`, `esoi.structure.intent_registry.template_sync.templates` | Reading the intent template from `SKILL.md` and generating the non-code templates |
| `esoi.structure.structure_check.check`, `esoi.structure.structure_check.rules` | The rule runner and the built-in rule groups; a plugin interface for your own |
| `esoi.runtime.implementation_selection.declare` | Declare solutions and alternatives in code (`@solution`, `@implementation`, `register`) and run the selected one: per call, context, environment, deployment, then the records' default |
| `esoi.runtime.implementation_selection.selection_registry` | What the code declares: the registry of solutions and implementations by scope, `SelectionError`, add and forget |
| `esoi.runtime.implementation_selection.selection_cascade` | The selection cascade: which implementation a call would run, fetched when chosen, and the selection snapshot |
| `esoi.runtime.assemble_by_name.assemble` | Depend on other solutions by name: validated names, safe loading, needs from typed constructor parameters checked against `uses_solution_ids`, build in dependency order, fail at startup on a cycle or an unmet need ([guide](../../docs/how-to/assemble-by-name.md)) |
| `esoi.optimization.keep_metric_record.spec_slice`, `esoi.optimization.keep_metric_record.metric_meter`, `esoi.optimization.keep_metric_record.metric_results`, `esoi.optimization.keep_metric_record.iteration` | Keep a metric's value before and after a piece of work: the slice of the specification a request serves, bounded readings by a recorded row or an offline arm that cannot spend money, measured and recorded rows that never overwrite each other, and `MetricIteration` to wire them |
| `esoi.optimization.leaderboard.circumstances`, `esoi.runtime.implementation_selection.variants` | See a difference by circumstance: conditions on cases and on the run, `name@key=value` variants, derived slice rows and a per-case log; a slice verdict is a proposal, nothing is selected by it ([guide](../../docs/how-to/measure-per-circumstance.md)) |
| `esoi.structure.intent_registry.template_sync.versioning` | The stamp of the skill and template the library follows, the template version, and recording it in a repository (`esoi version`, rule S34) |
| `esoi.runtime.implementation_selection.select` | The selection table and `Selector`, the lower layer; defaults may come from the records |
| `esoi.structure.intent_registry.specify_from_code.declarations`, `esoi.structure.intent_registry.specify_from_code.newsolution` | Read the declarations from the source, sync the records, start a new solution |
| `esoi.optimization.promote_the_winner.promote` | Switch the selected implementation to the winner of the solution's own metric, or propose it |
| `esoi.understanding.readable_records.readme` | The README of each intent folder, generated from its records |
| `esoi.understanding.readable_records.readme_view` | Shared facts and text helpers of the generated READMEs |
| `esoi.understanding.readable_records.readme_intent_page` | The README of an intent folder in each layout |
| `esoi.understanding.readable_records.readme_folder_page` | The README of a folder beside code: implemented-by listing and arm pages |
| `esoi.optimization.measurement_harness.run_component` (with `case_loading`, `arm_loading`, `call_meter`, `record_result`, `record_slices` and the other one-job modules beside it), `esoi.optimization.measurement_harness.expect`, `esoi.optimization.measurement_harness.hermetic` | Run an implementation over a component's cases and record it with provenance |
| `esoi.optimization.leaderboard` (`ranking`, `rival_decisions`, `verdict_labels`, `board_report`, `cascade_stages`, `stage_standings`, `cascade_report`) | Rank, call a verdict, mark baselines and ablations, run the cascade |
| `esoi.understanding.review_tracker.tracker`, `esoi.understanding.review_tracker.sheets` | The review sheet tabs and their two-way sync |
| `esoi.runtime.consumer_check.consumer` | Check a repository that builds on a library |
| `esoi.structure.structure_check.hygiene` | Secret and private-data scan, working tree and history |
| `esoi.understanding.the_standard.skill_distribution.skill` | Generate, check and install the public copy of the author's skill |
| `esoi.understanding.the_standard.scaffold`, `esoi.__main__`, the `commands` module of each container | `esoi init` and the command |

Reference: [configuration](docs/configuration.md), [evaluation components](docs/evaluation-components.md),
[rules](docs/rules.md).

## Using the table from your code (the advanced layer)

```python
from esoi.runtime.implementation_selection.select import Selector

selector = Selector.from_config(config)      # the table `selection` names; an entry without a "default" takes the records' `selected`
implementation = selector.resolve("greet", overrides={"greet": "loud"})
```

The decorators above and this table are one set of names; see [Declare, call, measure, promote](../../docs/explanation/graceful-selection.md).

## Tests

```bash
python -m pytest implementations/python/tests          # from the repository root; offline, no network
```

`tests/test_components.py` runs this repository's own evaluation components, and `tests/test_self.py` checks the
repository against its own structure.
