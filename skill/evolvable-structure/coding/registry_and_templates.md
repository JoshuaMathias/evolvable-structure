# evolvable-structure coding examples: registry, templates and definitions

Part of `../coding.md`. A name-keyed registry library, a repository template library and easyinfo, and the Project Documentation board's parameter format. Load for finding code by name, scaffolding a project, packaging, or documenting parameters. These are how one project met an ideal, not rules for every
project: carry over the purpose, and copy the mechanism only where the codebase already uses it.
Evidence pointers read `file > heading`, with files in `../sources/`.

**1. Registry library: a definition is a folder, found by name.** *Purpose:* callers should not break
when code moves (pattern 2). Each definition is a folder holding `<name>.py`, found anywhere under the
repo root by its name, so it can move or be renamed without touching callers, and a name can come from
config or a database row.

```python
# the registry walks the package; folder name == file name == definition name
def_filename = join(dirpath, dir_name, dir_name + ".py")
# callers: import_definition("train_revenue_standard")  -> the object, not the module
```

**2. Registry library, template library and easyinfo: one command scaffolds, and a new project
is renames in one file.** *Purpose:* starting a new case should be a few substitutions, not a copy
(patterns 1 and 4). `define <name>` creates the folder, the file and the test. A new package is
placeholders replaced in `__meta__.py`, with the framework as one dependency line.

**8. Registry library and pipeline library: ship only what is imported.** *Purpose:* a small default install
(pattern 15). Production packages the definitions the code imports, found by scanning imports; an API
package lists what it needs in a text file.

**12. Project Documentation board: parameter documentation is part of the definition.** *Purpose:*
defaults a reader can see and change (patterns 3 and 7). Each parameter is written
`var_name (type)=default: Description`, which is both the docs and the interface.

## Known weaknesses

The registry library's README promises a `version` parameter and metric-based selection the code lacks, and names and template leftovers drifted. Lesson: an extension point counts once it is built and tested.
