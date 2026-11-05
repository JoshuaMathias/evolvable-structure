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
| Scope | 0.20 | every arm defines the methods of its solution's Protocol; a folder declares few Protocols; the arms of one solution share one purpose (the word-overlap measure of rules S48 and S49) |
| Coupling | 0.20 | the share of cross-solution imports that land on a declared entry point; import cycles; a library that names a consumer the project declares; at stage two, files that change together without an import |
| Size and cohesion | 0.15 | functions, modules, files per folder, solutions per intent and depth inside their budgets |
| Reuse and duplication | 0.15 | the share of code copied between files, by token windows |
| Behavior preserved | 0.15 | a contract test or shared case set that runs every arm of a solution with several |
| Flow fidelity | 0.10 | the coherence gate's precision and coverage for each intent (rule S38) |
| Public surface | 0.05 | the share of a solution's exported names that another solution uses |

Each dimension is a share of items inside a budget, joined by a geometric mean, so one part that fails outright pulls its dimension down instead of
being averaged away. The dimensions are joined by the weights above, which are fixed before any alternative is scored. A dimension that a project
gives nothing to measure (no records, no interfaces) is reported as not measured and left out of the mean, with the weight measured stated, so a
missing dimension is never counted as perfect.

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

## Where it enters the work

Structure Quality is a solution of the Structure container. Structure Check calls it through the advisory rules S54 to S59 (one per dimension, flow
fidelity being S38), so a finding reaches the author when the change is made; the rules inform and never block, and the fix is at the source. The
review of scoping also belongs before code exists, so [the order of building](the-order-of-building.md) asks for it when interfaces are written.

How to run it: [measure structure quality](../how-to/measure-structure-quality.md).
