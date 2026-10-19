# evolvable-structure: index

`SKILL.md` is Joshua's own words and the authority; read it first. Every other file is AI-maintained
detail that serves it. Open a file only when its row matches your task, and stop once you have what
you need: most tasks need `SKILL.md` plus one or two rows. "Pattern N" means row N of the patterns
table in `principles.md`, which also gives that pattern's "reached when" test.

## First

If a local ESOI index exists (`$ESOI_HOME/INDEX.md`, or `~/.esoi/INDEX.md`), read it to find how ESOI is already applied to
the project you are in, and go where it says. If none exists and the user applies ESOI to several projects, offer to start
one (`esoi projects init` if the Python tools are in use, otherwise a `projects.csv` by hand). This index deliberately does not
list projects: it routes by kind of task, and which projects exist is the user's own, so it lives in the local index.

## Which file, and when

| Read | When | Skip when |
|---|---|---|
| `steps.md` | defining or applying ESOI to anything new, or working through a project in order: the steps from purpose to selection by metric and where to loop back, and how the process itself is improved | you are only answering a narrow design question |
| `python_tools.md` | the work is a code repository where ESOI's checks and measurements could be automated, the user asks whether a tool exists, or you are about to push a public repository: the optional `esoi` Python package, when to suggest it, and how to ask whether to use it and whether the repo may become a development or runtime dependency | a first pass, or any non-code intent: do it by hand |
| `principles.md` | you need concrete design or review questions for the ideals (the 15 patterns), you are deciding whether to generalize at all, writing up a design, or editing this skill. It is a sub-index for `principles/` | `SKILL.md` already settles the question |
| `coding.md` | writing, reviewing or restructuring code, especially code AI writes. It is a sub-index for the project examples in `coding/` | the work is not code |
| `other-categories.md` | products and settings, research method, teaching, coaching and certification, team processes and governance, documents | the work is only code |
| `sources/INDEX.md` | you need the original evidence or a quote for a claim, or are adding evidence to the skill | ordinary design or review: the files above already summarize it |

## By task

| Your task | Read | Only if needed |
|---|---|---|
| A data model, fields, where data lives | patterns 1, 4; `coding/pipelines_and_experiments.md` (examples 4, 5) | |
| Pipelines, stages, one function for notebook, CLI, pipeline and test | pattern 8; `coding/pipelines_and_experiments.md` (examples 3, 7); `coding/writealyze.md` (examples 13, 15) | |
| Experiments, tuning, evals, choosing the best implementation by a metric | pattern 9; `principles.md` "How to think and document"; `coding/pipelines_and_experiments.md` (example 6) | `principles/patterns_change.md` |
| Parameters, config, defaults that vary by run, user or environment | patterns 3, 4; `coding/pipelines_and_experiments.md` (example 5); `coding/registry_and_templates.md` (example 12) | `principles/patterns_core.md`, `principles/patterns_people.md` |
| A component other systems will use; versions, swappable implementations, changing a shared interface | `coding/components.md`; patterns 2, 13, 15 | `coding/registry_and_templates.md` (example 1); `coding/writealyze.md` (examples 9, 13, 14); `sources/INDEX.md` "Functional components" |
| A new repo or package, CI, environments, a deployment or lane as config, a script rebuilding a library's wiring | `coding/registry_and_templates.md` (examples 2, 8); `coding/concept_ai_quest_qar.md` (example 16) | |
| AI writing or reviewing code; a module that keeps growing | `coding.md` "When AI writes the code" and "Checks for any codebase" | |
| A product feature or setting, per-user customization, automation, or another multi-role product | `other-categories.md` "Product and UI"; patterns 3, 6, 10, 11 | `coding/concept_ai_quest_qar.md` (example 11, an example of per-user customization with shared defaults) |
| How an AI behaves: personas, context it sees, standing rules, model tiers, prompts, domains defined as data over one engine | pattern 7; `coding/concept_ai_quest_qar.md` (examples 10, 16, examples of a shared engine with data-defined domains) | `other-categories.md` "Process, organization and documents" |
| A business offering: course, coaching program, certification, individual plans | `other-categories.md` "Teaching, coaching and certification"; pattern 5 | |
| A research method, comparing cases or theories | `other-categories.md` "Research method"; pattern 12 | |
| How people propose, check and decide (reviews, votes, approval gates), or a process that should improve itself | `other-categories.md` "Collaborative innovation and process"; `principles/purpose.md` "A process is a structure too" | |
| Writing or reviewing a CLAUDE.md or other always-loaded context file | `other-categories.md` "Context files (CLAUDE.md)" | `principles/difficulties.md` "Copies drift" |
| Starting a project, product, course or process with ESOI, or asking "what do I do first?" | `steps.md` | |
| Deciding whether a part of a project should become a sub-intent, a separate solution or just an implementation; an intent that has grown too large | `steps.md` step 11; `principles.md` "Hierarchy is intents, not solutions"; the ESOI repository's "When to create a sub-intent" | `principles/difficulties.md` "The right level" |
| Where ESOI is already applied on this machine, how projects relate, or recording a new project | the local ESOI index (First, above); `python_tools.md` for `esoi projects` | |
| Automating ESOI's checks or measurements, a tool to check the records, or scanning a repository before a public push | `python_tools.md` (ask the user first) | |
| Writing up a design, a doc template, a project board | `principles.md` "How to think and document" | `other-categories.md` "Process, organization and documents" |
| Someone proposes an abstraction, or how much structure the task deserves is unclear | `principles/difficulties.md`; `principles/purpose.md` (sizing to the purpose) | `principles/research.md`; `sources/INDEX.md` "When NOT to generalize" |
| Deciding what stays stable and what is changeable | pattern 14; `principles/purpose.md` | `sources/INDEX.md` "Parts that change at different rates" |
| Carrying what one iteration learned into the next | `principles/purpose.md` | |
| Explaining the idea, choosing a word (adaptable, adaptive, evolvable, flexible) | `principles/vocabulary.md` | `sources/INDEX.md` "Definition and vocabulary" |
| Editing this skill | `principles.md` "Upkeep of this skill" | |
