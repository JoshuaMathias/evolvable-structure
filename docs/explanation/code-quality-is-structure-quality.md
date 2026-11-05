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
| Scope | 0.20 | every arm implements every member of its solution's Protocol with matching parameters and a body that is more than a stub (`pass`, `...`, `raise NotImplementedError`), under a solution id that exists (Protocols and base classes of adopted libraries and installed packages count); every arm does work of its own instead of handing each call on unchanged; a folder declares few Protocols; the arms of one solution share one purpose (the word-overlap measure of rules S48 and S49) |
| Coupling | 0.20 | the share of cross-solution imports that land on a declared entry point or on the project's shared kernel (both rules below); import cycles; a library that names a consumer the project declares; at stage two, files that change together without an import |
| Size and cohesion | 0.15 | function lines, module lines and decision points (McCabe's complexity) inside their budgets, graded by how far over a part goes; files per folder, solutions per intent and depth inside their budgets |
| Reuse and duplication | 0.15 | the share of code copied between files, by token windows, scored on the graded curve (1 - copied) cubed and reported as boilerplate shared by four or more files (a table-driven helper removes it) and accidental clones |
| Behavior preserved | 0.15 | a contract test or shared case set that runs every arm of a solution with several |
| Flow fidelity | 0.10 | the coherence gate's precision and coverage for each intent (rule S38) |
| Public surface | 0.05 | the share of a solution's exported names that another solution uses, and the share of each used Protocol's members that a caller uses |

Each dimension's parts are joined by a geometric mean, so one part that fails outright pulls its dimension down instead of being averaged away. The
dimensions are joined by the weights above, fixed before any alternative is scored. A dimension that a project gives nothing to measure (no records,
no solution with two arms) is reported as not measured and left out of the mean, with the weight measured stated, so a missing dimension is never
counted as perfect.

There is no pass mark. The report shows a reference line instead, the lowest balanced number among the structures that were reviewed and kept in the
repositories measured when it was set (the derivation is in `esoi/structure/structure_quality/balance.py`). A dimension under 0.60 is named as weak in
the report: a floor that makes a collapsed dimension visible, never a mark that fails a project or excludes an arm (rule S45).

## The shared kernel is not coupling

Every repository measured had its coupling at 0.09 to 0.48, and most of what was left after front doors were excluded was imports of a few widely
shared modules: a configuration module imported from 93 places, a records registry from 78, an error module from 69, a storage base from 371. Is that
coupling, or a healthy shared kernel? The answer came from the history, not from taste. For every import that reached past an entry point, the
question was how often the importer changed in the same commit as the module it imports (last 400 commits, files modified in place, so moves do not
count):

| Repository | Kernel module, names two or more units take | Kernel module, a name only one unit takes | Other reach-ins | Imports through declared entries |
|---|---|---|---|---|
| records library | 3 percent (8 of 240) | 15 percent (4 of 27) | 11 percent (23 of 218) | 6 percent (1 of 17) |
| hub library | 19 percent (14 of 73) | 50 percent (2 of 4) | 47 percent (7 of 15) | 22 percent (25 of 114) |
| web backend | 1.4 percent (16 of 1152) | 6 percent (3 of 48) | 6.4 percent (690 of 10766) | 5 percent (1 of 20) |
| orchestration runner | too few changes to say (2 of 8): its kernels were moved weeks ago | | 9.5 percent (47 of 495) | 12 percent (56 of 459) |

An import of a shared kernel ripples about as rarely as an import through a declared entry, and three to five times less often than a reach into
another solution's inside. So the metric counts it as clean, under a rule strict enough that nothing can be passed off as a kernel (`foundation.py`):

- **many depend on it**: at least three other units import it;
- **it is stable**: its instability, fan-out over fan-in plus fan-out counted in units (Martin), is at most 0.2;
- **it depends on no solution**: every module of another unit in its import closure, lazy imports included, is itself a kernel or a declared entry,
  found as a fixed point (the stable and acyclic dependencies principles), so a module that reaches up into a solution, directly or through a
  helper, is never a kernel;
- **each name it gives is shared**: an import is clean only when every name it takes is taken by two or more units (the common reuse principle). A
  name one unit alone takes belongs in that unit, and the history agrees: such imports changed with their target 15 to 50 percent of the time.

An import of a kernel is also left out of the cycle graph: a kernel's own imports reach only other kernels, so no file-level cycle can pass through
it. The report names the kernel modules it found after the coupling line, so a reviewer can see exactly what was excused. In the web backend the
storage base (1376 lines, imported 371 times) is still a reach-in, correctly: it lazily imports services that import solutions, so it depends on
them, and the offender says so.

## Gaming moves, tested

Each move was written as a small project with its expected order set before it was scored. All are cases of the metric (`SQ-013`, `SQ-026` to
`SQ-041`) except the last, which shows a limit.

| Move | Before this change | Now |
|---|---|---|
| Cut the code into tiny files | caught (coupling, reuse and surface pay) | caught |
| Meet a fat interface with stub methods | passed: a stub counted as an implementation | caught by scope (a stub implements nothing) |
| A fat interface whose members no caller uses | passed | caught by surface (members callers use) |
| Hide a reach-in behind `import *` in the unit's own package | passed | caught by coupling (the star is followed) |
| Re-export a unit's inside by name in its `__init__.py` | flagged as coupling only when no package `__init__.py` sat above it | coupling clean either way (PEP 8 makes a package's `__init__` its interface); surface charges the re-exports nobody uses |
| Split one solution into a chain of pass-through solutions | passed on scope, caught only by the copied wrappers | caught by scope (arms that pass every call on unchanged, Ousterhout's pass-through methods) |
| Move each unit's own code into one foundation module | n/a | caught: every name is taken by one unit, so it is not a shared kernel |
| A widely imported module that imports a solution | n/a | caught: not a kernel |
| Delete the hard code | the number rises | the number still rises: a static score cannot see deleted behavior |

## Size is graded, and complexity is part of it

A count of functions over budget treats a 5549-line function and a 101-line one alike, so a web backend with one of the former scored 0.97 on
functions. Size now counts the lines over the budget against all function lines (outermost functions only, so nothing is counted twice), and the
same for module lines. Cyclomatic complexity was added as a third graded part (budget 10, McCabe's own limit): on the four repositories it ranked
with function length at 0.70 to 0.81, and 1.5 to 3.2 percent of functions were over 20 while under the length budget (an 83-line function with
complexity 68), so it carries information length does not. Nesting depth (1.0 to 1.7 percent of functions flagged beyond what length flags, and it
moves with complexity) and parameter count (1.0 to 1.6 percent) were measured and not added: too little beyond the parts already there.

## What was considered and not changed

- **Behavior on repositories with no arms.** Reading which units a test imports was tried as a general stand-in; it reached 35 to 42 percent of files on
  all four repositories, including one whose tests run its commands end to end, so it measures test style, not held behavior. Behavior stays
  measured where there are solutions of two or more arms and is reported as not measured elsewhere.
- **Copies of an adopted library's code.** The adoption commits in the history removed a parallel implementation that shared no 30-token window with
  the library, so counting token clones across libraries would not have seen it. Duplication stays token windows within the project.
- **A fold across dimensions that lets one collapsed dimension sink the number.** Before the kernel change coupling sat near 0.1 on every repository;
  a geometric fold would have made that one noisy dimension the number. The weighted mean stays, and the weak list names a collapsed dimension.
- **The weights.** They are a judgement of which failures cost most, not fitted: nine history pairs cannot fit seven weights. They are unchanged.

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
when the number holds or rises, and when it falls the commit says what the number does not see. The standard that shows this rule when solution records or
interfaces are edited is `esoi/standards/restructure-by-structure-quality.md`.

### The scorer against real histories (2026-11-05, stage 1, flow measured)

Each row is a restructuring whose expected direction a reviewer wrote before looking at the number; every pair is a real commit or a run of commits
found in the history (`git log -S` located the commit that removed the interfaces the repair restored). Three earlier rows used guessed ranges that
mixed unrelated work; they are replaced below.

| Restructuring | Commits | Reviewer expects | Previous scorer | This scorer | Agrees |
|---|---|---|---|---|---|
| Runner: interfaces written first, one per solution | one commit | up | 0.780 to 0.789 | 0.786 to 0.793 | yes |
| Runner: 81 solutions merged to 44 | the four commits of the merge | down | 0.789 to 0.788 | 0.793 to 0.792 | too close to call: scope fell 0.108 (arms left off their interfaces) while solutions per intent and flow improved, because the merge also consolidated |
| Runner: the repair that restored 17 solutions with their interfaces | one commit | up | 0.799 to 0.809 | 0.805 to 0.813 | yes |
| Runner: a flat layout moved into five containers | one commit | up | 0.750 to 0.774 | 0.767 to 0.780 | yes |
| Runner: its own due and order arithmetic replaced by calls to a library's solutions | one commit | up | 0.801 to 0.802 | 0.803 to 0.803 | no: flat. The removed code was a parallel implementation that shared no 30-token window with the library, so token windows cannot see it |
| Runner: an ordering arm composes the library's arm and keeps only its own rules | one commit | up | 0.802 to 0.802 | 0.803 to 0.803 | no: flat, for the same reason |
| Hub: records moved into five containers, code left in place | one commit | up | 0.650 to 0.603 | 0.691 to 0.622 | no, debatable: only the records moved, so the code the number reads got no better |
| Hub: all code moved beneath the solution it implements | one commit | up | 0.641 to 0.797 | 0.666 to 0.857 | yes |
| This library: a flat package moved into four containers | one commit | up | 0.574 to 0.674 | 0.623 to 0.741 | yes (case `SQ-025`) |

Counting a move under 0.002 as flat, both scorers agree with the reviewer on the same five of nine rows, and neither ranks a row the wrong way by more
than that. This change did not make the history agree better; what it changed is the foundation question and the gaming moves above. The history
does show what the number misses: two adoptions that removed real duplicated work score flat. The rows can be reproduced from git references with
`esoi structure-quality --compare <before> <after>`.

## What a reviewer can and cannot believe from the number

Believe: a fall in scope, coupling or surface after a change names something real, and the offenders say where; two commits of one repository measured
the same way can be ranked; a dimension under 0.60 is a real weakness of that kind.

Do not believe: that a number above the reference line means the split fits the domain; that a rise means no behavior was lost (deleting hard code
raises it); that two repositories with different dimensions measured are comparable; that an adoption which replaced a parallel implementation will
show (token windows cannot see code written twice in different words); that calls per request are any good (not measured: it needs traces). The
coupling dimension still reads 0.28 to 0.82, and in the web backend it is low because its units are its first two folders, so layering itself shows as
crossings.

## What counts as an entry point

Coupling reads imports between units (a unit is the folder of a solution's `interface.py` or `solutions.csv`). An import that crosses from one unit into
another is clean when it lands on that unit's declared entry, or on the shared kernel with names two or more units take, and an offense when it reaches
into a module that is neither. The evidence of an entry is what the project already declares:

- the unit's `interface.py` (a Protocol is the declared entry of a solution) and the unit's own `__init__.py`, for the names it names;
- the module an `implementations.csv` record names in `filepath` (the entry call's code), and a module that declares a `@solution` or `@implementation`;
- a name that a project's front door re-exports **only when the name resolves to one of the above**.

A project's front door is its public API module: a file called `api.py`, or the top package's `__init__.py` when that folder is not itself a solution's.
It exists to expose the parts, so it is not a unit that reaches into others: what it imports is not counted as a cross-solution call and does not enter
the cycle graph. A unit that imports a name from a front door is followed through the re-export to the module that defines it, and if that module is not
an entry the import is a reach-in, so moving every import behind a re-export changes nothing. A name a package passes on only through `import *` is
followed the same way. A `run("<id>")` call is not an import and is never an offense.

## Where it enters the work

Structure Quality is a solution of the Structure container. Structure Check calls it through the advisory rules S54 to S59 (one per dimension, flow
fidelity being S38), so a finding reaches the author when the change is made; the rules inform and never block, and the fix is at the source. The
review of scoping also belongs before code exists, so [the order of building](the-order-of-building.md) asks for it when interfaces are written.

## Grounding

- Parnas, "On the criteria to be used in decomposing systems into modules" (CACM, 1972): a module hides a decision; a reach-in defeats that.
- Martin, *Agile Software Development: Principles, Patterns, and Practices* (2002): instability, and the stable dependencies, acyclic dependencies, common reuse and interface segregation principles.
- Evans, *Domain-Driven Design* (2003): the shared kernel, a small part that several parts agree to share.
- McCabe, "A complexity measure" (IEEE TSE, 1976): decision points per function, limit 10.
- Jay et al., "Cyclomatic complexity and lines of code" (JSEA, 2009), and Landman et al. (ICSME, 2014): complexity and length correlate, with wide variance, so both are read.
- Ousterhout, *A Philosophy of Software Design* (2018): deep modules, and the pass-through method as the sign of a split with no job of its own.
- Gall, Hajek and Jazayeri (ICSM, 1998) and Zimmermann et al. (IEEE TSE, 2005): logical coupling from files that change together.
- PEP 8: a package's `__init__` that exposes its submodules is its public interface.
- Conway, "How do committees invent?" (1968): the structure follows the organization that builds it, which is why a metric reads the code and not the plan.

How to run it and read the report: [measure structure quality](../how-to/measure-structure-quality.md).
