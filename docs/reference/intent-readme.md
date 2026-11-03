# The README of an intent folder (standard)

Every intent folder holds a `README.md` that `esoi readmes` writes from its records. It is for a person clicking through the folders of
any repository that applies ESOI, and it is the same for every repository, this one included. The page is never edited by hand: edit
the CSV files, then run the command. A person's own prose about the network stays in a file of their own (`network.md`).

## The layout (`glance`, the selected layout)

| Part | Heading | What it holds |
|---|---|---|
| 1 | the intent's name | The vision statement, a one-line note that the page is generated, and the opportunities (for a sub-intent, the implementation of the parent intent it arises from, linked to the parent) |
| 2 | How the solutions fit together | The solution coherence paragraph |
| 3 | Diagram | The Mermaid diagram of the solutions' connections, the same source as `diagram.md` |
| 4 | Solutions at a glance | One row per solution: its one-line entry call (`package.run("id", example)`, or "no entry declared"), its selected implementation and its metrics |
| 5 | Problems and ideals | One line each: the id and the first sentence; at most 10 of each, with a link to the full list below |
| 6 | Metrics and their leaders | Each metric with the implementation that leads it in the results log and its score |
| 7 | Where to go next | Links down to each sub-intent, up to the parent intent and out to the repository's top README, the record files, and the diagram page |
| 8 | The full record | After a divider (`---`): the full problem, ideal, solution, implementation and metric tables |

A cell that holds only an `unconfirmed:` marker is an unwritten cell and is left out of the page, so a page states finished truth only.
No em dashes appear in generated text. `diagram.md` stays beside the records: it is the diagram on a page of its own (with the
coherence paragraph), generated from the same lines as the diagram in the README, so the two cannot differ.

## Folders beside the code

Where a repository keeps its records beside the code ([the standard](records-beside-code.md)), the top intent's page lists the solution folders under "Where to go next" ("Records beside the code"), a sub-intent beside its code gets the page above, and every solution folder gets its own generated page, described in the standard.

## The two rival layouts

`full` writes the record tables only, in file order (the page before this standard). `links` writes the name, the vision statement
and links to everything else. They are implementations of the solution `readable-records`, measured against `glance` and kept so a
repository can choose one: `[readme] layout = "full"` in `esoi.toml`. Without it the layout is the arm the measurement selected.

## What is measured

The metric `metric-readme-glanceability` (component `readme_at_a_glance`) runs one case per intent folder of this repository and of the
adopting repositories (named by `ESOI_GLANCE_ADOPTERS`, paths separated as `PATH` is). A case passes when:

- `vision`, `coherence` and `diagram` all end inside the first screen: 100 rendered lines (prose wraps at 110 characters, a Mermaid
  block counts as 20 lines);
- `solutions`: every solution of the intent has a row with its entry call (or the statement that none is declared) and its selected
  implementation (or "none selected");
- `links`: every relative link resolves, and the page links each sub-intent, the parent intent and the repository's top README;
- `finished`: no em dash, no `unconfirmed` marker and no machine path;
- `pure`: the text is identical when generated again from a fresh read of the records (nothing hand-kept, no clock);
- `size`: the part above the divider stays within 320 rendered lines, and the long record tables sit below the divider.

The first stage needs no model. A later stage, not run, has a person open three intent folders in each layout side by side and name
the one they would rather open first (`cascading_conditionals` of the metric).

## Commands

| Command | Does |
|---|---|
| `esoi readmes` | Writes the README of every intent folder that differs from what its records generate |
| `esoi readmes --check` | Lists the stale pages and exits 1 when there are any |
| `esoi check --write-docs` | Writes the same pages (and the other generated files) |
| `esoi check` | Rule S8 reports a page that is out of date |

The page reads the results log for each metric's leader, so it changes when a result is recorded: run `esoi readmes` after recording.
