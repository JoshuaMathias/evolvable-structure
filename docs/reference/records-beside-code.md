# Records beside the code (standard)

A repository that applies ESOI can keep each solution's records in the folder that holds its code, instead of in one `esoi/` folder.
This page is the standard: the exact layout, which files each kind of folder holds, how names work, what is generated, what each
README shows, and what `esoi check` reports. It is one of two rival implementations of the solution `intent-registry`: the layout
in [the intent folder template](templates/intent-layout.md) (`esoi_folder`) and this one (`beside_code`). The metric
`metric-navigable-records` measures both on the same repositories, and the selected one is the library's default recommendation;
a repository chooses with its own configuration. The fill-in version is [the solution folder template](templates/solution-folder.md).

## Both layouts, any language

Both layouts are arms of `intent-registry` and both stay available; a repository chooses in `esoi.toml` (the presence of
`beside_code` is its choice), and `esoi select intent-registry` shows which arm the measurement favours. Neither depends on Python.
A record reaches its code only through the `filepath` column (`path`, or `path::symbol`), never by importing or a decorator, so a
JavaScript, TypeScript, Go or mixed repository uses either layout, and folders, READMEs and diagrams come from the records alone. What
needs Python is optional and switches on only where the repository declares Python code (`package` in `esoi.toml`): the
`@solution` and `@implementation` scan (`esoi records sync`), the typed `run(Interface)` call and the one-line entry check
(rule S37). A repository in another language records its own entry call in the solution row, as the first code span of `usage_notes`
(for example `` `greet("Ada")` ``), and its page shows that call.

| The repository | Use |
|---|---|
| Its code can be organized by solution: a library, a service, a package that is free to put a folder where it likes | Records beside the code |
| Its build or framework fixes its folder structure (an app framework, a monorepo with generated or shared folders, generated code), or its code folders must hold only code | The `esoi/` folder |
| Unsure | Start with the `esoi/` folder and run the metric on both: `esoi run navigable_records --impl esoi_folder` and `--impl beside_code` with `ESOI_GLANCE_ADOPTERS` naming the repository; the layout that passes more solutions is the one to move to (`esoi records place`). |

The metric lays the repository out both ways in a temporary tree from the records alone (every folder that holds an implementation's
code may host records), so it is computed for any repository of any language, and the choice is measured, not assumed.

## Opting in

In `esoi.toml`, list the folders (paths or globs from the repository root) that may hold records next to code:

```toml
[records]
beside_code = ["mypackage", "mypackage/*"]
```

Nothing else changes in the configuration. Without the key the library reads only the structure folder, as before.

## The layout

```
esoi/                          the top intent only
  intent.csv
  README.md                    generated: the whole network at a glance, with links to every folder below
  components.csv  waivers.csv  results and other files that are not records: stay here
mypackage/                     a solution folder (it holds code, records and a generated README)
  solutions.csv  implementations.csv  metrics.csv  problems.csv  ideals.csv     only the files it has rows for
  README.md                    generated, never edited
  module.py                    the code the implementations name in `filepath`
  area/                        a code folder below it, with its own records and README when it holds an implementation
  sub-intent-id/               a sub-intent beside its code: intent.csv, the same record files, a generated README
```

A folder is one of three kinds:

| Kind | Marker | Holds |
|---|---|---|
| Top intent folder | `intent.csv`, in the structure folder | The top intent's record and the files that are not records (components, waivers, results). It holds no solution row once the records are placed. |
| Solution folder | any of the five record files, no `intent.csv` | The records of the solutions whose code it holds, and a generated README. Its rows belong to the nearest folder above it that has an `intent.csv`, else the top intent. |
| Sub-intent folder | `intent.csv` | A sub-intent: its own record, its `implements` naming the parent intent's implementation it arises from, its record files and a generated README. Its folder is named by its `intent_id`. A folder below it that has no `intent.csv` is a solution folder of that sub-intent. |

