# Extend before adding a solution

A task that comes up is almost never a new solution. The solutions of an intent are its long-term jobs; a task is one occasion
that touches one of them. So extend what exists first, and create a solution only when one is genuinely missing and lasting.

## The rule

When a new behaviour is wanted, look for the existing solution whose purpose it serves and extend that:

- **Add cases** to the solution's metric, so the new situation is measured.
- **Adjust the metric**, or its cascade, when the new situation needs a factor or a cheaper first stage.
- **Add an implementation** (an arm) when the new behaviour is another way of doing the solution's job.
- **Add a flow step** in the composition arm when the behaviour is one more step in how siblings connect.

## The test for a genuinely missing solution

Create a solution only when all three hold:

1. It has a distinct purpose that no sibling holds.
2. Several alternatives could compete on one metric for that purpose.
3. It would still exist if the task that raised it were forgotten.

A one-off behaviour, a guard, a check or a step in a sibling's flow fails the test. It is an arm, a case set, a metric stage or a
flow step.

## When you do create one

Write the justification against each sibling in its record: its `purpose`, its `out_of_scope` (what it is not responsible for) and
its `delegates_to` (who owns that instead). Rule S48 reads these. A new top-level solution of a hierarchy also needs the owner's
approval: propose it as a decision rather than adding it.

## Two examples

- A check that an answer meets the goal condition it was asked for. A verifier solution already exists for judging answers, so
  the check is a new arm of it, and the situations it must catch become cases in its metric.
- A new source of data to take in. An intake solution already holds the ways of bringing data in, so the source is another arm of
  it, measured on the same cases.

See [the order of building](the-order-of-building.md), [when to create a sub-intent](when-to-create-a-sub-intent.md) and
[a solution holds alternatives of one job](a-solution-holds-alternatives-of-one-job.md).
