# The ESOI steps: defining and applying it, in order

Follow these steps in order to turn an intent into evolvable structure, whether it's a project, a product, a course, a
team process or a piece of code. Each step says what to write and which record type it fills; the record types and
their questions are in `SKILL.md` ("The five specification templates within an intent", and the "Intent specification" for the container), and the number after a step is the principle it
carries out. The steps are the same for a small task and a large project; size each one to the work. A small change may
need a sentence per step, and a step with nothing new to add is skipped with a stated reason, never silently.

The order goes from why to what to how: purpose, problems, ideals, solutions, metrics, then implementations. Metrics
come before implementations so that "best" is decided before anything is built to win it, and the metric is itself
checked before anyone trusts it.

Steps marked **(human)** are where a conscious intent has to be stated or confirmed. An AI drafts them and asks; it
doesn't settle them alone. An AI can carry out every other step and report it.

## Part 1: Understand the intent

1. **State the purpose (human).** Name the intent (a specific phrase that distinguishes its topic) and write its vision
   statement in present tense ("The world is ..."): the intent is the container for everything below. In a sentence or two, write what the work is for, whose intent it serves, and the
   farthest point in the future it is meant to serve. Name the next milestone and its date: this is the timeframe
   that decides how much structure pays for itself (2, 1). Name the single top solution everything else will sit
   under (2). Before creating a new intent, check whether this project is already in the local ESOI index (8).
2. **Learn the five record types.** An intent brings insights on risks, uncertainties and opportunities: risks are
   addressed by the disadvantages of implementations and metrics, uncertainties by metrics, opportunities by solutions.
   Read what each type is, what it is not and what it connects to, so problems aren't
   written as tasks and solutions aren't written as code (13).
3. **Brainstorm everything in one place.** Before writing any separate record, list the problems, ideals, possible
   solutions and possible implementations together, plus a "probably won't be done" list that keeps scoped-out ideas
   visible and movable.
4. **Describe who it serves.** For each kind of person (or system) the work is for: why they'd use it, what makes them
   different, how serving them changes the way the work is done, and what may make it hard for them to use.
5. **Write the problems.** One Problem record each: what it is, who has it, why it matters, why it is hard, and the
   current workarounds. Give each record a short, clear id (13).
6. **Gather what is already known, and what already exists.** Collect knowledge about these people and problems, and
   look for existing structure to reuse before building any: earlier work of your own, open-source tools, science,
   data, advice (8). Link each source to the records it affects.
7. **Review the problems again** in light of what step 6 found. Merge, split, reword or drop them.

## Part 2: Define what "better" means

8. **Write the ideals (human).** One Ideal record per direction of improvement: a name, the principle it asks for, a
   description of what reaching it would be like, and hints of how you would know. Each opposes at least one problem.
9. **Check coverage.** Every critical problem is opposed by at least one ideal. A problem left uncovered gets a new
   ideal, or moves to "probably won't be done" with a reason.
10. **List the difficulties.** What may make this hard: missing knowledge, approvals needed, dependencies, risks. Each
    one becomes a problem, a piece of knowledge to find, or an open question for a person.

## Part 3: Define the solutions and how they are judged

11. **Write the solutions, top first.** Fill in the top solution, then give a part its own solution if and only if it
    has a different definition of best that could impact the success of the intent. SKILL.md recommends specifying an implementation as a
    sub-intent (a container of its own) "if and only if that intent brings insights on opportunities that don't emerge
    directly from the parent intent or solution that the sub-intent is implementing" (2). Also consider practicality:
    whether the resources to create and maintain it outweigh the benefit of defining it, within the timeframe up to the
    next highest priority milestone (step 1). Risks and uncertainties alone do not justify one: "Risks are addressed by
    considering disadvantages of Implementations and Metrics, uncertainties are addressed by Metrics". Where a solution elsewhere
    already serves a need, record that the implementation builds on it. Each Solution record names its problems and ideals, its scoped purpose (including what it
    deliberately avoids), goals, knowledge and measures of success. Before writing a new one, check whether an existing
    solution elsewhere already serves it (8, 9).
12. **Define the interfaces, and what stays stable.** For each solution, write its interface (parameters, inputs,
    outputs, effects) so implementations can change behind it without breaking what depends on it (3). Decide which
    parts are meant to stay stable and which are meant to change, from the purpose and what is likely to change next:
    this is the structure's niche of changeability (5).
13. **Write the metrics (human confirms).** For each solution, one authoritative Metric measuring the distance to its
    ideals: what is recorded and on which cases. Write the cases now (inputs and what a good result looks like),
    including cases where the right result is to do less. The top solution's metric measures the outcome in the real
    world, not only task completion (10). Write down what the metric cannot see (7). A person confirms each metric and
    its cases, since this is where people steer from (4).
