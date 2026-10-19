# ESOI applied to AI behaviour

The author's skill says it is not only for code: its description names "general improvements to how AI behaves, builds,
and implements business offerings to reflect Joshua's principles". Applying ESOI to an AI agent's behaviour is therefore an
part of ESOI's own intent, with the same five record types: a solution for guiding agents (`esoi-for-ai`), the solution
whose cases and arms its metric uses (`behave-by-esoi`), and the judge that grades replies (`esoi-behaviour-judge` and
`judge-esoi-behaviour`). This page says how each part maps; the records are in [structure/](../../structure/). It was once a
sub-intent of its own; it is not, because its opportunity repeated the goals and metric of `esoi-for-ai` (an uncertainty,
which a metric handles), and version history keeps the earlier records.

## The problem is behaviour that nobody can see drifting

An agent given the principles still builds a framework for a one-off fix, records a task as a problem, merges two use
cases whose best differs, or restates a rule without its condition. Correcting it in conversation fixes one reply, and the
agent starts the next session without the correction. The ideal is **principled behaviour**: the agent acts by the
principles in its own work, including holding back where structure costs more than it returns.

## The skill is an implementation

The solution `esoi-for-ai` has the implementations below, and its metric, behaviour adherence, is carried out by the
solution `behave-by-esoi`: the same cases run once per implementation (its arms), and the solution `esoi-behaviour-judge`
says how far the grading of those runs can be trusted.

The skill is not the solution, it is one way of giving an agent the principles. Others are to load it only when the task
looks like design or reuse, to give the agent nothing, or to have it check a draft against named perspectives. Each is an
implementation of the same solution, so each can be measured on the same cases and the better one used. The skill itself
asks for two behaviours that make this loop work: "Whenever using this skill, in your final output provide a short summary
of how you applied evolvable structure. If the human gives you feedback which suggests you didn't apply ESOI in the ideal
way, then record that learning in the relevant file in this skill's folder."

Perspectives are implementations too. The author's principle 7 says "We value collaboration and alternative perspectives,
as we don't know which perspective is best for a particular purpose; perspectives are implementations." Two reviewers who
disagree about a draft are two alternatives to compare against the purpose, not an authority to defer to.

## Measuring behaviour against cases

A behaviour case is one row: a scenario an agent might be sent, what acting by the principle looks like, what failing to
looks like, two cheap patterns (the reply must match every `must_have` and none of the `must_not`), and a recorded good
reply and bad reply. The recorded replies make the scorer itself testable offline: the good replies must pass, the bad ones
must fail, and a baseline that stuffs in the structure words must fail the cases that call for restraint.

Three kinds of case matter, and a set that has only the first would reward adding structure everywhere:

- **Build:** the right reply adds a registry, a metric, a single source of truth.
- **Restraint:** the right reply does the small fix and builds nothing. Principle 9 applies structure "only where the
  disadvantages of the particular structure don't outweigh the advantages", and a typo is not a framework.
- **Nuance:** the right reply keeps a qualifier. Principle 4 reads "Humans need only review metrics, not implementations
  (but they can still add value to implementations)", and a reply that drops the parenthesis, or that demands a review of
  every implementation, fails. The same holds for a separate solution, which needs a different definition of best that "could impact
  the success of the intent", and for a sub-intent, which needs an opportunity and has to pay for itself within the
  timeframe the larger solution prioritizes (see [when-to-create-a-sub-intent.md](when-to-create-a-sub-intent.md)), and for a problem, which is "a challenge, difficulty, or description of how an
  ideal is not reached", not a task.

The arms that call a model are the skill as standing instructions, the skill on request, and no skill at all as the floor.
They cost money, so they are measured only when a decision depends on them, in staged samples inside a call budget and with
the author's approval (see [when-metrics-are-run.md](when-metrics-are-run.md)). The offline arms run on every change.

## A judge calibrated against humans

Patterns cannot tell a reply that acts well in other words from one that only uses the right words, so a model can grade
instead, against the case's expected behaviour and failure mode, with the patterns as a prefilter. That judge is its own
solution. Applying the tests in [when-to-create-a-sub-intent.md](when-to-create-a-sub-intent.md): its best is agreement with a human verdict, where
the behaviour's best is acting by the principles, so the two would choose different implementations; the difference
affects the intent, because a judge that likes the wrong things makes the behaviour metric steer the wrong way; and the
split pays for itself within the timeframe, because the judge is needed before any live behaviour number can be trusted.

The judge is scored on labelled replies, with false passes and false fails counted apart. While the labels are the case
author's, agreement shows the judge is not broken, not that it is right; a person's verdicts go in the `human_verdict`
column and the headline shows how many labels are theirs. The judge and the agent that wrote a reply may be the same model,
and then it may favour its own phrasing; the metric measures that risk and does not remove it.

## Humans need only review metrics, and can still add value

The people who steer need only review the cases, the metric and its results, not every reply. They can still read a reply or
improve the instructions, and that still adds value. When someone corrects an agent, the lasting fix is a new case, so the
correction is measured from then on and the instructions can change without losing it.

## Where it is here

The solutions are in the top intent of [structure/](../../structure/). The cases and arms are in `implementations/python/evaluation/components/behave_by_esoi/` and `judge_esoi_behaviour/`, the
grading in `implementations/python/esoi/behaviour.py`. Run the offline arms with
`esoi run behave_by_esoi --impl reference_good`. Whether the skill changes behaviour is not yet measured.
