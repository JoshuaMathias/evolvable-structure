# Apply ESOI with the Python tools

The `esoi` package checks the structure you wrote, runs and records measurements, ranks the alternatives, and builds a review
sheet. It is one implementation; the record formats are plain CSV, so another tool could read the same files.

## Install

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git#subdirectory=implementations/python"
```

Add `@<commit>` after `.git` to pin a version. Python 3.11 or later; no dependencies in the core. For Google Sheets sync add
the extra: `esoi[sheets]`.

## A new repository

```bash
esoi init                                  # writes a small example that already passes
git init && git add . && git commit -m "esoi example"
esoi run greet_a_person --impl live --record
esoi check --strict
esoi leaderboard
```

Rename the example's parts, replace its text with your own intent, and keep running `esoi check`. The example includes an
overall network and detailed records that link up to it.

## An existing repository

1. Write `esoi.toml` at the root (see the [configuration reference](../../implementations/python/docs/configuration.md)):
   at least the package name and its layers.
2. Write `components.csv` first: every file in exactly one component. `esoi check` names the files that are not.
3. Write the overall network, then the detailed solutions, with a gap noted where no metric exists yet. Problems and
   solutions need not pair up: a problem can need several solutions, and a solution can address several problems. Split a
   solution only as [when-to-split.md](../explanation/when-to-split.md) describes.
4. Turn gaps into evaluation components one at a time (`evaluation/components/<name>/` with cases, a scorer and
   implementations), and record a run for each with `esoi run <component> --impl <name> --record`.
5. Keep the rules that fit. Switch off those that do not (`disable = [...]`), and record a justified exception as a waiver
   with a reason. Waivers can only shrink: the check reports one that no longer applies.
6. Add your own rules as a plugin when a mistake has happened twice.

## When to run what

Metrics that call no paid service run on every change; paid ones run only when a decision depends on them, staged and under a
call budget. Write your repository's version down with the [metric run policy template](../templates/metric-run-policy.md) and
read [when metrics are run](../explanation/when-metrics-are-run.md). In day-to-day use:

```bash
esoi run <component> --impl <name>        # the part you changed
esoi check                                # before committing
git commit ...                            # measured code and cases committed
esoi run --stale                          # re-run and record whatever is stale, then commit the results log
esoi check --strict                       # every recorded result is current
```

`esoi run --stale` re-runs the selected arm of each solution and the rivals recorded beside it (a verdict that rests on a rival
recorded before the measured code changed is flagged by `esoi check --strict`, waive one as `S20 <solution>:<implementation>`),
but never an arm that may spend money: one that declares `PAID = True`, is listed in `paid_arms`, or whose last run called a
model. Those are listed as skipped with the command to run them; opt in with `--include <component>/<impl>` or `--include-paid`.
Code the measurement depends on may sit in a sibling repository: name it in `code_paths` (`../sibling/pkg`) and the results log
records that repository's commit in a `code_shas` column. Give `prices` in the configuration and a model run's `cost_usd` is
computed from its tokens; with no price it is left blank, never `0`.

`esoi check` keeps a small cache of what it learned about each module in `.esoi_cache/` (gitignored), so a second run reads
only the files that changed; `cache = false` in the configuration turns it off.

## Keeping the templates in step with the skill

The questions in the templates come from the author's `SKILL.md`. After it changes:

```bash
ESOI_TEMPLATE_SOURCE=path/to/SKILL.md esoi template sync
```

regenerates the parsed field list, every document in `docs/templates/` and the quoted excerpts. `esoi template check`
tells you whether they are stale; a new field appears as a missing column in your records until you fill it.

## Commands

| Command | Does |
|---|---|
| `esoi check [--strict] [--write-docs]` | Runs every rule; `--strict` also rejects results recorded on uncommitted code |
| `esoi rules` | Lists the rules |
| `esoi run <component> --impl <name> [--record]` | Runs and records one implementation (`--sample N`, `--only IDS`, `--max-calls N` for staged, budgeted runs) |
| `esoi run --stale [--include-paid \| --include C/I]` | Re-runs and records every selected implementation, and the rivals beside it, whose result is stale; paid arms are skipped unless included |
| `esoi leaderboard [--strict]` | Ranks implementations and prints a verdict per solution |
| `esoi tracker build\|check` | Builds the review sheet tabs |
| `esoi sheet-sync sync\|push\|pull\|check` | Syncs those tabs with a Google Sheet |
| `esoi template sync\|check` | Parses the template source and regenerates the templates |
| `esoi skill sync\|check\|install` | Generates and verifies the public copy of the skill, or installs it ([guide](install-the-skill.md)) |
| `esoi consumer check` | Checks a repository that builds on a library |
| `esoi hygiene [--history]` | Scans for secrets and private data before a public push (a folder that is not a git checkout is walked; `[hygiene.patterns]` adds your own secret shapes) |
| `esoi select <solution>` | Shows what a selection table resolves |
| `esoi init` | Writes the passing example |
