# Adopting solutions from a library

An application often needs solutions a shared library of ESOI records already defines. Picture an application adopting a shared hub of AI
solutions: the hub defines how to route a request to a model, how to remember a conversation, how to judge an answer. The application needs
all of that, and it also needs things only it has: its own users, its own data, its own metrics. If it copies the hub's solution records, it
ends up with about seventy-four records of which many restate the hub's. Each copy has its own vision, problems and ideals, so the
structure is large, two places say the same thing in different words, and the copies drift as the hub changes.

## The principle

A solution is defined once, in the repository that owns the job. A repository that needs the same job **adopts** the solution: it records a
reference to the library's solution and nothing else the library already says. What the application adds is only what differs: its own
arms (implementations) that compete under the library's metric, its own binding and configuration, and the solutions that are its own.

This is [override only what differs](override-only-what-differs.md) applied to records, with [a metric building on its
foundation](a-metric-builds-on-its-foundation.md) as the way the two measure together and [dependence by name](cross-dependency-by-name.md)
as the way the reference is written.

## Three kinds of record

| Kind | What the library has | What the application records | Where its vision, problems, ideals and role come from |
|---|---|---|---|
| **Adopted** | The solution is defined | A reference (`adopts`), its binding, and any arms of its own | The library, never copied |
| **Specialized** | A general solution that needs the application's data to do its job | A full record with its own short vision, naming the library solution it specializes (`specializes`) | Its own, scoped to the one part the library cannot know |
| **Own** | Nothing for this job | Full records: problems, ideals, role, metrics and code | Its own |

### The test for choosing

Ask of the job in front of you: would a stranger's use of the library need this?

1. **Yes, and the library already has it**: adopt it. Do not write a vision, problems or ideals.
2. **It is the library's job but needs this application's data** (its documents, its users, its vocabulary): specialize it. The specialized
   solution says in one short sentence what this application adds, and delegates the general part to the adopted solution.
3. **Only this application has the need**: it is your own solution. It carries its own metrics, customization and code.

An own solution that proves general, because a second application wants it, is proposed back to the library, which then owns it and the
application adopts it. Until then it stays yours.

## What an adopted record holds

An adopted solution is one row in the application's `solutions.csv`. It has an id, a name and an `adopts` cell written
`@<library>/<solution id>`, the same form a record already uses to name another project's solution in `uses_solution_ids`. Everything the
library defines stays empty in the row: the description, purpose, approach, scope, milestones, knowledge, measures of success, problems,
ideals, delegation and change driver. The row may carry what is the application's: the implementations it adds, which one is selected,
and the interface name.

Which repository `<library>` means is configuration, not a record: `[adopts.<library>] repo = "../hub"` in `esoi.toml`, with an optional
`url` that the generated pages link to instead of a relative path.

### How the application's own arms register

An arm the application adds to an adopted solution is an ordinary row in `implementations.csv` whose `solution_id` is the adopted
solution. Its code declares `@implementation("<the library's solution id>", "<arm name>")` and follows the library's interface, because the
library's metric and selection call it through that interface. It competes with the library's own arms on the library's metric: the
application does not write a second set of cases for a job the library already measures.

### How the application's metric builds on the library's

The metric that scores the adopted solution in the application is declared with `[builds_on]`, so the library's recorded per-case results
are reused when current and the application runs only the cases that are its own (its real requests, its own data). The application's
number is one balanced score at rising fidelity, never a second criterion. The rules of that mechanism are in [A metric builds on its
foundation](a-metric-builds-on-its-foundation.md); adoption adds only the record that says which solution the metric is about.

## What the checks say

`esoi check` informs (rule S53) and never fails:

- an adoption that does not resolve: the library is not configured, cannot be read, or has no such solution;
- an adopted record that restates what the library already says (a description, problems or ideals of its own);
- an own solution whose purpose and description say the same job as a library solution, with the next action: adopt it, specialize it, or
  record why the job differs;
- an arm under an adopted solution whose code does not declare the library's solution id, so the library's interface does not reach it.

The generated page of an intent shows an adopted solution as a link to the library's page with the library's own description of it, read
from the library at generation time and never written into the application's records. Specialized and own solutions appear as any
solution does.

## What this does not do

It does not copy, vendor or snapshot the library's records. It does not decide that two solutions are the same job: a person does, and
the check only points at likely cases. It does not make the library a dependency of the application's runtime: adoption is about records,
and how the code reaches the library's arms is [assembly by name](cross-dependency-by-name.md).

How to adopt a solution is in [Adopt a solution from a library](../how-to/adopt-a-solution-from-a-library.md). What is general and what
stays in an application is in [What belongs where](what-belongs-where.md).
