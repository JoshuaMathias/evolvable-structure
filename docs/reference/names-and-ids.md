# Names and ids: the name leads, the id is the handle

Every record of ESOI has an `id` and most have a `name`. They do different jobs.

| | Job | Example |
|---|---|---|
| `name` | the human-readable label a person says, and the one every generated page, table, diagram and message **leads** with | `Mind`, `Card store` |
| `id` | the stable handle: what commands, links, `uses_solution_ids` and waivers write, never reworded | `mind`, `card-store` |

## What esoi does with them

- **Tables** (README solutions, implementations, metrics, ideals, problems, arm-folder pages, the evidence table) have the name as the
  first column and the id after it as a code-font handle column or suffix: `Mind` then `` `mind` ``, or ``Mind (`mind`)`` in a list.
- **Headings and links** use names; the id follows in parentheses.
- **Diagrams** label each node with the name as the headline and the id as a small italic second line. A name that is only its id is shown
  once; the id is never repeated as `id: name`. Edge labels are the provider's `outputs`, unchanged.
- **The coherence paragraph is written in names**: "The Mind asks Science for evidence ...". The check recognises a solution by its name
  (a whole phrase, any case, any spacing) as well as by its id. A name that appears only inside the longer name of another solution
  (`Mind` inside `Mind and body`) names the longer one. Ids are optional in the paragraph.
- **Command-line output** that a person reads (the leaderboard's "by solution" lines, the evidence table) says `Name (id)`. Where a
  command needs copy-paste (`esoi run <component> --impl <arm>`, a waiver key, a finding's record id) the exact id is printed, because
  the id is the argument.

## Rule S46

Advisory, never a failure: a record's `name` that is missing, equals its own id (or the arm part of an implementation id), is the id
plus a suffix or after a colon (`mind: core`), or is written kebab-case or snake_case (`card_store`) is a handle, not a name. The fix
is to write the human name. Waive as the record id.

## Where this is not yet true

Ids still print where they are the argument or the only identifier: the leaderboard's component and arm lines (`card_store (selected:
local_card_store)`, which are folder and file names for `esoi run`), finding keys for waivers, `uses_solution_ids`, and sheet tabs of the
tracker. A record with no name is shown by its id.
