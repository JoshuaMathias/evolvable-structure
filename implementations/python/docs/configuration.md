# Configuration reference

One file per repository: `esoi.toml` (top-level keys) or the `[tool.esoi]` table of `pyproject.toml`. Paths are relative to
the folder that holds it. Every key is optional. An unknown key is an error, so a typo does not pass silently.

```toml
package = "mylib"                      # the importable package the module rules look at ("" turns them off)
package_dir = "src/mylib"              # where it lives (default: the package name)
python_path = ["src"]                  # folders put on sys.path when evaluations run
cache = true                           # remember per-module facts in .esoi_cache/ (gitignored); false turns it off
layers = ["core", "adapters", ["cli", "tools"]]   # inner to outer; a nested list shares one rank
other_layers = ["docs", "evaluation", "examples", "scripts", "tests", "vendor", "prompts"]   # non-code areas a component may name
max_lines = 1500                       # the size ceiling for a Python module (rule S4)
root_python_files = false              # allow .py files at the repository root (rule S3)
root_python_allow = ["setup.py"]       # ... or only these root files (a waiver `S3 <file>` also works)
docstring_exempt = ["/vendor/"]        # paths whose modules need no docstring (rule S5)
structure_dir = "esoi"                 # the folder that holds the top intent (default "esoi"; "structure" and "docs/structure" work when set)
tracker_folder = "tracker"             # the generated review tracker inside structure_dir; never read as an intent
overall = "docs/overall"               # the overall solution network's folder (five record files); detailed records link up to it
evaluation_dir = "evaluation/components"   # one folder per evaluated component
results = "evaluation/components/results.csv"
shared_eval_dirs = ["__pycache__"]     # folders in evaluation_dir that are not a solution's metric
code_paths = ["mylib"]                 # what counts as the measured code when marking a result "-dirty"; an entry may point into
                                       # a sibling repository ("../sibling/pkg"): its own commit is recorded in `code_shas`
                                       # entries are git pathspecs, so ":(exclude)mylib/data" leaves bundled text out
paid_arms = ["chat/openai"]            # arms `esoi run --stale` skips because they spend money (also: PAID = True in the module)
prices = { "model-x" = { input = 3.0, output = 15.0 } }   # USD per million tokens; computes cost_usd when a provider reports none
metric_command = '(?:esoi run|run\.py) (\w+) --impl (\w+)'   # how a metric's command names a component and an implementation
live_imports = ["mylib"]               # an evaluation implementation importing these drives live code (rule S12)
live_calls = ["common.build_app"]      # ... or calls one of these attributes
selection = "mylib/selection.py:SELECTION"   # a selection table, file path or module (rules S7, S14, S23); an entry may omit "default"
                                       # (the records' `selected` is then the default). Write it as a [selection] table to add deployment choices.
template_source = "path/to/SKILL.md"   # where the intent template is read from (or set ESOI_TEMPLATE_SOURCE)
templates_dir = "docs/templates"       # generated non-code templates; excerpts_file = "docs/explanation/from-the-skill.md"
plugins = ["tools/my_rules.py"]        # extra rule modules (a file path or an importable module)
disable = ["S13"]                      # rule ids that do not apply here
tracker_extra = { solutions = ["area"] }   # extra record columns kept on the tracker tabs, after the key

[selection]                            # instead of the string above: deployment choices (the third layer of the cascade of esoi.runtime)
table = "mylib/selection.py:SELECTION" # optional: the selection table
greet-a-person = "loud"                # solution_id = "implementation name"; the environment variable ESOI_SELECT_GREET_A_PERSON beats it

[rules.S13]                            # per-rule options
layers = ["core"]                      # layers (or paths = ["mylib/core/"]) that may not read the environment

[hermetic]                             # variables scrubbed while an evaluation runs
prefixes = ["MYAPP_"]
names = ["API_KEY"]
set = { MYAPP_MODE = "offline" }

[consumer]                             # for `esoi consumer check`: the library this repository builds on
library = "otherlib"
column_prefix = "lib"
port_modules = ["otherlib.ports"]
pin_name = "otherlib"
selection = "otherlib.selection:SELECTION"

[sheets]                               # for `esoi sheet-sync`: ids and key files come from the environment
sheet_id_env = "ESOI_SHEET_ID"
credentials_env = "ESOI_SHEETS_CREDENTIALS"
state_file = ".esoi_sync_state.json"
[sheets.tabs]
Problems = { csv = "esoi/tracker/problems.csv", key = "problem_id", prefix = "PROB-" }

[hygiene]                              # for `esoi hygiene`
allow_email_domains = ["corp.test"]
exclude = ["tests/fixtures/"]
[hygiene.patterns]                     # your own secret shapes, reported under these names
acme-key = "acme_[A-Za-z0-9]{24,}"

[skill]                                # for `esoi skill`: a public copy of a private skill (see esoi/skill.py)
dir = "skill/myskill"                  # the primary copy; `copies` lists folders that must hold the identical copy
include = ["SKILL.md", "notes/*.md"]   # the files that ship, relative to the source (ESOI_SKILL_SOURCE or --source)
[[skill.substitute]]                   # a regular expression that must match once; the reason is required
file = "SKILL.md"
pattern = " under \\S+ \\(private\\)"
replacement = ""
reason = "names a private folder"
```

## Record files

`structure_dir` holds `components.csv` (`component_id, layer, path, role, solutions`), `waivers.csv`
(`rule, path, reason`) and the five record files, each with the template's fields as columns plus links:
`problems.csv`, `ideals.csv`, `solutions.csv`, `implementations.csv`, `metrics.csv`. Headers to copy are in
[docs/templates/record-headers/](../../../docs/templates/record-headers/). A rule that reads a column a file lacks reports it
(`no `port` column ...`) and sees it as empty; `port` is only a finding when a Protocol class or a selection table needs it.
A module may hold several implementations: list them as `path::name` in the solution's `implementations` cell and give each
record in `implementations.csv` the same `path`; rule S14 accepts a selection-table module that either lists, and the record
ids need not follow any pattern (the default is `solution:file-stem`, `solution:name` also matches).

`solutions.csv` may carry two optional columns beyond the template: `promotion` (`automatic` lets `esoi select --promote`
switch the selected implementation when a rival clearly wins on the solution's own metric; empty means a person applies the
printed proposal) and, as for any record, nothing else is required. The code under `code_paths` is read (not imported) for
`@solution`, `@implementation` and `register` declarations (rule S30; `esoi records sync` writes the missing rows).

## Results log

`esoi run --record` appends to `results` with columns `date, component, impl, cases, passed, dev, heldout, model_calls,
tokens_in, tokens_out, cost_usd, seconds, git_sha, cases_sha, sample, model, details`, plus `code_shas` (`../sibling/pkg@abc1234`,
`;`-separated, `-dirty` for uncommitted changes) when `code_paths` names code in another repository. `cost_usd` is what the
provider reported, else tokens times the `prices` entry of the model (an exact name, else the longest listed prefix), `0.0` when no
model was called, and blank when the model has no price. `sample` is blank for the full set, `sample:N` for `--sample N` and
`only:ids` for `--only`; the leaderboard compares two arms only on rows with the same `cases_sha`, `sample` and case count
(a log from before the column is told apart by the count), each rival on the newest such run both have, and reports a rival
with none as not comparable (`--strict` fails on it).

## Environment

| Variable | Used by |
|---|---|
| `ESOI_TEMPLATE_SOURCE` | `esoi template sync` and rule S27 |
| `ESOI_SHEET_ID`, `ESOI_SHEETS_CREDENTIALS` | `esoi sheet-sync` |
