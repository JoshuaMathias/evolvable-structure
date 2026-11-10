# Experiments in ESOI

> "I see an experiment as scoping the current effort of focused exploration for the intent/[workspace]." (the owner, 2026-11-10)

> "There should be records of experiments." (2026-11-10)

> "Experiments represent the pinnacle of [the workspace's] value IMO, and I'm using it to clarify where focused attention goes, whether for me or
> a team member, and what is in a sense set in stone for the period of the experiment, like a trial period before reevaluating. Though a
> person can have more than one experiment if they choose." (2026-11-10)

## Definition

An experiment is a record, at an intent, of its current effort of focused exploration. It is a research direction: its research
question, scope, owners and period. An investigation ([`investigations.csv`](knowledge-search-standard.md)) is one piece of information
gathering carried out to answer a question (a review of sources, a trial, an observation, an interview), inside an experiment or on its
own. The `question` of an investigation is a sub-question of the experiment's `research_question`, or the same question. "Research"
stays the general word for the activity; the record of one piece of it is always an investigation (the owner's choice, 2026-11-10, over
inquiry, study and evidence search; it was `research.csv` before).

Two ideas make an experiment distinct:

1. **It directs focused attention.** For its period, what is outside its scope is not where attention goes, for its owners (people or
   team members, human or AI).
2. **It fixes certain things for a trial period.** The choices it holds fixed are not re-decided until the reevaluation time, and are
   reopened then. The AI and people do not reopen them early, and do reopen them at that time.

