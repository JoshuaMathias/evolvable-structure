# Applying a specification: Application Questions, order and sub-intents

How a person applies an ESOI specification to themselves, and how AI helps. `SKILL.md` defines the Application Question
field; this file is Joshua's guidance on using it (2026-11-10), with what follows from it. General principles first,
examples last.

## The question and its answer

- **The question belongs to the solution; the answer belongs to the person applying it.** The answer names the
  implementation they choose, or describes it, in words they understand: "What is your unifying technique?" is answered with
  the technique the person chose The answer is the human-readable form of which
  implementation is selected.
- **The answer keeps evolving.** Keep its history: the history is how the person's clarity grew.
- **An answer records uncertainty too.** How sure the person is decides what to test: decided (test that one),
  choosing between a few (compare them on the solution's metric), not sure yet (explore to find the options).
- **AI drafts, the person decides.** AI drafts each answer from the implementation it currently proposes; the person
  edits or replaces it. A restructuring or experiment result proposes changes to answers first, and the changes to
  implementations, habits and experiments that follow from an answer are shown with it.
- **Questions are simple.** They do not restate the ideals or metrics; they ask for the choice. They simplify by
  consolidating: one question may cover several ideals of its solution (a question about developing discernment can
  cover several related ideals at once), and whether each ideal needs
  its own attention depends on the person, so do not split a question just because its solution has several ideals.

## Completeness

Once a person has answered every Application Question of an intent with confidence, no additional choice should be
needed to carry out the intent: details are determined from the answers and the rest of the specification. A choice the
answers leave open means a question, or a solution, is missing.

**Drafting order follows dependencies.** Questions are shown in priority order, but an answer that depends on others
is drafted after them: dependencies are determined from solution dependencies (implementations' `uses_solution_ids`),
across an intent and its sub-intents. A schedule is the typical case: it places the practices chosen everywhere
else, so it is drafted last and revisited when they change. Check a specification for this before it is applied:
list the choices a person would still have to make after answering every question.

## Sub-intents: questions that build up to a solution's question

A solution's elaboration into smaller solutions always follows ESOI: the smaller solutions live inside an intent, a
sub-intent that is an implementation of the parent solution. Never link solutions to a parent solution directly; that
corrupts the structure. When a solution's implementation is a sub-intent, the sub-intent's Application Questions
together answer the parent solution's question, and the completeness check applies inside the sub-intent too. A
person applying the specification sees the sub-questions under the parent question; the parent answer summarizes the
sub-answers, and it is only as certain as the least certain of them.

**The structure is complex; the experience is simple.** However deep the structure (intents, sub-intents, their
solutions), a person applying a specification sees only questions, with sub-questions nested under the question they
build up to. They never see, name or create an intent or sub-intent; when a choice splits into smaller choices, AI
creates the sub-intent structure behind the questions.

## Order: solutions by priority for the intent

List an intent's solutions in order of priority for the intent: what the intent needs first comes first. Dependencies
often decide it: a solution that others depend on comes before them. Keep that order wherever solutions are shown,
and write it into every prompt that generates or restructures solutions, so generated solutions come out in that
order and new ones are placed by priority, not appended.

## Ideals as preferences

- **An ideal is a preference.** When someone applies a library specification, its ideals are the default
  preferences: they adopt each as their own (linked to the library ideal) and may reword its Principle, State
  Description and Hints of Measurement. A preference the library lacks becomes a new ideal of their own. How much each
  ideal matters to them feeds the weights of the solution's metric.
- **Show the preferences where the choice is made.** Beside each Application Question, show the person's version of
  the ideals linked to that solution, so the answer is chosen against them.
- **Principle or Approach?** Both may be worded as commands. A Principle says what is wanted, a standard any solution
  could be judged by; an Approach says how this one solution gets there. The test: swap in a very different solution.
  If the sentence still holds, it is a principle; if not, it is an approach. "Keep development steady" holds for
  habits, a coach or a community; "practice your unifying technique daily" is one way to be steady.

## What an implementation can be, for a person

- **A choice:** a decision that shapes other solutions ("my unifying technique is X"), with nothing to do on a
  schedule by itself.
- **A habit:** a recurring practice. **A goal:** a one-off step or daily goal.
- **A schedule** is a property of habits and goals (when and how often), not a kind of implementation. A
  specification may still have a solution whose question is about time; its answer sets that property.

## Optional fields

No field blocks anything. A field without the "(optional)" marker, left empty, is reported as the next thing to think
through; mark a field optional when leaving it empty is a fine permanent state for many records.

## Examples

**Sub-questions in a language-learning specification.** One solution keeps practice consistent. Its implementation is a
sub-intent with two solutions, so the person sees:

- How will you keep your learning moving in one direction, week after week?
  - What is your core technique that every other practice builds on? (for example, shadowing native audio)
  - What do you do on a regular basis, at what time or order, and for how long?

Answering both sub-questions answers the parent. The schedule question was surfaced by the completeness check (how
the week's limited time is split across practices was a choice no answer covered), and it is drafted last because its
implementation uses the solutions whose practices it places.

**A quest-creation flow.** Each strategy screen opens with its question, the AI's draft answer, a three-way "how sure"
choice that picks the experiment kind, and "What matters to you here" (the linked ideals, editable). A holistic
restructuring proposes answer changes first.
