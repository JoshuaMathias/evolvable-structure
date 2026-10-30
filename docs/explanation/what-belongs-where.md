# What belongs in the ESOI library and what stays in an application

An application that adopts ESOI keeps its own records and its own domain. The library holds only what any adopter could use.
Without this line, general machinery gets built inside whichever application needed it first and is later copied by the next.

## The test

> Would an adopter that has nothing to do with the application's domain need this? Then it belongs in the library.

Say the domain out loud for the thing in front of you: "an AI hub", "a card store", "a model tier". If you can remove those
words and the code still describes something a website, a data pipeline or a course would want, it is general.

## Where things go

| Belongs in the ESOI library (`esoi`) | Stays in the application |
|---|---|
| Name validation, and the rule that configuration carries names, never import paths | The names themselves: its solution ids and implementation names |
| Safe loading of a packaged arm: prefix check and a location check inside the package folder | The packaged records and snapshot it ships |
| Name-based lookup across solutions, so one solution can depend on another without importing it | Which solutions exist, as Protocol classes, and what their methods mean |
| Reading needs from typed constructor parameters and checking them against `uses_solution_ids` | The arms (implementations) of its solutions and their third-party libraries |
| Building in dependency order, injecting needs and options, a frozen result with a reason line per solution | Its configuration values: which arm, which options, its prompts, keys and settings |
| Startup failure on a cycle or an unmet need, naming the chain | Domain logic: scoring, selection of a model tier, risk rules, storage, search |
| The cascade (explicit name, selections, default) and late binding through `esoi.runtime` | The decision of which arm is best for its domain, as a metric with real cases |
| Packaging a pruned selection (a snapshot for an installed copy) | Adapters to its own products and services |
| Reading a repository's records for a task: the solution it serves, its next milestone and its metric; reading a metric's value; keeping the value before and after a piece of work | Which workers, tools and briefs an application hands the work to, and the words it asks of them |
| Circumstances as conditions on case fields and on a run, derived slice rows, a per-case log and `name@key=value` variants | Which circumstances exist, their thresholds and the case fields that carry them |
| Checks over records and declarations that any adopter could run | Checks whose subject is its own domain (for example, vendor names in its core code) |

## Examples

An adopter that moved its own generic assembly code here is told in [examples/adopters.md](../../examples/adopters.md).

## What an application may keep

Its records (`esoi/*.csv`), its Protocol classes and arms, its configuration, its domain logic, and thin names that bind the
library to its package (for example, one `Assembler` object and the public names it exports). A thin binding is a few lines.
If an application module grows a function that would read the same with the domain words removed, it has drifted: move it.

## When unsure

Do not decide alone, and do not build it in the application "for now": for now becomes permanent. Describe the capability and
where you would put it, and propose the change to the library's owner. Anyone may open an issue; only the owner or an AI acting on the
owner's prompt changes the library.

## Keeping it true

Each adopting application can add a small test that fails when one of its modules defines a function the library already
provides (a name validator, a dependency-graph walk). The library's own records say which part serves which solution: a
new general part is a component in `esoi/components.csv` that serves a solution in `esoi/solutions.csv`.
