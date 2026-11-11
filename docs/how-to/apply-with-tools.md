# Apply ESOI with the Python tools

The `esoi` package checks the structure you wrote, runs and records measurements, ranks the alternatives, and builds a review
sheet. It is one implementation; the record formats are plain CSV, so another tool could read the same files.

## Install

```bash
pip install esoi
```

Add `@<commit>` after `.git` to pin a version. Python 3.11 or later; no dependencies in the core. For Google Sheets sync add
the extra: `esoi[sheets]`.

The tools check the records against [the repository standard](../reference/templates/repository-standard.md). An AI agent that applies
them follows [ESOI applied to AI behaviour](../explanation/esoi-for-ai.md); a piece of work records its metric before and after as in
[keep a metric's value before and after](measure-before-and-after.md); a program built on a library is kept in step as in
[keep a consumer current with an AI agent](keep-a-consumer-current-with-an-ai-agent.md).

## The graceful path: declare, call, measure, promote

State each fact once, where the code is ([the full page](../explanation/graceful-selection.md)):

```python
from esoi import implementation, solution

@solution("greet-a-person")                  # declare the interface once
def greet(name: str) -> str: ...

@implementation("greet-a-person", "plain")   # and each alternative beside its code
def plain(name: str) -> str:
    return f"Hello, {name}!"

greet("Ada")                                 # call: runs the project default from the records
greet("Ada", using="plain")                  # this call only; a block: `with override("greet-a-person", "plain"):`
```

```bash
esoi records sync                            # the records follow the declaration (you write only the text it leaves empty)
esoi run greet_a_person --impl plain --record    # measure it beside the others; no wrapper file needed
esoi select --promote                        # switch to the winner when its own metric says so (or print the proposal)
```

The selection table (below) is the advanced layer underneath. `esoi new solution <id>` starts a whole solution in one command.

## A new repository

```bash
esoi init                                  # writes a small example (specifications in esoi/); the check names what only you can write
git init && git add . && git commit -m "esoi example"
esoi run greet_a_person --impl live --record
esoi check --strict
esoi leaderboard
```

Rename the example's parts, replace its text with your own intent, and keep running `esoi check`. The example is a top intent (a folder with an `intent.csv`) holding a single top solution, `project-purpose`, and the solutions it builds on: the evolvable structure the project applies (`project-structure`) and a stand-in for your own work (`greet-a-person`). The check names, until you fill them, the top intent's name and vision statement (why your project exists, in your words) and the top solution (what it is for).

## An existing repository

1. Write `esoi.toml` at the root (see the [configuration reference](../../implementations/python/docs/configuration.md)):
   at least the package name and its layers.
2. Write `components.csv` first: every file in exactly one component. `esoi check` names the files that are not.
3. Write the top intent (`intent.csv`: name and vision statement), then its solutions, with a gap noted where no metric
   exists yet. Problems and solutions need not pair up: a problem can need several solutions, and a solution can address
   several problems. Create a sub-intent only as
   [when-to-create-a-sub-intent.md](../explanation/when-to-create-a-sub-intent.md) describes. A repository that still
   uses the two-level overall layout is loaded as before; see [migrate-to-intents.md](migrate-to-intents.md).
4. Turn gaps into evaluation components one at a time (`evaluation/components/<name>/` with cases, a scorer and
   implementations), and record a run for each with `esoi run <component> --impl <name> --record`.
5. Keep the rules that fit. Switch off those that do not (`disable = [...]`), and record a justified exception as a waiver
   with a reason. Waivers can only shrink: the check reports one that no longer applies.
6. Add your own rules as a plugin when a mistake has happened twice.

## When to run what

Run a metric when what it teaches is worth its cost: run the part you changed while you work, and measure for a decision when a
choice turns on the number; paid ones run only when a decision depends on them, staged and under a call budget. No commit hook and no
CI step runs metrics, and a changed file only informs. Write your repository's version down with the [metric run policy template](../reference/templates/metric-run-policy.md) and
read [when metrics are run](../explanation/when-metrics-are-run.md). In day-to-day use:

```bash
esoi run <component> --impl <name>        # the part you changed
esoi check                                # before committing
git commit ...                            # measured code and cases committed
esoi run --stale --plan                   # which recorded results no longer describe the code, which file and owner, and why each is or is not re-run
esoi run --stale --for-decision           # when a decision or release depends on the selected arms: re-run and record those that are stale
esoi check --strict                       # lists each stale recorded result as advice (plain `esoi check` prints one info line with the count; never a failure)
esoi check --for-decision                 # when a decision or release depends on the results: a stale one is then a to do
```

`esoi run --stale` reports a row whose measured code changed and re-runs only what is worth running (a selected arm never measured, an expiration that has passed, `--for-decision`, `--include`; `--all` re-runs every stale arm); which files count as measured code is the staleness rule ([Choose when a result is stale](choose-when-a-result-is-stale.md)). `esoi run --stale --plan` lists what would run and why, and runs nothing; a real `--stale` pass can be killed and run again, because the recorded rows are the progress and it starts at the arm that was in flight. `esoi run --stale` re-runs the selected arm of each solution and the rivals recorded beside it (a verdict that rests on a rival
recorded before the measured code changed is listed by `esoi check --strict`, waive one as `S20 <solution>:<implementation>`),
on the sample the selected arm's latest row used (`--full` runs the whole set), so a re-record stays comparable; a rival
recorded on another sample is not stale, it is not comparable, and is re-run too. It never runs an arm that may spend money: one that declares `PAID = True`, is listed in `paid_arms`, or whose last run called a
model (unless it declares `SIMULATED = True`, a deterministic stand-in that counts calls and spends nothing). Those are listed as skipped with the command to run them; opt in with `--include <component>/<impl>` or `--include-paid`. An arm included with `--include-paid` is still skipped, with the reason, when another arm already passed every case on the same cases and sample at no higher cost (or, with a balanced score, when it cannot win on cost or time either); naming it with `--include` runs it.
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

regenerates the parsed field list, every document in `docs/reference/templates/` and the quoted excerpts. `esoi template check`
tells you whether they are stale; a new field appears as a missing column in your records until you fill it.

## Commands

| Command | Does |
|---|---|
| `esoi check [--strict] [--write-docs]` | Runs every rule; `--strict` also rejects results recorded on uncommitted code |
| `esoi rules` | Lists the rules |
| `esoi run <component> --impl <name> [--record]` | Runs and records one implementation (`--sample N`, `--only IDS`, `--max-calls N` for staged, budgeted runs). Every run, recorded or not, is saved case by case in `runs.csv` beside the results log; an unrecorded run stops at its first failing case (`--keep-going` runs on), `--failed` reruns just the cases that failed last, and a run of every case waits until they pass ([why](../explanation/when-metrics-are-run.md#iterate-on-the-failing-cases-before-the-whole-set)). A later stage reuses cases already run for the same implementation version (`--fresh` runs them again). Refuses a run that cannot inform a decision unless `--differs \"harness: ...\"` or `--force \"reason\"` ([why](../explanation/when-metrics-are-run.md), [how to declare the public benchmark](use-public-evidence.md#4-skip-runs-whose-answer-is-already-public)) |
| `esoi run --stale [--plan] [--full] [--for-decision \| --all] [--include-paid \| --include C/I]` | Reports every selected implementation and rival whose result is stale and why; re-runs and records only what is worth running (never measured, expired, a pending decision with `--for-decision`, named with `--include`, or everything with `--all`); paid arms are skipped unless included |
| `esoi stale --explain COMPONENT \| --count` | The changed files that count for each arm of a component and who owns them; how many rows each staleness rule calls stale now |
| `esoi leaderboard [--strict]` | Ranks implementations and prints a verdict per solution |
| `esoi tracker build\|check` | Builds the review sheet tabs |
| `esoi diagram [--check]` | Draws each intent's solution diagram (Mermaid, `diagram.md` beside its records) from the solutions' outputs and the implementations' `uses_solution_ids`; `--check` lists the ones out of date. `esoi check --write-docs` writes them too |
| `esoi readmes [--check]` | Writes the README of every intent folder (at a glance: vision, solution coherence, diagram, entry calls, links, then the full record); `--check` lists the stale ones. `esoi check --write-docs` writes them too |
| `esoi sheet-sync sync\|push\|pull\|check` | Syncs those tabs with a Google Sheet |
| `esoi template sync\|check` | Parses the template source and regenerates the templates |
| `esoi skill sync\|check\|install` | Generates and verifies the public copy of the skill, or installs it ([guide](install-the-skill.md)) |
| `esoi consumer check` | Checks a repository that builds on a library |
| `esoi hygiene [--history]` | Scans for secrets and private data before a public push (a folder that is not a git checkout is walked; `[hygiene.patterns]` adds your own secret shapes) |
| `esoi select <solution>` | Shows which implementation runs and which layer of the cascade chose it |
| `esoi select --promote [solution] [--dry-run]` | Switches `selected` to the rival with the highest result on the solution's metric (the verdict says if the lead is significant), or prints the proposal |
| `esoi follow [--parent P] [--solution ID] [--plan] [--run-free] [--json]` | Judges a parent repository's current selections on your own metric: adopt, keep an override, drop it, or not measured ([how-to](follow-a-parent-repositorys-selections.md)) |
| `esoi lock [--update\|--diff\|--status]` | Pins the selected implementation per solution in `esoi.lock.json` and moves it on your schedule ([how-to](pin-selections-for-production.md), [reference](../reference/lock.md)) |
| `esoi select --snapshot FILE` | Writes the defaults and modules for a package shipped without the records |
| `esoi records sync [--intent ID] [--dry-run]` | Writes the rows the code declares and the records lack |
| `esoi new solution <id> [--intent ID]` | Writes the records, a code skeleton with the decorators and an evaluation folder for a new solution |
| `esoi projects init\|add\|list\|check\|index\|where` | Keeps a local index of the projects ESOI is applied to ([local-index.md](../explanation/local-index.md)) |
| `esoi init` | Writes the passing example |
