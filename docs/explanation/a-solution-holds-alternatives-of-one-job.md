# A solution holds alternatives that do the same job

Joshua's lesson: "A solution is a container for alternatives that do the SAME job. If a general solution's implementations serve
different purposes or very different specificity (example: a solution named Acting whose arms are a one-call file edit, an MCP write
and Claude Code runners), the solution is mis-defined: read the implementation list for purpose and specificity when defining or
reviewing a solution; split by purpose (a general solution with general arms, specific solutions nested beneath or composed by it,
optionally routed cheapest-first), and name which general alternatives are missing."

## Why it matters

The selection rule picks the best alternative of a solution on its one metric. That only means something when the arms compete for
the same job. A one-call file edit and a coding-agent runner do not: one is cheap and narrow, the other is slow and general, so a single
leaderboard either crowns the narrow one for the cases it can do or hides it behind the general one. Either way the number answers no
question a person has.

## How to read a solution

Read the implementation list, one arm at a time, and ask two questions of each:

1. **Purpose.** Is it for the solution's purpose, or for a neighbouring one (writing a file, versus carrying out a goal)?
2. **Specificity.** Is it as general as the others, or does it only serve a slice of the cases?

If the answers differ across arms, split by purpose. Give the general job a **general solution** with general arms (the ways anyone
could do it), and give each specific job its own solution, nested beneath it or composed by it. The general solution may route
cheapest-first: try the specific solutions that can serve the case, and fall through to a general arm. Then name the general
alternatives that are missing: a general solution with only specific arms has no answer for the cases they do not cover.

## When

When defining a solution (step 11 of the steps), and when reviewing one (step 15): read the implementation list for purpose and
specificity before reading anything else. esoi does not check this: grouping arms by what their descriptions say is a judgement, and
a word-overlap heuristic over names and descriptions would flag solutions whose arms are merely described differently, so there is no
rule for it, only this page and the review step.

See also [extend before adding a solution](extend-before-adding-a-solution.md), [what belongs where](what-belongs-where.md) and [when to create a sub-intent](when-to-create-a-sub-intent.md).
