# evolvable-structure: everything except code

How the ideals in `SKILL.md` show up in products, research method, teaching, protocols, plans and
documents. Evidence pointers use `sources/<file> > <heading>`; `INDEX.md` maps topics to files.

## Product and UI

- **One generic feature, attached to specific users from outside.** Quest is a product for every
  user, and Spiritual Data's own tools connect through the public API or webhook. The working test: would this
  screen make sense to a stranger's team?
- **Generic is not yet a reason to keep it.** Team Reports was made generic, then removed, because only
  one org's workflow used it.
- **Collections are a generic data primitive.** A dream journal, a habit or a course assignment is a
  collection from a template the user can use as is or customize.
- **Templates improve without overwriting people.** A new template version reaches each quest except
  the fields its owner changed.
- **Every quest is a context card.** The quest's outcome, state and the person's preferences go into
  every AI call, so one AI behaves differently for each person.
- **Autonomy is a setting a person chooses.** Autopilot is "Off by default; a quest never opts itself
  in.", planning is per quest (`plan_and_work`), and per-person AI handling is auto, ask or never, with
  a flag recording whether the person actually chose it.
- **New behaviour starts opt-in, and a default that acts at scale is bounded.** After calendar sync
  flooded Joshua's calendar, sync became opt-in and its window a user setting.
- **Settings grow without the screen growing.** The Autopilot panel is four groups, and nothing not
  yet set is drawn until asked for. One control holds new affordances instead of a nav entry per team.
- **Default workspaces per role, all overridable.** Writealyze planned presets for translators, data
  scientists and students, each changeable.

## Research method

- **One method across cultures, people and sources, with categories that emerge.** His near-death-experience (NDE) work uses
  one phenomenological method across cultures and found the fixed Greyson scale fails some of them.
- **Applicability as one scored method.** His quantitative hermeneutics paper treats domain, outcome
  and population as parameters of one method, tests it by self-application, and stops expert tuning
  once the metric is high enough.
- **The dissertation method is theory-agnostic.** The domain is the content fed in, labels stay out of
  the ranking, and the phases loop. No second-domain run is reported yet.
- **Concept AI: a domain is a parameter, and weight is earned.** One engine, domains as YAML, sources
  weighted by measured reliability, and a wrong method kept as a comparison arm.
- **Flexibility has a cost worth naming.** Joshua marked Lucas (1974) on this as a key quote; the text
  is in `principles/difficulties.md`.

## Teaching, coaching and certification

- **The container is shared, the content is personal.** Every student gets the same rhythm and the
  same three evaluation criteria, and each student's experience is "a separate research project"
  with their own metric.
- **The teacher narrows options and the student chooses.**
- **One map, editable by its users, applied one student at a time.** The developmental map's propositions apply to every ability
  type, and teachers and students are free to adapt it. It has three layers: seven propositions, then 20 shared ideals, then each student's own strategy. Super Psychic Academy's method is this paper's framework.
- **A component can be reused in more than one offer.** SPA 101 is the first month of the coaching program,
  "Not a separate product", so the same piece serves a standalone course and the start of the program, and it improves
  in one place. The same test
  applies to a lesson, a protocol or a template: improvable inside, usable in another system with only its
  parameters changed.
- **One structure for any big goal.** Quest holds a grounded strategy (a public plan), personal context, and daily
  execution. In the marathon example the plan came from a public training plan, and a sore knee became a comment
  ("walk instead") on that day, not a new plan.
- **The Quest course is a Quest cohort.** Assignments are collections tied to each student's own goals,
  each week building on the last. Promising founder-built features per student pulls against the
  generic core.
- **Fixed core standards, procedure per ability.** The certification protocol fixes the standards,
  sets a default procedure per ability with room to customize, and says what it leaves out (healing).
- **Iteration gated on evidence.** The Academy funnel releases spend stage by stage and carries the
  Quest course's lesson forward by name.

## Collaborative innovation and process

A process is an evolvable structure: the stable part is how people propose, check and decide, and
what it lets change is the work and, in the end, the process itself. The examples are Cantr's staff
and player governance proposals (proposals, not records of how they worked).

- **The process can amend itself.** "How decisions are made." is a decision for the top board, and
  each group's list of decisions "may be adapted in the future".
- **It exists so change happens well.** No one person carries a big decision, everyone has a voice,
  and a second person verifies each change.
- **It keeps work moving.** Silence after two weeks means acceptance, and a rejection must produce an
  alternative within a month.
