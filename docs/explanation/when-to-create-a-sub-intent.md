# When to create a sub-intent

The hierarchy in ESOI is between intents. A project, a repository or a big goal is an intent. A part of it becomes a
sub-intent only for a reason, and "infinite hierarchy is a trap". This page says what the reason is. Whether two
use cases need separate solutions inside one intent is a different, older question, answered at the end.

The author's principle 2, quoted from [from-the-skill.md](from-the-skill.md):

> Have a separate, defined component for every use case that has a different definition of best, if and only if the
> different definition could impact the success of the intent.
>
> - Comprehensiveness: Everything implemented falls under a solution.
> - Start with one at the top: Every project, repository, organization, big goal, etc. has a single solution which
>   encapsulates sub-solutions for more specific components.
> - Note on hierarchy: An intent is like a folder containing the files of the other five specification types. The other
>   specification types do not have direct children (except as a way to elaborate on the conceptual details, such as
>   describing different areas of a problem as sub-problems) and hierarchy is in terms of intents and sub-intents.
>   Sub-intents are not directly children of intents, however. Instead, they arise as implementations of a solution in
>   the parent intent. This ensures that the role of the sub-intent is clear.
> - When to split into sub-intents: I recommend specifying a sub-intent if and only if that intent brings insights on
>   opportunities that don't emerge directly from the parent intent or solution that the sub-intent is implementing.
>   Opportunities suggest that there may be creative value in the implementation, which goes outside the scope of the
>   solution or is sufficiently meaningful to consciousness that they desire to bring focused attention into that
>   implementation to specify it further.
>     - Consider also practicality: Do the resources required to create and maintain the solution infrastructure and
>       specifications for a sub-intent outweigh the potential benefits of clearly defining the sub-intent, within the
>       timeframe currently prioritized by the larger solution (in other words, the due date of the next highest
>       priority goal milestone)? Fortunately, with AI the resources required tend to be minimal, but infinite hiearchy
>       is a trap, so every sub-intent that AI creates should be justified by an insightful opportunity.
>     - Consider groupings: Notice opportunities to break down an intent that has too many specifications for optimized
>       access patterns (analogous to working memory, but not specifically 4 items), where some clusters of problems and
>       solutions are independent as indicated by the intent's network of connections. The parent of the intent could be
>       restructured or created to improve organization based on what such clustering reveals.
> - Allow benefits outside hiearchy: While there can be hierarchy, solutions may be useful as dependencies outside its
>   containing intent. **Implementations are expected to build through connecting solution interfaces**, where such
>   solutions are available. This is the magic of ESOI: a web of interweaving dependencies refines itself over time
>   (while mitigating risk of dependency failure through solution abstractions, alternative implementations, and
>   metrics).

**A note on the quote.** The "Start with one at the top" bullet still says "sub-solutions". Read it in the current terms:
the intent has a single top solution, and everything implemented falls under it, through the top solution's
implementations, through the sub-intents those implementations become, and through the solutions they build on. The
words are the author's and are quoted as written. See [intents-and-sub-intents.md](intents-and-sub-intents.md).

## What a sub-intent is

A sub-intent is not a child of the parent intent as a whole. It arises as an **implementation of a solution** in the
parent intent. The parent's solution says what is wanted; one implementation of it turns out to be big or interesting
enough to be an intent with its own problems, solutions, ideals and metrics. That makes its role clear: it is one
alternative for that solution, and the solution's metric compares it with the others.

Implementations are essentially ideas, so an implementation can start as a sub-intent or evolve into one. Nothing is
lost either way: the implementation record stays in the parent and names the sub-intent, and the sub-intent names the
implementation it came from.

## The opportunity test

Specify a sub-intent if and only if it brings insights on opportunities that do not emerge directly from the parent
intent or from the solution it implements. An opportunity suggests creative value in the implementation that goes
outside the scope of the solution, or something meaningful enough that someone wants to give that implementation
focused attention, specify it further and iterate on its potential.

An intent brings insights on risks, uncertainties and opportunities, and each already has a home:

| Insight | Where it goes | Why that is enough |
|---|---|---|
| Risk | The disadvantages of the implementation (or of the metric) | A risk of one way of doing it is a disadvantage of that implementation |
| Uncertainty | The metric of the existing solution | Measuring is how an uncertainty is resolved |
| Opportunity | The solution, or an advantage of the implementation | An opportunity may be creative value beyond the solution's scope; only then is a sub-intent worth it |

So do not create a sub-intent because of a risk or an uncertainty alone. The three aspects of an intent are already part
of the solution and implementation definitions. An opportunity is the one that can point outside them: there may be
something here the solution does not ask for, or something that deserves its own attention.

Questions to ask:

- What opportunity does this implementation bring that the parent intent, or the solution it implements, does not
  already state? If you cannot name it, keep the implementation where it is and record the risk or uncertainty in the
  implementation's disadvantages or the solution's metric.
- Is the opportunity beyond what the solution is scoped to do, or meaningful enough that someone wants to specify the
  implementation further?

The sub-intent's `opportunity` is written down (see [intents-and-sub-intents.md](intents-and-sub-intents.md)), so the
reason survives and can be challenged later.

## Practicality

An opportunity passing the test makes a sub-intent possible, not automatic. Weigh:

- **The cost:** the resources to create and maintain the sub-intent's infrastructure and specifications: its records,
  its metrics and cases, its alternative implementations, and keeping results current.
