# Why a new technology needs a decision, not a slot

A structure that lists solutions and the ways of doing them must meet technologies it did not plan for. The wrong responses are to
force the newcomer into the nearest slot (so a metric compares things that are not alternatives) and to rebuild the structure each time
(so the records stop being a stable place to measure from). Admission is a short ladder of decisions that changes as little of the
specification as the technology allows, and writes down why when it must change more.

## The idea behind the order

The records separate what is wanted (a solution and its interface) from how it is done (the implementations) and how they are
compared (a metric). A new technology differs from what is there along exactly one of those, and the cheapest honest move changes
only that one:

- It differs in **how**: it is an arm. The specification is untouched.
- It differs in **how it is judged**: the metric gains a stage or a circumstance. The solution is untouched.
- It differs in **where it sits**: it is a stage of a composite arm, or it spans several seats. A solution is added, and the seats below are untouched.
- It differs in **what is wanted**: the interface is widened, or solutions are merged or split. This is the expensive case, and it needs a reason.

Principle 2 in [from-the-skill](from-the-skill.md) says a separate solution exists for every use case with a different definition of
best, if and only if the difference could affect the intent. That sentence is the test for adding, merging and splitting: two things
share a solution when one definition of best ranks them, and they do not when it cannot.

## A rival with no arm is information

A technology often cannot be run the day it is found. Dropping it loses the finding, and inventing an arm that fakes a result breaks
the rule that a metric must be real ([metrics-must-be-real](metrics-must-be-real.md)). The middle path is an implementation record with no
code. The leaderboard lists it as not measured, so what has been left out stays on the page until someone builds it or decides it is not
worth building, and `esoi records sync` turns the record into an arm the moment its code is declared.

## Why a justified change is recorded in the solution

A change to the specification outlives the commit that made it. Months later nobody remembers why `search` has a reranker under it
or why two solutions became one. The reason goes into the `knowledge` of the solution it concerns (the template's field for what informs
a solution's definition), dated, as "what changed, because why". An empty reason is refused, because a change nobody can explain is the
kind that structure exists to prevent.

## What stays fixed

Admission never edits `selected`, never writes code and never lowers a floor. The default changes only when a metric moves it, and a
change to the specification passes the same checks as any other (`esoi check`, the coherence of the solutions). How to do each step is in
[Admit a technology that does not fit the structure](../how-to/admit-a-technology-that-does-not-fit.md).
