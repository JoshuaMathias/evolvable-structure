# How the records connect

The five types form a network. Each template ends with a "Connects to" line, quoted from the author's template; this page
describes how those links are written down as columns in record files.

| Record | Links it carries |
|---|---|
| Problem | `solution_ids` it is addressed by, `ideal_ids` that oppose it |
| Ideal | `problem_ids` it opposes |
| Solution | `problem_ids` and `ideal_ids` it serves, `metric_ids` that measure it, its `implementations`, and `selected` |
| Implementation | the `solution_id` it carries out, and the `path` of what was built |
| Metric | the `solution_ids` it measures, and the `command` that produces its record |

## Links agree on both sides

If a solution lists a problem, that problem lists the solution. Agreement on both sides is cheap to check and catches
the most common drift: a record renamed or deleted on one side only. Every problem has at least one solution and one
ideal; every ideal opposes at least one problem; every solution has one or more ideals (its own or its parent's) and a
metric. The mapping is not one-to-one in either direction: one problem can need several solutions, and one solution can
address several problems.

## Placement

A second map answers a different question: which files serve which solution. It is a table of components, each with a
set of path patterns, a role, and the solutions it serves. Every file belongs to exactly one component, and a component
that serves no solution is a sign the code should go. This is how "nothing exists outside a solution" is made checkable.

## Results

Measured numbers are not part of the records. They live in a results log with one row per run: the component and
implementation, the cases passed out of cases run, the cost, the commit, and a hash of the case files. The leaderboard
reads the log; the records name only which implementation is selected and why.
