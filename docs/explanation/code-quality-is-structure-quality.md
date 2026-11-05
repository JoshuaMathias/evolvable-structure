# Code quality is structure quality

Joshua asked what guidance, approach or metric ESOI can define so that it ensures high-quality coding in terms of proper solution scoping and
modularity across different dimensions. The answer is that most of what makes code good to change is not inside any one file: it is how the work
is divided between files and solutions. ESOI measures that division as one balanced number, **Structure Quality**, and names the worst parts so
a person or an agent knows where to cut.

## What goes wrong

The incidents are generic shapes, seen in more than one repository:

- a package tree that grew to about a thousand files in one folder;
- a list of 74 solution records whose code held 33 functions over 150 lines;
- a merge that stripped interfaces, so a family of arms implemented none of the solution's methods;
- a library that came to name its one consumer;
- the same due-date arithmetic written out in six places;
- a refactor that deleted behavior production still used, because nothing held the arms to one contract.

Line and file limits catch the first two. None of them sees the rest, because those faults sit between files.

## Seven dimensions, one number

| Dimension | Weight | What it reads |
|---|---|---|
| Scope | 0.20 | every arm implements every member of its solution's Protocol with matching parameters under a solution id that exists (Protocols and base classes of adopted libraries and installed packages count); a folder declares few Protocols; the arms of one solution share one purpose (the word-overlap measure of rules S48 and S49) |
| Coupling | 0.20 | the share of cross-solution imports that land on a declared entry point; import cycles; a library that names a consumer the project declares; at stage two, files that change together without an import |
| Size and cohesion | 0.15 | functions, modules, files per folder, solutions per intent and depth inside their budgets |
| Reuse and duplication | 0.15 | the share of code copied between files, by token windows, scored on the graded curve (1 - copied) cubed and reported as boilerplate shared by four or more files (a table-driven helper removes it) and accidental clones |
| Behavior preserved | 0.15 | a contract test or shared case set that runs every arm of a solution with several |
| Flow fidelity | 0.10 | the coherence gate's precision and coverage for each intent (rule S38) |
| Public surface | 0.05 | the share of a solution's exported names that another solution uses |

Each dimension is a share of items inside a budget, joined by a geometric mean, so one part that fails outright pulls its dimension down instead of
being averaged away. The dimensions are joined by the weights above, which are fixed before any alternative is scored. A dimension that a project
gives nothing to measure (no records, no interfaces) is reported as not measured and left out of the mean, with the weight measured stated, so a
missing dimension is never counted as perfect. The report names the dimensions measured and the ones not, and says their weight is shared out in proportion.

There is no pass mark. The report shows a reference line instead, the lowest balanced number among the structures that were reviewed and kept in the repositories measured when it was set (the derivation is in `esoi/structure/structure_quality/balance.py`), and calls a project at or below it only that. Calls per request, the symptom of duplicated work at run time, is not a dimension: it needs a trace of real requests, and no trace format exists in this library; a consumer that records one can add it as cases of its own metric.

## Why no single dimension can win

Shrinking files is the easy way to look good. It raises the size score and costs everything else: a project cut into tiny files has callers
reaching into each piece, the same boilerplate in each, and exports nobody uses. The metric's cases include exactly that shape, and a comparison
case needs the balanced real structure to score above the same project cut into tiny files, while a scorer that reads file size alone scores them the
other way round. This is rule S45's lesson in this domain: a trivial winner means the number lacks a factor
([a cascade runs one criterion](a-cascade-runs-one-criterion.md)).

## A cascade at rising fidelity

Every stage reports the same number.

1. **Static.** Free, seconds, no model: the AST and the records.
2. **History.** Free: `git log --name-only` over a bounded window, with a minimum support and confidence, finds files in different solutions that
   always change together without an import joining them. That is esoi's own problem of a change missed, measured instead of guessed.
3. **Expert review.** Paid and rare: an expert model reads an outline and judges the scoping against labelled cases. It is specified and costed, and runs
   only with approval ([when metrics are run](when-metrics-are-run.md)).