A folder with no record file and no `intent.csv` is just code and is not read as records.

## Where each record lives

Each record lives once, in one folder. `esoi records place` (a dry run without `--apply`) moves every record to the folder below, and
`esoi records gather` moves them back into the structure folder.

| Record | Lives in |
|---|---|
| Implementation | The listed folder at or above the folder of the file its `filepath` names, the nearest one. |
| Solution | The lowest listed folder that holds the code of all its implementations. One code folder: that folder. Code in two folders: the folder above both. So its spec and its code are in the same folder or one link apart. |
| Metric | With its solutions: the lowest listed folder that holds them all. |
| Problem | With its solutions, likewise. |
| Ideal | With its problems, likewise. |
| A record with no code to follow | Stays where it is. |

A row never leaves the intent that owns it: the rows in and below a sub-intent folder belong to that sub-intent, and `place` skips any
move that would change the owner. An id is unique across the whole tree, so a link in one folder may name a record in another.

## Forms of implementation

What an implementation record's `filepath` points to says which form it takes (no new field; `description` and `uses_solution_ids`
say the rest):

| Form | `filepath` points to | Example |
|---|---|---|
| Code | A source file in any language: a declared class or function, optionally `path::symbol` | `src/greet/greet.ts`, `mypackage/recall/store.py::LocalStore` |
| Reference | A registry file that lists the files, services or practices that implement the solution: a CSV whose `filepath`, `path`, `paths`, `file` or `files` column holds repository paths (`;` separated), or a markdown or text file whose relative links name them | `mypackage/registry/hub_integrations.csv` |
| Registry row | `registry-file.csv::row-id`: a real-world system (an external service, an organization, a process) recorded as one row of a registry; the first column of the row is its id | `mypackage/registry/hub_integrations.csv::stripe` |

The generated README of a solution folder shows "Implemented by" under each solution: the files its implementations name, the files
the code declares it in (`@implementation`), the paths its reference registries list, and the files of the components that
`components.csv` assigns to it (its ownership map), at most 8 with a count of the rest. It is generated from those sources and never
hand-kept. Rule S40 informs when a reference or registry lists a path that does not resolve or a row that does not exist, and when code
that declares a solution is missing from the registry that lists its implementations.

## Reading and generating

The library reads the structure folder and every listed folder as one tree (`esoi.intents.folders`), so the rules, the cascade, the
selection, the assembly and the tracker see the same registry as with one folder. No roll-up file is generated and nothing is copied.
A person who wants the whole network in one place opens `esoi/README.md`, which lists every solution with its entry call and
selected implementation and links to every folder; a program that wants one table reads the registry (`esoi.registry.load`) or the
spec index (`esoi spec index`), not a CSV file.

`esoi readmes` (also `esoi check --write-docs`) writes `README.md` in the top intent folder, in every sub-intent folder and in every
solution folder. Rule S8 reports a page that is out of date. A page is never edited: edit the records and generate again.

## Arms whose code lives in an `impls` folder

An implementation's code may live in a folder of arms, `<evaluation_dir>/*/impls` by default, while its record belongs to the
intent that owns it (a sub-intent folder beside the package code). `esoi records place` never moves a record out of its intent,
so such a folder holds no records. Instead it is covered by a README that `esoi readmes` generates in it: a table of the arms
whose code it holds, each with its code, and a link to the README of every owning intent. The page says it is generated and is
kept current by rule S8 once written. A README in that folder that `esoi readmes` did not write is left alone and covers it.

More folders are named under `[records] arm_folders` (globs from the repository root). Only a folder matching those patterns
that holds no records of its own, is not at or around the row's folder and whose rows have a known owning intent is covered;
arms anywhere else, or of no known owner, are still reported. The link distance of a solution's code in such a folder is measured
through the owner link: one past the folder that holds the row.

## Code in a shared layer

