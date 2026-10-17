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
docstring_exempt = ["/vendor/"]        # paths whose modules need no docstring (rule S5)
structure_dir = "docs/structure"       # the records, components, waivers and the generated index
overall = "docs/overall"               # the overall solution network's folder (five record files); detailed records link up to it
evaluation_dir = "evaluation/components"   # one folder per evaluated component
results = "evaluation/components/results.csv"
shared_eval_dirs = ["__pycache__"]     # folders in evaluation_dir that are not a solution's metric
code_paths = ["mylib"]                 # what counts as the measured code when marking a result "-dirty"
metric_command = '(?:esoi run|run\.py) (\w+) --impl (\w+)'   # how a metric's command names a component and an implementation
live_imports = ["mylib"]               # an evaluation implementation importing these drives live code (rule S12)
live_calls = ["common.build_app"]      # ... or calls one of these attributes
selection = "mylib/selection.py:SELECTION"   # a selection table, file path or module (rules S7, S14, S23)
template_source = "path/to/SKILL.md"   # where the intent template is read from (or set ESOI_TEMPLATE_SOURCE)
templates_dir = "docs/templates"       # generated non-code templates; excerpts_file = "docs/explanation/from-the-skill.md"
plugins = ["tools/my_rules.py"]        # extra rule modules (a file path or an importable module)
disable = ["S13"]                      # rule ids that do not apply here
tracker_extra = { solutions = ["area"] }   # extra record columns kept on the tracker tabs, after the key

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
Problems = { csv = "docs/structure/tracker/problems.csv", key = "problem_id", prefix = "PROB-" }

[hygiene]                              # for `esoi hygiene`
allow_email_domains = ["corp.test"]
exclude = ["tests/fixtures/"]

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
[docs/templates/record-headers/](../../../docs/templates/record-headers/).

## Environment

| Variable | Used by |
|---|---|
| `ESOI_TEMPLATE_SOURCE` | `esoi template sync` and rule S27 |
| `ESOI_SHEET_ID`, `ESOI_SHEETS_CREDENTIALS` | `esoi sheet-sync` |