Cases are small projects of the incident shapes above, each tagged with its source; kinds of cases are sources of the one metric, not stages.
A consumer builds on it with `[builds_on]`, tightens the budgets and adds its own cases, and keeps no copy of the scorer
([a metric builds on its foundation](a-metric-builds-on-its-foundation.md)).

## A restructuring is an alternative structure

A merge, a split, an adoption, an interface change and a moved module each change the structure, so each is measured like any alternative: the number
before and after (`esoi structure-quality --compare <before> <after>`), the offenders fixed and introduced, and the per-solution deltas. The change is kept only
when the number holds or rises, and when it falls the commit says what the number does not see. The scorer was checked against real histories as well as
invented cases: the known improvements (a flat package moved into containers, a merge that stripped interfaces repaired) score higher after, and the
merge that stripped them scores lower than before it. The standard that shows this rule when solution records or interfaces are edited is
`esoi/standards/restructure-by-structure-quality.md`.

### The scorer against real histories (2026-11-05, stage 1, flow measured)

Eighteen invented cases written with the scorer prove little, so the scorer was run on checkouts from the git history of three repositories on one
machine: an orchestration runner of about 1100 files, a hub library of about 400 files and this library. Each row is a restructuring a reviewer judged
before looking at the number. The order the reviewer expected is the order the scorer gave in every row but two, and both of those are debatable.

| Restructuring | Before | After | Reviewer expects | Agrees |
|---|---|---|---|---|
| Runner: interfaces written first, one per solution | 0.781 | 0.790 | up | yes |
| Runner: 81 solutions merged to 44, arms left off their interfaces | 0.790 | 0.766 | down | yes |
| Runner: the repair that restored the interfaces | 0.766 | 0.813 | up | yes |
| Runner: a flat layout moved into five containers | 0.747 | 0.775 | up | yes |
| Runner: later records and adoption work on the repaired structure | 0.813 | 0.806 | up | no, debatable: it adopted solutions of a library whose flow the code shows less strongly (flow fell from 0.91 to 0.82) while scope rose; the commits changed records more than structure |
| Hub: records moved into five containers, code left in place | 0.640 | 0.599 | up | no, debatable: only the records moved, so the code structure the number reads got no better and fewer folders hold more Protocols |
| Hub: all code moved beneath the solution it implements | 0.637 | 0.796 | up | yes |
| This library: a flat package moved into four containers, one folder per solution | 0.574 | 0.674 | up | yes |

The merge that stripped interfaces scores below the structure before it and the repair above both, which is the ordering that mattered. The history
also showed three faults in the first version of the scorer, fixed since: the reuse dimension reached zero at 15 percent copied code on every large
repository, so no real improvement could show (it is now a graded curve); Protocols and base classes of an adopted library were invisible, so arms of
adopted solutions were called off their interface; and a Protocol reached only through the front door (`run("id")`) was called an unused export.
The rows can be reproduced from git references with `esoi structure-quality --compare <before> <after>`; the library's own row is a case of the
scorer's metric (`SQ-025`), checked out from this repository's history.

Where the number cannot be trusted: coupling scored 0.20 to 0.56 on all three kept structures because most imports of another solution land on a module inside
it, not on its `interface.py` or `__init__.py`; that is the library's own style as much as a fault, so treat the coupling offenders as a to-do list and the
dimension as a way to compare two structures of one repository, not two repositories. The reference line (0.68) is the lowest of the three kept structures.

## Where it enters the work

Structure Quality is a solution of the Structure container. Structure Check calls it through the advisory rules S54 to S59 (one per dimension, flow
fidelity being S38), so a finding reaches the author when the change is made; the rules inform and never block, and the fix is at the source. The
review of scoping also belongs before code exists, so [the order of building](the-order-of-building.md) asks for it when interfaces are written.

How to run it: [measure structure quality](../how-to/measure-structure-quality.md).
