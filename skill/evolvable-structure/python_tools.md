# The optional Python tools (`esoi`)

The ESOI repository (https://github.com/JoshuaMathias/evolvable-structure) also ships a Python package and command, `esoi`.
You never need it to apply ESOI: the principles, the record types and `steps.md` work with a pen, a spreadsheet or a few
markdown files. The tools only automate the parts that are tedious by hand, so offer them when they would save real work, and
never install or require them on your own.

## What they do

- `esoi check` runs the structural rules over records kept as plain CSV: every record links up, every solution has a metric
  and a selected implementation, every file belongs to a component, and recorded results are current.
- `esoi run` runs each implementation of a solution on the same cases and records the result; `esoi leaderboard` ranks them
  and says which one the metric selects.
- `esoi tracker` and `esoi sheet-sync` build a review sheet (and sync it with a Google Sheet) so a person can steer by
  reviewing problems, ideals and metrics instead of reading implementations.
- `esoi.select` is the part meant for production: code asks it which implementation of a solution is currently selected
  (`Selector(load_table(...)).resolve("greet")`, with per-call overrides), so the selection recorded in the structure is what
  actually runs and changing it needs no code change. `esoi consumer check` verifies a repository that builds on a library
  this way.
- `esoi projects` keeps a local ESOI index (`projects.csv` and `INDEX.md` under `$ESOI_HOME` or `~/.esoi/`) of the projects ESOI is
  applied to, how they relate and where to look in each; `esoi projects where` names the project the working directory is in.
- `esoi hygiene` scans for secrets and private data before a public push. `esoi init` writes a small example that passes.

Requirements: Python 3.11 or later, no dependencies in the core, Apache-2.0 licence. Install from the repository (it is not
on PyPI):

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git#subdirectory=implementations/python"
```

Add `@<commit>` after `.git` to pin a version. The full guide is "Apply ESOI with the Python tools" on the repository's wiki.

## When to suggest them

| The work | Suggest the tools? |
|---|---|
| A code repository where the user wants ESOI's records enforced over time, with several implementations to measure, compare and select between | Yes: `check`, `run` and `leaderboard` for development, and `esoi.select` if the selection should apply in production |
| A first pass on a project or any non-code intent (a course, a team process, a plan) | No: use the templates and `steps.md` by hand. Mention the tools only if the records grow past what is comfortable to check by eye |
| A public repository about to be pushed | Offer `esoi hygiene` alone, as a one-off scan |
| The user asks whether a tool exists, or wants the checks automated | Yes, and explain the choices below |

## Ask first, with the choices

Before installing anything or editing any project file, ask the user. Say in two or three sentences what the tools do for
their task, then offer the options that apply and wait. There are two separate uses, so ask about each that applies: checking
and measuring the project (development time), and resolving implementations at run time (production).

1. **Do it by hand.** No tools; records live as markdown or a spreadsheet. Always a fine answer.
2. **Use `esoi` as a separate tool.** Install it outside the project (a throwaway virtual environment or `pipx`) and point it
   at the project's records. Nothing is added to the project's dependency files. Reversible, so a good first try.
3. **Add it as a development dependency** (code projects). Pin it to a commit in the dev or test requirements so
   `esoi check` and `esoi run` can run in the project's own checks and CI.
4. **Add it as a runtime dependency** (code projects whose solutions have more than one implementation). The project's code
   calls `esoi.select` so the implementation chosen by the metric is the one that runs in production, and the selection table
   stays the single source of truth. This makes the repository a dependency of the shipped code, so say so plainly: it is
   installed from GitHub, not PyPI, so pin a commit; the core has no dependencies of its own; the project then follows that
   repository's changes only when the pin is moved.

Options 3 and 4 change the project's dependency files, so each needs the user's explicit yes, and for a shared project mention
that other contributors and deploy environments would need it too. Recommend 2 for a first try, 3 once the user wants the
checks on every change, and 4 when the project has implementations to select between and wants the selection applied in
production. If the user declines, carry on by hand and do not raise it again unless the situation in the table changes.

After using the tools, say in the closing summary what ran and what was left to the user.
