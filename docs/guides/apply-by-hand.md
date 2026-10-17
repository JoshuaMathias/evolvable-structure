# Apply ESOI by hand

No tools are needed. A folder of text files and a spreadsheet are enough. Plan on about an hour for the first pass.

## 1. Write the overall network (about twenty minutes)

Copy [overall-solution-network.md](../templates/overall-solution-network.md). Write one to three problems and ideals, one
overall solution with a few areas, the alternatives to it as a whole, and one or two top metrics. Use short ids such as
`prob-slow-reports` and `ideal-fast-answers`.

## 2. Write the first detailed solution (about twenty minutes)

Pick one part of the work. Copy [solution.md](../templates/solution.md) and answer every question. Copy
[problem.md](../templates/problem.md), [ideal.md](../templates/ideal.md), [implementation.md](../templates/implementation.md)
and [metric.md](../templates/metric.md) as needed, once per record. Link them: the solution names its problems, ideals,
metric and implementations, and each of those names the solution back. Name the parent in the overall network.

## 3. Make the metric real (about twenty minutes)

Write five to ten cases: an input and what a good output looks like. Run each implementation on them, by hand if need be,
and record one row in a results table with the date, the implementation, cases passed out of cases run, the version of the
thing measured, and a short fingerprint of the case file (a file hash, or a version number you bump when cases change).
The columns are in [record-headers/results.csv](../templates/record-headers/results.csv).

## 4. Decide and write it down

Mark the implementation you chose and why: it won, it tied and you kept it for a stated reason, or it lost and you are
keeping it anyway until a named decision. Put that in `selected` and `selected_by` on the solution.

## 5. Make it a habit

- Add a row to the results table each time an implementation or the cases change.
- Review the overall network when direction changes, and the results when something is rerun.
- Use [review-sheet.md](../templates/review-sheet.md) to lay the records out as a spreadsheet for someone else to review.
- Copy [repository-standard.md](../templates/repository-standard.md) once the shape has settled, and keep it short.

When the files multiply, move to [the tools](apply-with-tools.md), which check that links agree, that every file has an
owner, and that results are fresh.
