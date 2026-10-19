# evolvable-structure: everything except code

How the ideals in `SKILL.md` show up in products, research method, teaching, protocols, plans and
documents. Evidence pointers use `sources/<file> > <heading>`; `INDEX.md` maps topics to files.

## Product and UI

- **One generic feature, attached to specific users from outside.** A product serves every user, and
  the owner's own tools connect through its public API or a webhook. The working test: would this
  screen make sense to a stranger's team? For example, Quest carries nothing only its author's
  organization needs.
- **Generic is not yet a reason to keep it.** A feature only one organization's workflow uses can leave
  the product instead of being generalized further. For example, Quest's Team Reports was made generic, then removed.
- **One generic data primitive, many uses.** For example, in Quest a dream journal, a habit or a course
  assignment is a collection from a template the user can use as is or customize.
- **Templates improve without overwriting people.** A new template version reaches each copy except
  the fields its owner changed (in Quest, each quest).
- **Personal context enters every AI call.** The person's goal, its state and their preferences go
  into each call, so one AI behaves differently for each person. In Quest every quest is a context card.
- **Autonomy is a setting a person chooses.** Record whether the person actually chose it. In Quest,
  autopilot is "Off by default; a quest never opts itself in.", planning is per quest (`plan_and_work`), and
  per-person AI handling is auto, ask or never.
- **New behaviour starts opt-in, and a default that acts at scale is bounded.** After calendar sync
  flooded Joshua's calendar, sync became opt-in and its window a user setting.
- **Settings grow without the screen growing.** Group them and draw nothing not yet set until asked for;
  one control holds new affordances instead of a nav entry per team. For example, Quest's Autopilot panel is four groups.
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
- **A domain is a parameter, and weight is earned.** For example, Concept AI has one engine, domains as
  YAML, sources weighted by measured reliability, and a wrong method kept as a comparison arm.
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
- **One structure for any big goal.** A grounded strategy (a public plan), personal context, and daily
  execution. In a Quest marathon example the plan came from a public training plan, and a sore knee became a comment
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
  each group's list of decisions "may be adapted in the future". (`cantr_governance_proposals.md > Escalation by significance, not by department`, `> A per-department list of what is voted on, open to change`)
- **It exists so change happens well.** No one person carries a big decision, everyone has a voice,
  and a second person verifies each change. (`cantr_governance_proposals.md > Why a process at all: shared responsibility and a voice for everyone`, `> A second person as the verification step`)
- **It keeps work moving.** Silence after two weeks means acceptance, and a rejection must produce an
  alternative within a month. (`cantr_governance_proposals.md > Silence and rejection have defined outcomes`)
- **Commitment is staged.** Agree on the idea before effort goes into details, then approve the
  details; a changed proposal gets a new vote without waiting. (`cantr_governance_proposals.md > Revising a proposal without restarting the process`, `> Multi-department work in a sensible order`)
- **A steady rhythm carries changing content.** A fixed week lets volunteers plan and think;
  routine, reversible items pass by default, and contested ones rise to a slower level. (`cantr_governance_proposals.md > A fixed rhythm so people can plan and think`, `> Defaults with stated overrides: duration, ties, early close, anonymity`)
- **Bias and power are handled by design.** Anonymous submissions judge ideas apart from their author,
  groups balance each other, reasons are public, and the owner's override is visible. (`cantr_governance_proposals.md > Ideas judged apart from who proposed them`, `> Balance between groups`, `> Accountability for the owner's override`)
- **Participation is open and earned.** Anyone can propose, and board membership comes from several
  kinds of contribution, renewed monthly. (`cantr_governance_proposals.md > Membership by contribution, through several paths with thresholds`, `> Three vote types on one board`)

## Process, organization and documents

- **Defaults keyed to reversibility.** Reversible matters are decided with a default; forks and
  irreversible acts wait for a person.
- **One quality gate reused everywhere.** Draft, critic, human approval, with the confirmation step as
  the parameter.
- **Standing rules as small retrievable cards.** Tag each rule with when it applies, retrieve rather than
  paste, and keep paid-for lessons as dated invariants. For example, quest-ai-runner does both.
- **Documentation as problem, ideals, definitions and implementations.** Joshua's Project Documentation
  board is the model `principles.md` follows ("How to think and document"). (`trello_project_documentation.md > Documentation`, `> Solution Definitions`)
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
- **Generated blocks** (a tool writing between markers, such as a generated block listing a goal's folder)
  render this same shape, stay short, and put detail in the file it governs.
