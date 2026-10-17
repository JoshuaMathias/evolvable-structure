# When to split a solution into sub-solutions

The author's principle 2, quoted from [from-the-skill.md](from-the-skill.md):

> Have a separate, defined component for every use case that has a different definition of best, if and only if the
> different definition could impact the success of the intent.
>
> - Comprehensiveness: Everything implemented falls under a solution.
> - Start with one at the top: Every project, repository, organization, big goal, etc. has a single solution which
>   encapsulates sub-solutions for more specific components.
> - When to split into sub-solutions: The resources required to create and maintain the solution infrastructure for
>   sub-solutions outweigh the potential benefits of comparing alternative implementations and clearly defining the
>   sub-solution, within the timeframe currently prioritized by the larger solution (in other words, the due date of the
>   next highest priority goal milestone).
> - Allow benefits outside hiearchy: While the above implies hierarchy, sub-solutions may be useful as dependencies or
>   sub-solutions elsewhere.

## Start with one at the top

Every project, repository, organization or big goal has a single solution, and everything implemented falls under it
or under one of its sub-solutions. Nothing sits outside a solution. Splitting is then always a question about one
existing solution: should part of it become a sub-solution of its own?

## Whether best differs

The first sentence sets two conditions, and both are required. "If and only if" works in both directions: split when both hold, and do not
split when either fails. Keeping two use cases in one solution when their best differs in a way that matters hides a
choice the metric should be making; splitting when it does not matter adds records, metrics and cases that serve
nothing.

## The two tests

**1. Is "best" defined differently for this use case?** Ask whether the use case would have a different ideal, a
different measure of success, or a different weighting of the same measures, so that a different implementation could
win. Concrete signs:

- You would write a different metric, or different cases, to judge it.
- The same metric applies, but the trade-off flips: one use case wants speed, the other accuracy.
- On the existing metric, implementations rank differently when the cases are grouped by use case. This is the
  strongest evidence, because it is measured rather than predicted.

If the same implementation would win for both, it is one solution, however different the use cases look.

**2. Could the difference affect whether the intent succeeds?** Name the consequence: something the people the intent
serves would notice, a cost that matters, a failure that would follow from using the other use case's best. If you
would pick a different implementation but the intent succeeds equally well either way, keep one solution.

## Whether it is worth it in the prioritized timeframe

Passing both tests makes a split possible, not automatic. Weigh the two sides:

- **The cost:** the resources to create and maintain the sub-solution's infrastructure: its records, its metric and
  cases, its alternative implementations, and keeping their results current.
- **The benefit:** what comparing alternative implementations and clearly defining the sub-solution would gain.

Count both within the timeframe the larger solution currently prioritizes, which is the due date of its next highest
priority goal milestone. A benefit that would only arrive after that date does not yet pay for a split; when the
resources outweigh the benefits in that window, the part stays inside the larger solution. Weigh it again when the next
milestone is set, since both sides change.

## Benefits beyond the hierarchy

Splitting implies a hierarchy, but a sub-solution can also serve elsewhere: as a dependency of another solution, or as a
sub-solution of a different parent, in this system or another. Count those uses among the benefits. A part that several
solutions would depend on often pays for its own definition sooner than a part only its parent uses.

## Often not a split

- **Different how, same best.** Two ways of doing the same thing, judged by the same measure, are two implementations
  of one solution, not two solutions.
- **Different inputs, same best.** When one implementation stays best across settings (a length, a language, a
  threshold), the difference is a parameter of one solution. It becomes a split only if a different implementation wins
  at some setting and that matters to the intent.
- **A difference nobody can name yet.** Splitting rests on a predicted or measured difference you can state, tied to the
  purpose. "It might differ someday" is not enough. The ontology is "ideal but iterative": start with the split you can
  justify now, and split further when a case or a result shows that best differs.
- **A split whose cost outweighs it in the prioritized timeframe.** See above. A structural solution is applied only
  where its disadvantages do not outweigh its advantages for this purpose and niche, and the simpler structure wins a tie.

## Signs worth checking against the tests

These suggest a split, but none decides it alone; each still has to pass both tests.

- Two groups of people want opposite trade-offs from the same part.
- Part of a solution changes at a very different rate from the rest.
- Part of a solution would be used by other solutions or another system with only new parameters (a benefit beyond the
  hierarchy).
- A result keeps being discussed as "good for these cases, bad for those".

## The right level

Too fine is as wrong as too coarse. A solution defined per case leaves too few cases to measure and multiplies records.
A solution that is too broad lets one implementation win on average while losing badly on a use case that matters. When
you place a solution in the network, write the reason: which definition of best it has that its neighbour does not.

## Merging back

The tests are applied again as things change. When two solutions' definitions of best converge, or the difference stops
mattering to the intent, merge them, keep one metric, and park the retired records rather than deleting them, so their
results and reasoning stay findable.

## How a split shows in the records

A sub-solution is a solution like any other. It names the solution or area it refines (see
[overall-and-detailed.md](overall-and-detailed.md)), carries its own metric, and adds its own problem and ideal only
when it serves a narrower difficulty than its parent. The parent can remain as the shared interface, a template or a
routing that chooses which sub-solution handles a request; the author's Solution template allows exactly that.

## An example

A team answers customer messages. Refund questions and how-to questions look like one use case, "reply to a customer".
Test 1: for refunds, best means agreeing with the refund policy every time; for how-to questions, best means complete
and quick. A reply step tuned for speed could win on how-to cases and lose on refund cases. Test 2: a wrong refund answer
costs money and trust, so the difference affects the intent. Split: two solutions, each with its own cases, sharing one
interface.

Replies in English and in Spanish fail test 1 as long as the same implementation stays best in both: language is a
parameter. If measurement later showed a different implementation winning in Spanish, and Spanish-speaking customers
were being served worse, the tests would be applied again.

## A short checklist

1. Start from the single solution at the top, or the existing solution the part falls under.
2. Write the definition of best for each candidate use case in one line. If the lines are the same, stop: one solution,
   perhaps with a parameter.
3. If they differ, name the consequence for the intent of using one use case's best for the other. If there is no
   consequence that matters, stop.
4. Weigh the resources to build and maintain the sub-solution against the benefits of comparing alternatives and
   defining it clearly, including uses outside its parent, within the timeframe to the next highest priority milestone.
   If the resources outweigh the benefits, stop for now and weigh it again at the next milestone.
5. Otherwise split, link the sub-solution to its parent (and to any other solution that depends on it), and give it a
   metric that can show the difference.
