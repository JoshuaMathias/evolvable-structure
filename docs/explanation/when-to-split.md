# When to split a solution into sub-solutions

The author's principle, quoted from [from-the-skill.md](from-the-skill.md):

> Have a separate, defined component for every use case that has a different definition of "best," if and only if the
> different definition could impact the success of the intent.

Two conditions, and both are required. "If and only if" works in both directions: split when both hold, and do not
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

## Often not a split

- **Different how, same best.** Two ways of doing the same thing, judged by the same measure, are two implementations
  of one solution, not two solutions.
- **Different inputs, same best.** When one implementation stays best across settings (a length, a language, a
  threshold), the difference is a parameter of one solution. It becomes a split only if a different implementation wins
  at some setting and that matters to the intent.
- **A difference nobody can name yet.** Splitting rests on a predicted or measured difference you can state, tied to the
  purpose. "It might differ someday" is not enough. The ontology is "ideal but iterative": start with the split you can
  justify now, and split further when a case or a result shows that best differs.
- **A split whose cost outweighs it.** Each solution needs its own records, metric and cases, and someone keeps them
  current. A structural solution is applied only where its disadvantages do not outweigh its advantages for this purpose
  and niche, and the simpler structure wins a tie.

## Signs worth checking against the tests

These suggest a split, but none decides it alone; each still has to pass both tests.

- Two groups of people want opposite trade-offs from the same part.
- Part of a solution changes at a very different rate from the rest.
- Part of a solution would be reused by another system with only new parameters.
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

1. Write the definition of best for each candidate use case in one line.
2. If the lines are the same, stop: one solution, perhaps with a parameter.
3. If they differ, name the consequence for the intent of using one use case's best for the other.
4. If there is no consequence that matters, stop: one solution.
5. Otherwise split, link the sub-solution to its parent, and give it a metric that can show the difference.