- **Commitment is staged.** Agree on the idea before effort goes into details, then approve the
  details; a changed proposal gets a new vote without waiting.
- **A steady rhythm carries changing content.** A fixed week lets volunteers plan and think;
  routine, reversible items pass by default, and contested ones rise to a slower level.
- **Bias and power are handled by design.** Anonymous submissions judge ideas apart from their author,
  groups balance each other, reasons are public, and the owner's override is visible.
- **Participation is open and earned.** Anyone can propose, and board membership comes from several
  kinds of contribution, renewed monthly.

## Process, organization and documents

- **Defaults keyed to reversibility.** Reversible matters are decided with a default; forks and
  irreversible acts wait for a person.
- **One quality gate reused everywhere.** Draft, critic, human approval, with the confirmation step as
  the parameter.
- **Standing rules as small retrievable cards.** QAR stores rules as cards tagged with when they apply,
  and keeps paid-for lessons as dated invariants.
- **Documentation as problem, ideals, definitions and implementations.** Joshua's Project Documentation
  board is the model `principles.md` follows ("How to think and document").
- **Apply it to the document, not only to the tool that plans it.** When building an instrument for a
  document (a checklist or question sheet for an outline), structure the document itself too: each
  section names the problem it solves, its interfaces (which sections depend on it), where its content
  is reused, and a test that every draft is scored against, per draft version. Separate research
  questions that have different definitions of "best" (a domain question vs a method question), each
  with its own ideal and metric, and state the method's question with the domain as a parameter.
  Joshua, 2026-10-15, after a sheet applied the skill only to its own columns: "was it applied to the
  dissertation outline itself", then "apply it to the research question and dissertation".
- **One question per separately measurable answer.** When a planning sheet asks someone to define a
  solution, split a question wherever a part could have its own metric (finding cases vs screening them
  vs when to stop), and split the metrics the same way so each part links to its own. Keep anything
  derivable (a section's test from its questions' tests) derived, not copied, with a checker that
  regenerates it. Joshua, 2026-10-16: "every separately operational answer should be a separate
  question essentially ... relationship to metrics is a good way to think about it, if metric could be
  separate."
- **Principles with a purpose and a decision.** Each Writealyze principle card says how the truth
  relates to the purpose and how it is applied in decisions, so a new case can be checked against it.

## Context files (CLAUDE.md)

The standard for every CLAUDE.md (and any file loaded the same way). Claude Code loads each CLAUDE.md
from the working folder up to the root into every session, and a subfolder's when files there are
read, so each line costs attention in every session below it, and a rule written twice drifts.

**What a CLAUDE.md does:** orient any session working in its folder: what the folder is for, what is
here and when to open it, and the rules that apply to most work here and are not stated above it.

| Ideal | Applies | Reached when |
|---|---|---|
| Purpose first: what the folder is for, who works here, its tracked goal if any | 10 | someone can tell in three lines whether their task belongs here |
| Say only what differs from the files above it; point to the owner of anything stated elsewhere | 7, 11 (generational, topical) | no rule appears twice in the load chain |
| Every always-loaded line applies to most sessions here; task-specific material sits in an on-demand doc with a "read when" line | 10 | there is no section most sessions would skip |
| One owner per rule, by its dimension: the lane's hub for a lane rule (vertical), the repo or tool for a technical rule (horizontal) | 11 | changing a rule is one edit |
| Status lives elsewhere: no "as of" snapshots; standing rules keep Joshua's words and date | 5, 6 | nothing is stale a month later without an edit |
| Self-contained where its readers cannot see the parents (a public repo, or a user that cannot read above the folder) | 11's limit | those readers get every rule they need |

Measure: characters always loaded for a typical working folder (lower, with nothing lost), duplicated
rules (zero), broken pointers (zero).

Shape (only the opening is required; headings are named, not numbered):

```
# <Folder name>
<What it is for, who works here, its tracked goal if any.>
## What's here   <path: what it is; read when ...>
## Rules here    <only what adds to or differs from the parents>
## On demand     <doc: read when ...>
```

- **Where moved material goes:** on-demand docs in `.claude/docs/` beside the CLAUDE.md (or an
  existing `docs/`); superseded status and dated history in `history.md` or `archive/`, not deleted.
- **Generated blocks** (a tool writing between markers, such as quest-ai-runner's quest-folder block)
  render this same shape, stay short, and put detail in the file it governs.