Modules that several areas import stay in a shared layer (`core`, `adapters`), not in each area's folder. A solution whose spec is in
an area folder and whose code is in a layer that `layers` ranks below the areas is measured **one link** from its intent when the
intent's own code reaches that file: a module of the area folder or the code of an implementation its rows name imports the file, or
names the solution (its id or its interface class, in executable code, as an area does when it wires members by typed need). An area
folder that `layers` does not name has the rank the named area folders share. Code in a layer at or above the area, in a layer
`layers` does not declare, in `docs`, `examples`, `scripts` or `tests`, or that the intent's code never reaches, is still reported
as more than one link apart. Python only: the imports are read from the syntax trees.

## The README of a solution folder

| Part | What it holds |
|---|---|
| Title | The name of the solution when the folder holds one, else the folder's name, and a note that the page is generated from the CSV files in the folder |
| One section per solution | Its name and id, the first sentence of its purpose, its one-line entry call, its selected implementation, its metrics |
| Diagram | The Mermaid diagram of the solutions in this folder and the folders below it, when one builds on another |
| Implementations | A table of the implementations this folder holds: id, name, a link to its code, and whether it is the selected one |
| Metrics | Each metric of the folder with the implementation that leads it in the results log |
| Problems and ideals | One line each |
| Implemented by | Under each solution, the files that implement it, linked, generated from the records, the declarations and the ownership map |
| Where to go next | Up to the folder above (or the intent), down to each folder below it, out to the repository's top README |

The page states finished truth only (no `unconfirmed` marker, no em dash, no machine path), as in
[the intent README standard](intent-readme.md), which also describes the README of the top intent and of a sub-intent. The top
intent's README gains one line, "Records beside the code", that links to each solution folder it owns.

## What is measured

The metric `metric-navigable-records` (component `navigable_records`) runs one case per solution of this repository and of the
adopting repositories (named by `ESOI_GLANCE_ADOPTERS`). Each arm lays the repository's records out its own way in a temporary tree
(the code is not copied, only an empty file where each implementation says its code is) and the same checks score the tree:

- `together`: the folder holding the solution's row and the folder of each implementation's code are the same folder or one link
  apart (parent and child);
- `clicks`: from the repository's top README, following links between README pages, the page of the folder that holds the solution's
  row, naming it, is within 3 clicks;
- `implemented`: the page that names the solution links, in one hop, to each file that holds its implementations (a code file, or the
  reference or registry file an implementation names);
- `unduplicated`: none of the solution's records is kept in two places;
- `readme`: every folder that holds the code of one of its implementations has a `README.md`;
- `pure`: laying the records out again writes the same pages.

The first stage needs no model. The selection rule chooses the arm that passes more cases, and says whether that is significant or a
best guess.

## What `esoi check` reports

Rule S40 runs only where `[records] beside_code` is set. It informs and never blocks: `esoi check --findings` lists each finding with its
next action. A waiver excuses one key.

| Finding | Next action |
|---|---|
| A solution's spec is in one folder and its code in a folder more than one link apart | `esoi records place --apply`, or list the folder that holds the code under `beside_code` |
| A folder holds the code of an implementation but has no `README.md` | `esoi records place --apply` (it moves the records there and writes the page), or list the folder under `beside_code` (or under `arm_folders` when the record belongs to an intent elsewhere) |
| A folder of arms owned by an intent has no generated `README.md` yet | `esoi readmes` |
| A solution's code is in a shared layer the intent's code does not reach | Import or wire it from the intent's code, move the code, or record the solution where the code is |
| A record is kept in two places | Delete the copies that are not in the folder that holds its code |
| A reference or registry lists a path that does not resolve, or a registry row does not exist | Correct or remove the entry (also reported where `[rules.S40] enabled = true` without `beside_code`) |
| Code declares a solution but the registry that lists its implementations leaves it out | Add the file to the registry |

How to adopt it, step by step: [keep records beside the code](../how-to/keep-records-beside-the-code.md).