It says what is being explored (the research question, or way of thinking), its owners (optional: it may be one's own), the
period (a start and the time or condition of reevaluation), what is held fixed, what is in scope and what is outside scope for now. It
ends in a reevaluation: what was learned, what that changed (knowledge, structure, priorities, milestones), and a decision:
continue for another period, change it, or end it, with the next experiment if any. Investigations (reviews, observations, trials,
interviews) happen inside it under the [research standard](knowledge-search-standard.md), and give the experiment what it learns. A
trial of an alternative on a metric stage is the special case where the question is "is this alternative better".

The role is loose on purpose. An experiment may be quantitative or qualitative, may bear on many solutions or on none yet, or on how the
intent is thought about, and carries a number only when its question compares alternatives on a metric. Dated 2026-11-10; how to
run one: [run an experiment](../how-to/run-an-experiment-as-a-trial.md).

## The record

`experiments.csv`, in the records folder of its intent, beside that intent's other records (placement: [records beside the
code](records-beside-code.md)). An intent with no such file is valid. The fields, with the question each answers
(the wording is the owner's to adjust, and the fields are not part of the specification template, so the template version does not change):

| Field | Question |
|---|---|
| `experiment_id` | What is its handle? |
| `intent_id` | Which intent is it explored in? |
| `name` | What is a short name that distinguishes it from the intent's other experiments? |
| `research_question` | What question or way of thinking is being explored? An investigation's own `question` is a sub-question of it, or the same |
| `owners` | Whose focused attention is it for (people or roles)? Empty when it is one's own |
| `priority` | Proposed, for the owner's review: its place among the intent's running experiments, 1 first |
| `status` | `planned`, `running`, `reevaluating` or `ended` |
| `starts_on` | When does the period start? |
| `reevaluate_time`, `reevaluate_condition` | At which time (a date, or a date and minute), or under which condition, is it reevaluated? |
| `held_fixed` | Which choices are not re-decided until then? `;` separated, each `subject = choice` or free text |
| `in_scope`, `outside_scope` | What is in the scope of the exploration, and what is deliberately outside it for now? |
| `links` | Optional, many to many: `kind:id` of the solutions, problems, ideals, metrics, milestones, implementations or knowledge it bears on |
| `investigation_ids` | Which investigations (pieces of information gathering) were carried out inside it? |
| `learned` | At reevaluation, what was learned? |
| `changed` | What did it change, as `kind:record id` (knowledge, structure, priorities, milestones)? |
| `decision` | `continue`, `change` or `end` |
| `next_experiment_id` | Which experiment follows, if any? |

Investigations name their experiment with `experiment_id` in `investigations.csv`; the two lists agree. A generated intent page shows the intent's running experiments first, in priority order, one line each with its reevaluation date, before the
solutions table (the top intent's page above all), and nothing extra when it has none; it also lists every experiment with its status, research question, period and what is held fixed. `esoi.understanding.solution_consideration.experiments`
reads them: `running(config, intent_id, owners)` is where attention goes now; `due(config, on)` is what is past its reevaluation time.

### What `esoi check` says about it

Advice only in this pass. It lists a record missing its research question, start, scope or status; a running or planned experiment with no reevaluation time or
condition; a running one that holds nothing fixed; an ended or reevaluating one with no learned or decision; a link or changed entry
of an unknown kind; an investigation it names that does not exist; a reevaluation past its time; two running experiments of the same
person that fix different choices for the same subject, a priority that is not a whole number from 1, and two running experiments of an intent that share a priority.

## Several at once

An intent or a person may have more than one running. Each scopes its own research question and holds its own choices fixed; they coexist
as long as what they hold fixed does not contradict. A check advises when two running experiments with the same owner fix
different choices for one `subject` (`storage = local` against `storage = remote`); free-text commitments are not compared.

## How an AI uses it

Any AI working on an intent reads its running experiments first (`running`), so that it knows where attention goes, keeps its work
inside that scope and does not re-decide what is held fixed. At the reevaluation time (`due`) it prompts the reevaluation, which a
consumer's autopilot or chat surfaces: what was learned, what it changed, continue, change or end. It records the answer in the
record, proposes the milestone or structure changes for the intent's owner to confirm, and opens the next experiment if there is one.

## Placement

| Part | Where it sits | Reason |
|---|---|---|
| The experiment | `experiments.csv` at its intent | The owner's definition is about the intent; it may span several solutions or none; extend before adding applies to specification types, and this is a records file like knowledge, not a field of the template |
| Research question, in scope, outside scope | Its own fields | Not in `opportunities` (potentials, not a bounded exploration) |
| Held fixed, reevaluation | Its own fields | Nothing existing says what is not re-decided for a period |
| Investigations inside it | `investigations.csv` rows with `experiment_id` | One standard serves a review done for a one-off decision too |
| What it bears on | `links`, many to many, optional | Ids need no sign-off |
| What was learned, what changed | `learned`, `changed`, and `applied` on each investigation item, knowledge rows with `investigation_id` | A decision about an alternative is one application among others |
| A trial of an alternative | The special case below | Reuses existing fields |

### The special case: is this alternative better

The alternative is an implementation that is not `selected`; the measure is the solution's metric at a named stage of its
`cascading_conditionals`; the value expected is a solution milestone and the value that rejects it is the stage's floor, both fixed before
scoring (and listed in `held_fixed`); the end condition is the milestone's end condition, the stage's sample size and the run policy's
budget; the run is a row of the results log; the decision is `esoi select --promote` (a proposal, or an automatic switch where the
solution says so). A hub arm that is `on_trial` is measured and never handed to a consumer until the owner releases it: that is this case.

## Experiments and prioritization

> "scoped experiments could be important for ESOI too. ESOI is primarily a structure of components that self optimize and each solution has priorities. But experiments provide important capability of prioritized research directions that could be cross-cutting across different types of spec records and structure. But just optimizing an intent is the simplest example of an experiment or research direction. We could have a priority of research directions/experiments recorded at top of every esoi repo, need to check how this relates to general idea of prioritization, and how/why/if this is useful and something esoi itself should do." (the owner, 2026-11-10)

This section is a proposal for the owner's review; nothing in it fails a check.

Two kinds of priority nest:

- **Solution milestones** order effort inside a solution whose place in the structure is settled: "all effort is either defining the structure or
  reaching the next priority". A milestone is a value of a metric with an end condition.
- **Experiments** order where attention goes across the intent: which questions and which solutions are in focus now, cutting across any kind of
  record (a problem, an ideal, a metric, several solutions), and what is not reopened until the reevaluation. `priority` orders an intent's running
  experiments.

"Optimize the intent" is the default direction when none is recorded, carried out by the ordinary metric loop (measure the alternatives, promote the
winner, then the next milestone). A recorded experiment narrows or redirects that default for a period. So the two are one system: with no
experiment, effort follows the milestones; with one, effort follows the experiment's research question first and then the milestones it puts in focus.

Rules that avoid duplication (risk R1):

1. An experiment never restates a milestone. It links to the milestones it puts in focus (`links`, `milestone:<id>`) and to the solutions,
   problems, ideals or metrics it bears on.
2. Keep few running; the order is what directs attention first, so a long list directs nothing.
3. Each has a reevaluation time or condition, and the check advises when one is past it.

How a consumer's prioritization reads them (for example the hub's Prioritization solution and an autopilot built on it): the running
experiments first, in `priority` order, as the attention of the owners (people or AI) they name; then the milestones they put in focus, ordered by the
usual fields; then every other milestone and waiting item. An item inside an experiment's scope is not held back for being low in the default order;
an item the experiment's `held_fixed` forbids reopening is held back until the reevaluation time.

Whether ESOI itself should record a priority of research directions at the top of every repository is the owner's to decide. The proposal in this
pass is only what the generated page does: the top intent's page lists its running experiments first. A repository with none sees nothing new.

### Worked example: a repository's directions

The test of usefulness is whether recording a direction would have changed a decision. Three directions of a repository that assembles AI
components by metric, in generic wording:

(a) **A harness that beats the reference harness on the same model at the fast tier.** It cuts across five solutions (delegated sessions, the
format of the agent's actions, the folder view, goal completion and the terminal experience). Held fixed: the same model and judge, and the
consumer's own pick unchanged until the arm is promoted. Reevaluation: when the arm has results at the next stage, or a date. Recorded, it would have
changed decisions: work on each of the five solutions was judged on its own metric, so a gain in one was not weighed against a loss in
another, and the consumer's pick was at risk of changing before the arm was promoted. As a record, the held-fixed list is what stops that.

(b) **Adopt existing work before writing, across all solutions.** Held fixed: nothing is written for a solution until the strongest existing
implementation is built on or its rejection recorded. Reevaluation: when every solution has a recorded decision for its candidates. Recorded,
it would have changed one decision here: an arm written from nothing was crowned over a weak baseline while mature implementations sat in the
registry as findings; the standing direction, with its reevaluation, is what the repository's guard test later enforced. It is also the direction
the research standard serves, and it is the one most likely to be satisfied by rules and checks alone, so as an experiment it adds the least.

(c) **Make the structure visible in the experiences people use.** Held fixed: the structure's names and the person's view are not changed while the
exploration of what people look at runs. Reevaluation: a date. Recorded, it would probably not have changed a decision: it is a priority of
ordinary milestones on one solution (the experience), with no cross-cutting question and nothing to hold fixed, so a milestone already carries
it. It shows where an experiment is not needed.

So the honest finding is two of three: (a) is the case an experiment serves (cross-cutting, with things held fixed), (b) benefits mostly from the
reevaluation, and (c) is a milestone.

## A consumer application's experiment feature

An application built on ESOI that keeps experiments on a goal-planning workspace reads this page as the definition. Guidance for what its AI
generates and how it uses it, and a checklist for its own feature (this page changes no application).

An application's experiment is the focused exploration of a workspace for a period: the question in the person's own framing (or the way of
seeing the workspace they will try), its owners, what to try and notice, what is held fixed meanwhile, what is outside its scope for
now, when to look back, and, at the look back, what was learned, how it applies to the workspace, and whether to continue, change or end.
Research and trials happen inside it; what was learned is applied to the workspace's knowledge, goals, strategies or priorities. A person
may run several. It may span several goals, may be qualitative, and needs a number only when the person compares options on a measure.
The AI proposing one starts from the workspace's knowledge and research (citing them) and leaves the scope, the fixed choices and the period
to the person to confirm; the AI working in the workspace reads the running experiments to know where attention goes and what not to
re-decide, and prompts the look back.

Check an existing feature against the definition: does it say who owns it; what is held fixed for the period; what is outside its scope
for now; a reevaluation time or condition and a reevaluating state; an outcome that records what was learned, what it changed (with
record ids), and continue, change or end, with a next experiment; does it fit a qualitative exploration without goals or habits as data;
and do the investigations done inside it have a method, items and an applied part, with the knowledge it produced linking back? Where an
application falls short, the change list is: optional fields for `owners`, `held_fixed`, `outside_scope` and a reevaluation time or
condition; states `planned`, `running`, `reevaluating`, `ended`; a reevaluation outcome; links to the investigations inside it and to the knowledge
it produced; the AI's create and update tools asking for the research question in the person's framing, what to try and notice, what is held fixed and
the look back date; and a reevaluation prompt the person confirms. One application's own reading, with its mismatches, is kept with the
author's private notes on that application, not here.
