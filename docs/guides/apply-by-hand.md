# Apply ESOI by hand

No tools are needed. A folder of text files and a spreadsheet are enough, or a copy of the
[Project Documentation board](../explanation/project-documentation-board.md). Plan on about an hour for the first pass.

This guide is a short first pass through [the steps](../../skill/evolvable-structure/steps.md): section 1 covers steps
1 to 10 in brief, section 2 steps 11, 12 and 16, section 3 steps 13, 14, 17 and 18, section 4 step 19, and section 5 steps
20 to 23. It leaves out step 15 (review from other perspectives), so do that before relying on the result. When you
have more than an hour, follow the steps themselves.

## 1. Write the intent (about twenty minutes)

Copy [intent.md](../templates/intent.md) and give the intent a name and a vision statement in present tense ("The
world is ..."). Then write one to three problems and ideals, one top solution that everything falls under, the
alternative ways of carrying it out as implementations, and one or two metrics. Use short ids such as `prob-slow-reports`
and `ideal-fast-answers`. Keep them together in one folder: the folder is the intent.

## 2. Write the first detailed solution (about twenty minutes)

Start coarse. Give a part its own solution only when it has a different definition of best that could impact the success of
the intent, and a sub-intent only for an opportunity (see [when-to-create-a-sub-intent.md](../explanation/when-to-create-a-sub-intent.md)).

Pick one part of the work. Copy [solution.md](../templates/solution.md) and answer every question. Copy
[problem.md](../templates/problem.md), [ideal.md](../templates/ideal.md), [implementation.md](../templates/implementation.md)
and [metric.md](../templates/metric.md) as needed, once per record. Link them: the solution names its problems, ideals,
metric and implementations, and each of those names the solution back. If the part builds on a solution somewhere else,
write that solution's id on the implementation.

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
- Review the intent's vision statement, problems and ideals when direction changes, and the results when something is rerun.
- Use [review-sheet.md](../templates/review-sheet.md) to lay the records out as a spreadsheet for someone else to review.
- Copy [repository-standard.md](../templates/repository-standard.md) once the shape has settled, and keep it short.

When the files multiply, move to [the tools](apply-with-tools.md), which check that links agree, that every file has an
owner, and that results are fresh.
