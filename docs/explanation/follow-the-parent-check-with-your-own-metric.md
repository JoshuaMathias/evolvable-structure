# Follow the parent, check with your own metric

A hub measures its solutions and ships the best arm of each as a default. A child that builds on the hub has parts of its own and
often a cheaper or more specific metric. Two things go wrong between them. A child that overrides a default never looks at the
override again, so the override outlives its reason. A child that inherits a default sees the hub's improvement only if somebody reads
the hub's records.

## Why the child's metric decides

The hub's result describes the hub's cases. Whether the hub's new arm suits the child is a question about the child's cases, and the
child already has an answer for it when its own metric holds a row for that arm. So `esoi follow` never takes the parent's word:
it reads the parent's current selection only to know which arm to look up, and it judges that arm with the child's rows and the child's
selection rule. A child that requires significance before switching (`[switching]`) is held to it, and one that takes the highest
result is not made to wait.

That is also why the child benefits automatically. Most of the time the parent's arm holds on the child's metric (`ADOPT`), and the
advice is to follow it. Where it does not (`KEEP`), the child has the numbers for the reason it records in `overrides.csv`.

## Findings inform, never block

The command prints advice and exits 0. It neither changes a lock or a `selected` cell nor orders a run. A missing row is the one
place it points at spending, so it says what the row costs: an offline arm is free and may be recorded with `--run-free`, and a paid arm
is only listed. A paid arm needs a cost estimate, a staged sample, a call budget and a person's approval, as in the
[metric run policy](when-metrics-are-run.md). Only rows whose measured code changed are called stale (the child's staleness rule),
so a quiet parent costs the child nothing to follow.

## What it builds on

No new record field. The parent's selections come from the same places the assembler's parent layer and rule S35 read
(`[parent]`, a records folder, a snapshot or an Assembler's parent chain); the lock is `esoi.lock.json`; the reasons are
`overrides.csv`; the judgment is `esoi.leaderboard.decisions`; and staleness is `esoi.staleness`. How to run it:
[Follow a parent repository's selections](../how-to/follow-a-parent-repositorys-selections.md).
