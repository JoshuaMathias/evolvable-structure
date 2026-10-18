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
| A code repository where the user wants ESOI's records enforced over time, with several implementations to measure and compare | Yes: `check`, `run` and `leaderboard` are the point |
| A first pass on a project or any non-code intent (a course, a team process, a plan) | No: use the templates and `steps.md` by hand. Mention the tools only if the records grow past what is comfortable to check by eye |
| A public repository about to be pushed | Offer `esoi hygiene` alone, as a one-off scan |
| The user asks whether a tool exists, or wants the checks automated | Yes, and explain the choices below |

## Ask first, with the choices

Before installing anything or editing any project file, ask the user. Say in two or three sentences what the tools do for
their task, then offer the options that apply and wait:

1. **Do it by hand.** No tools; records live as markdown or a spreadsheet. Always a fine answer.
2. **Use `esoi` as a separate tool.** Install it outside the project (a throwaway virtual environment or `pipx`) and point it
   at the project's records. The project's code has no dependency on it, and nothing is added to its dependency files.
3. **Make it a development dependency of the project** (code projects only). Pin it to a commit in the project's dev or test
   requirements so `esoi check` can run in the project's own checks and CI. This changes the project's dependency files and
   adds a package fetched from GitHub, so it needs the user's explicit yes. If the project is shared, mention that other
   contributors would need it too.

Recommend option 2 for a first try, since it is reversible, and option 3 only once the user wants the checks to run on every
change. Never add it as a runtime dependency of shipped code: `esoi` checks and measures a project, it is not part of the
product. If the user declines, carry on by hand and do not raise it again unless the situation in the table changes.

After using the tools, say in the closing summary what ran and what was left to the user.