14. **Check the metric before trusting it.** A metric is a solution too, with its own best: agreeing with what a
    person would judge. Show it can tell good from bad: a known-good result passes, a known-bad one and a do-nothing
    baseline fail. A metric that relies on a model's judgement is compared with a person's verdicts on a sample.
    Decide when the metric is run, and for any run that costs money, write the estimate, a staged sample (3, then 10,
    then 30 cases) and who approves the spend.
15. **Review from other perspectives.** Read the records as the people served, the people who maintain the work, a
    critic looking for risk, and someone a year from now. Add the problems, ideals and cases they would add (6, 7).

## Part 4: Build, measure and choose

16. **Write the implementations, with alternatives.** For each solution, the implementation you plan plus at least
    one alternative to compare it against. When there's no second idea yet, use a simple baseline such as "do nothing"
    or "the current way" as the floor (7).
17. **Build what is needed.** Carry out the implementations worth measuring, behind the interface from step 12, and
    in a way that is useful the next time (11). Not every alternative needs to be built in full before it is measured
    once.
18. **Measure.** Run every implementation on the same cases, as the run policy from step 14 allows, and record each
    result with the date, the implementation, the version measured and which cases were used.
19. **Select by the metric, and record it in one place.** The best implementation by the authoritative metric becomes
    the default, ideally used automatically (4). Record which one is selected and why (it won; it tied and was kept
    for a stated reason; or it lost and is kept until a named decision) in the single source of truth for these
    records (3).

## Part 5: Keep improving

20. **Try better alternatives.** Look for implementations that might do better, add them and measure them in the same
    way. The selection changes when a measurement says so, not when someone prefers another.
21. **Check the ideals in the real world.** Is each ideal reached, and how far off is each one, judged by the outcome
    in use rather than by the cases alone (10)? A gap points back to a solution, a metric or a missing ideal.
22. **Retire what isn't useful.** Park losing alternatives with the reason they lost instead of deleting them, so they
    can return. Remove records, files and steps nobody uses, and make what is reused most the easiest to find (11, 9).
23. **Loop back to the step a change touches.** The steps don't end; they are run again in part whenever something
    changes (5):
    - a new or changed problem, or a new person served: step 4 or 5
    - a new direction, priority or milestone: step 8 (and step 1 if the purpose changed)
    - a metric that rewards the wrong thing, or disagrees with people: step 13 or 14, then measure again
    - a part that keeps growing, an implementation that shows a new opportunity, or two uses that want different bests: step 11 (a separate solution or a sub-intent)
    - a new idea for how to do it: step 16
    - the structure itself making the work harder: run these steps on the structure, which is itself a solution

When you finish a pass, say in a few lines how the steps were applied and what was skipped and why, so the next pass
starts from there.

## The steps are a solution too

This process is an implementation of a solution, and is improved the same way.

- **Problem.** People who want to apply ESOI have the record types and the principles but no order to follow. They
  don't know what to do first, build before deciding what "best" means, trust a metric nobody checked, and stop after
  the first build.
- **Ideal: a followable process.** Someone new can follow the steps without asking what comes next, and ends with
  linked records, a checked metric and a selection made by it.
- **Metric.** Per trial (a person or an AI applying the steps to a real piece of work): which steps were completed,
  skipped with a reason or skipped silently; how many times they had to ask what to do next; and whether the result
  passes the structure checks with a metric that tells good from bad. Not measured by a recorded run yet.
- **Implementations.** These steps (selected, because they are the only one covering every principle); the 2020 Trello
  checklist they grew from; a one-hour first pass through them; and the record types and principles with no stated
  order, as the floor.
- **How to improve it.** When a step confuses someone, gets skipped, or is missing, change this file and record the
  trial. The esoi repository records the process as the solution "The ESOI steps" with these records.

## Where this came from

The order started from the "Steps to project completion" checklist on Joshua's 2020 Project Documentation Trello board
(`sources/trello_project_documentation.md`). Kept: purpose first, brainstorming before separate cards, the audience,
problems, gathering knowledge and then reviewing problems again, ideals, checking coverage, difficulties, solution
definitions, implementations with alternatives, carrying them out, trying better alternatives, checking every goal,
and keep improving. Added for ESOI, because the board left them out: a named timeframe, an intent with a vision statement and a single top solution; the
separate-solution and sub-intent tests; interfaces and the choice of what stays stable; metrics and their cases written before implementations,
with a real-world measure at the top and their limits stated; checking the metric itself and its cost before trusting
it; a review from other perspectives; a baseline whenever there is no second idea; selection by metric recorded in
one place; retiring what isn't useful; the human steps marked; a map of where to loop back to; and this section,
which applies the steps to themselves. Dropped: deciding what labels mean, which ESOI covers with record ids and links.
