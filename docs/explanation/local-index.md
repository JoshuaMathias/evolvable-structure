# The local ESOI index

ESOI is applied to some projects and not others, and the records for each live in different places: a repository's
structure folder, a document, a spreadsheet, a board. A person or an agent working on a machine needs to know, for the
project in front of them, whether ESOI is already applied, where its specifications are, what to read first, and which
other projects it builds on or is built on by. The **local ESOI index** answers that in one place on that machine, in a
folder named `.esoi` in the user's home directory, the way a `.claude` folder holds a user's own configuration. The
`ESOI_HOME` environment variable names another folder instead.

## Why it exists

- **Principle 8, leverage existing structure.** The principle asks that structure "facilitate maintaining awareness of
  existing useful structure, when and only when such awareness is useful", and says "don't just build reuse; apply it".
  An index of where ESOI is already applied is that awareness: the agent goes to the existing specifications instead of
  starting new ones.
- **Principle 9, avoid duplication of effort.** The skill and this repository are public and generic. If they listed the
  projects of one user, every other user would carry routing that is wrong for them, and the same facts would live in two
  places. The projects are the user's own, so the index is local; each project's specifications stay in the project.
- **The skill stays generic.** The skill's index routes by kind of task to instructions and examples. Where ESOI is
  applied on this machine comes from the local index, which the skill's first instruction points to.

## How the skill finds it

The skill's first step reads `$ESOI_HOME/INDEX.md`, or `~/.esoi/INDEX.md` when `ESOI_HOME` is not set, if it exists, to
find how ESOI is already applied to the project the work is in, and goes where it says. If none exists and the user
applies ESOI to several projects, the skill offers to start one. With the Python tools, `esoi projects where` prints the
project that contains the working directory (or a given path) with its start-here file and specifications.

## What is in the folder

| File | Holds |
|---|---|
| `projects.csv` | One row per project: a project is a top intent somewhere on this machine or online |
| `INDEX.md` | Generated from `projects.csv` by `esoi projects index`: a short table, how projects relate, and a part you write by hand between markers |
| `projects/<project_id>.md` | Optional longer notes for one project |

The hand-written part of `INDEX.md` is for routing that is the user's own, for example which local skills or playbooks to
read for a kind of task in a given project. The generated part is rewritten each time; the hand-written part is kept.

### projects.csv columns

| Column | Holds |
|---|---|
| `project_id` | A short stable id other rows refer to |
| `name`, `vision_statement` | Optional overrides for a project that has no top `intent.csv` (a board, a file, a project not yet migrated). A project that has one is read from it by `list`, `index` and `where`, so the index never holds a second copy; `check` reports a row that disagrees with it |
| `location` | A local path (`~` allowed) or a URL |
| `kind` | `repository`, `folder`, `file` or `board` |
| `specifications` | Where its ESOI specifications are, relative to `location`: `esoi.toml`, `esoi/`, `structure/`, a single markdown file, a sheet URL |
| `start_here` | The file to read first when applying ESOI there: a contributor guide, a network overview, a playbook |
| `relations` | `;`-separated `<kind>:<project_id>`, kind one of `uses` (builds on its solutions), `used-by`, `sub-intent-of`, `example-of`, `related`. `used-by` follows from another row's `uses`, so write `uses` once |
| `notes` | One line on what differs when applying ESOI there |

### Examples

These projects are made up.

```csv
project_id,name,vision_statement,location,kind,specifications,start_here,relations,notes
orchard-app,,,~/code/orchard-app,repository,esoi/,CONTRIBUTING.md,uses:weather-feed,Metrics run offline; the field trial is paid
weather-feed,,,~/code/weather-feed,repository,esoi.toml,docs/network.md,,
choir-year,Choir year,The choir sings well and enjoys it,~/notes/choir,folder,plan.md,plan.md,,One markdown file; no code
```

The first two projects have a top `intent.csv`, which holds their name and vision statement. The third is one markdown
file with no `intent.csv`, so its row states them.

A project that already has ESOI specifications keeps them where they are. The index points at them, and records no copy of
what they say. A user whose specifications are a single file or a sheet gets a row with `kind` `file` or `board` and the
location of that file; the row is still a reference, not a second source of truth.

## The tools

`esoi projects` has `init` (create the folder and an empty `projects.csv`), `add <path-or-url>` (add a row,
finding the specifications and the first file to read; the name and vision statement stay in the project's top
`intent.csv`, and a project without one takes them from flags, nothing is guessed from its other records), `list`,
`check` (locations and specifications exist, relations resolve, ids are unique, and a name or vision statement does not
disagree with the project's `intent.csv`), `index` (write `INDEX.md`) and `where [path]`.
Nothing is fetched from the network: a URL is listed, not opened. The csv is plain, so the same index works by hand.

## Alternatives considered

Routing rows written into the skill's own index is the baseline this replaces: it ties the public skill to one user's
projects. Having nothing beyond each project's own records is the floor: it works, but leaves an agent to rediscover on
every task where ESOI is applied and how projects relate.