- **The benefit:** what clearly defining the sub-intent gains.

Count both within the timeframe the larger solution currently prioritizes, which is the due date of its next highest
priority goal milestone. With AI the cost tends to be small, but infinite hierarchy is a trap, so every sub-intent an AI
creates needs an insightful opportunity written down. A benefit that arrives only after that date does not yet pay for
it; weigh again when the next milestone is set.

## Groupings

A different reason to restructure: an intent with too many specifications to find things quickly, where the network of
connections shows clusters of problems and solutions that are independent of each other. The cluster can be broken out.
This does not make the cluster a child by itself. Ask which solution in the intent the cluster implements, and break it
out as the implementation's sub-intent; or restructure the parent, or create a new one, so the clusters sit in intents of
their own. The aim is access: how many specifications a reader or an agent must hold at once, which is not exactly four.

## Benefits outside the hierarchy

A solution can be a dependency of implementations in other intents. Implementations are expected to build by connecting
solution interfaces wherever the solutions exist, so an implementation in one intent records the solutions it builds on
(`uses_solution_ids`), wherever they are in the tree. This is a web of dependencies, kept safe by solution abstractions,
alternative implementations and metrics: if a dependency fails, its metric shows it and another implementation can be
selected. Count these uses when weighing a sub-intent: a solution several implementations build on is often worth its own
intent sooner than one only its parent uses.

## Whether best differs: separate solutions inside an intent

The original principle still decides when one intent holds more than one solution: "Have a separate, defined component
for every use case that has a different definition of best, if and only if the different definition could impact the
success of the intent." Both conditions are required, in both directions: when both hold, define a separate solution;
when either fails, do not. Hiding two bests in one solution hides a choice the metric should make; separating when it does
not matter adds records, metrics and cases that serve nothing. This is not a sub-intent: two solutions in one intent
need no opportunity, only a different best.

1. **Is "best" defined differently for this use case?** You would write a different metric or different cases, the same
   metric's trade-off flips (speed against accuracy), or implementations rank differently when cases are grouped by use
   case, which is the strongest evidence because it is measured. If the same implementation wins for both, it is one
   solution.
2. **Could the difference affect whether the intent succeeds?** Name the consequence. If the intent succeeds equally well
   either way, keep one solution.

### Often not a separate solution

- **Different how, same best.** Two ways of doing one thing, judged by one measure, are two implementations.
- **Different inputs, same best.** When one implementation stays best across settings, the difference is a parameter.
- **A difference nobody can name yet.** The ontology is "ideal but iterative": start with what you can justify now.
- **A cost that outweighs it in the prioritized timeframe.** A structure is applied only where its disadvantages do not
  outweigh its advantages for this purpose and niche, and the simpler structure wins a tie.

## What stops the hierarchy

Every intent could be broken down again, so something has to say where to stop: a structure budget that keeps the
structure's own cost in view and prunes what stops paying. It is needed in every project, conceptually, to avoid an
infinite hierarchy, but not every project merits a coded implementation of it; a written rule (the weighing above, applied
at each milestone) is often enough.

## Merging back

The tests apply again as things change. When a sub-intent's opportunity turns out to be covered by its solution, or its
implementation stops deserving focused attention, fold it back into an implementation of the parent solution, keep the
parent's metric, and park the retired records rather than deleting them, so their results and reasoning stay findable.
Two solutions whose definitions of best converge are merged the same way.

## An example

A team answers customer messages. The intent has a solution, "reply to a customer". Refund questions and how-to
questions look like one use case. For refunds, best means agreeing with the refund policy every time; for how-to
questions, best means complete and quick, and a reply step tuned for speed could win one and lose the other. A wrong
refund answer costs money and trust, so the difference affects the intent: two solutions in the same intent, each with
its own cases, sharing one interface. No sub-intent yet.

Now one implementation of "reply to a customer" is an assistant that drafts replies. While building it, the team sees an
opportunity the solution never asked for: the drafts could turn repeated questions into help-centre articles and cut
questions at the source. That is creative value outside the scope of the solution, and the team wants to specify it
further. The implementation becomes a sub-intent, "Questions that answer themselves", with its own vision statement,
problems, solutions and metrics. Its drafting solution is also a dependency of an unrelated intent's implementation, which
lists it in `uses_solution_ids`.

By contrast, "the assistant sometimes quotes an outdated policy" is a risk: it goes in the implementation's
disadvantages, and "we do not know whether customers prefer long replies" is an uncertainty: it goes in the solution's
metric. Neither is a sub-intent.

## A short checklist

1. Start from the single solution at the top, or the existing solution the part falls under.
2. If two use cases have the same best, stop: one solution, perhaps with a parameter. If their best differs and it
   matters to the intent, give each its own solution inside the intent.
3. For a candidate sub-intent, write the opportunity in one line, outside what the parent intent or solution already
   states. If it is only a risk or an uncertainty, put it in the implementation's disadvantages or the solution's metric
   and stop.
4. Weigh the cost to create and maintain it against the benefit, including uses by implementations elsewhere, within the
   timeframe to the next highest priority milestone. If the cost outweighs the benefit, stop for now and weigh again at the
   next milestone.
5. Otherwise make it an implementation of the parent's solution, as a sub-intent, linking both ways; give it a metric or
   inherit the solution's, and list the solutions it builds on.
6. If an intent has grown unwieldy, look for independent clusters in its network and restructure.
