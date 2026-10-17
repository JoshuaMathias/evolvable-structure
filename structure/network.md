# The ESOI network of the evolvable structure itself

Draft for Joshua's review, 2026-10-17. This is the intent of the structure itself: the evolvable
structure that every solution of an adopting repository is recorded, measured and selected through ("The structure itself is
an implementation of a solution which defines the purpose of the structure", `SKILL.md`). Every field
is a field of the intent template in the evolvable-structure skill's `SKILL.md`; nothing here adds
fields of its own. Metric has only a name until the template defines its other fields. Ids are short
and stable so records can link to each other and to the registry.

## Problems

### PR1 Intent is lost between the person and the code
- **What is the problem?** What someone meant when they asked for a capability lives in their head, a chat or a task, and the code that answers it carries none of that meaning. Months later nobody, human or AI, can tell what a module was for, which use cases it must serve, or what "better" would mean for it.
- **Who or what type of person has the problem?** The person who set the direction (Joshua, a Director), the developers and AI agents who change the code later, and anyone deciding whether a part is still needed.
- **Why does this problem matter?** Code drifts from its purpose, work is redone, and the only way to judge a change is to read the implementation, which does not scale with AI writing most of the code.
- **Why is the problem hard to resolve?** Words only approximate intent, intent changes over time, and many agents with no memory between sessions change the code faster than any document is kept current.
- **What solutions or workarounds already attempt to address the problem?** Product requirement documents, architecture decision records, issue trackers, CLAUDE.md files and playbooks, code comments. They hold intent as prose that nothing checks against the code.

### PR2 Nobody knows which alternative is best, so choices are made by opinion or habit
- **What is the problem?** Most parts of a system can be done several ways (a model tier, a router, a retrieval method), and the one in use was chosen by whoever wrote it, not by evidence. When a better alternative appears, nothing shows that it is better or makes it the default.
- **Who or what type of person has the problem?** Maintainers and AI agents choosing or changing an implementation; Joshua, who wants the best implementation used automatically.
- **Why does this problem matter?** Quality and cost depend on these choices. Real examples found once measured: a model priced at the wrong rate, a router kept although a cheaper one scored as well.
- **Why is the problem hard to resolve?** Model output is noisy, costs swing with caching, good test cases are expensive to write, live runs cost money, and "best" differs per use case.
- **What solutions or workarounds already attempt to address the problem?** Ad hoc evaluation scripts, public benchmarks, eval tools (promptfoo, OpenAI Evals, LangSmith), A/B testing platforms, experiment trackers. They measure, but do not tie the result to which implementation runs.

### PR3 Measurements cannot be trusted or compared
- **What is the problem?** A number recorded on uncommitted code, on a different case set, typed by hand, or copied into prose that is never updated looks like evidence but proves nothing. Two numbers from different conditions get compared as if they were alike.
- **Who or what type of person has the problem?** Anyone deciding from a result: reviewers, Joshua, the selection itself.
- **Why does this problem matter?** A wrong number leads to the wrong default, and once people notice untrustworthy numbers they stop reading metrics and go back to reading code.
- **Why is the problem hard to resolve?** Provenance needs discipline every single time, several agents edit the same working copy at once, and noise makes small differences look real.
- **What solutions or workarounds already attempt to address the problem?** Experiment trackers (MLflow, Weights and Biases), CI artifacts, lab notebooks, statistical significance tests.

### PR4 Changing which implementation runs means editing code
- **What is the problem?** Switching a provider, runner or backend means finding and editing the call sites, often an `if` chain, and an embedding system cannot switch without forking.
- **Who or what type of person has the problem?** Developers, operators configuring a deployment, and systems that embed a library built on this structure.
- **Why does this problem matter?** Measuring an alternative is pointless if adopting it is risky and slow, so the measured winner never ships.
- **Why is the problem hard to resolve?** Implementations need different configuration and optional dependencies, and a typo in a name must fail loudly rather than fall back silently.
- **What solutions or workarounds already attempt to address the problem?** Dependency-injection containers, plugin entry points, feature-flag services, factory functions.

### PR5 Code accumulates that serves no purpose and grows past understanding
- **What is the problem?** Files no one can attribute to a purpose stay because deleting feels risky, and modules grow until no one reads them whole (one adapter file reached thousands of lines).
- **Who or what type of person has the problem?** Maintainers, and AI agents whose context fills with code that does not matter to the task.
- **Why does this problem matter?** Every unowned line costs reading, testing and risk, and hides the parts that matter.
- **Why is the problem hard to resolve?** AI writes code faster than anyone prunes it, and without a record of purpose there is no basis to delete.
- **What solutions or workarounds already attempt to address the problem?** Dead-code finders (vulture), code owners files, size linters, periodic clean-up passes.

### PR6 Structure rules decay silently
- **What is the problem?** Rules written in prose (where files go, which way imports point, what must be documented) are followed by whoever read them and broken by the next agent, and generated documents drift from what they describe.
- **Who or what type of person has the problem?** Maintainers and every agent working in the repository.
- **Why does this problem matter?** The structure only gives its benefits while it holds; a rule broken once is copied.
- **Why is the problem hard to resolve?** Agents start without memory, rules multiply, and a check that is slow or noisy gets skipped.
- **What solutions or workarounds already attempt to address the problem?** Linters, pre-commit hooks, architecture tests (import-linter, ArchUnit), code review.

### PR7 Humans cannot review at the level of intent
- **What is the problem?** A person who wants to steer quality has to read implementations, because ideals, metrics and current results are not gathered anywhere they can read and correct.
- **Who or what type of person has the problem?** Joshua and the people who direct the work, who should review metrics, not implementations.
- **Why does this problem matter?** Review either does not happen or consumes the time it was meant to save, and human judgment never reaches the definition of "best".
- **Why is the problem hard to resolve?** Results live across folders and repositories, a metric is only worth reviewing if it measures its ideal, and edits made in a review must flow back to the source.
- **What solutions or workarounds already attempt to address the problem?** Dashboards, shared spreadsheets, pull-request review, status reports.

### PR8 Evaluation is detached from the code that ships
- **What is the problem?** Evaluations built beside production code test copies, stubs or scripts of their own, so their results describe something that does not run.
- **Who or what type of person has the problem?** Joshua (who named this), maintainers deciding from results.
- **Why does this problem matter?** A detached evaluation gives false confidence and decays as the real code changes.
- **Why is the problem hard to resolve?** Driving real code needs realistic inputs, fakes for external services, and isolation from real data and spend.
- **What solutions or workarounds already attempt to address the problem?** Integration tests, shadow traffic, canary releases, end-to-end tests against staging.

### PR9 A system that embeds a library cannot tell whether its use is sound
- **What is the problem?** A system builds on a library's solutions with its own stores and prompts, but cannot see which library solution each of its parts serves, whether its parts meet the library's own cases, or how far its pinned version lags.
- **Who or what type of person has the problem?** Developers of any system built on a library that uses this structure.
- **Why does this problem matter?** The embedding is where users meet the library, so an unsound integration undoes the library's quality.
- **Why is the problem hard to resolve?** Two repositories, one public and one private, change at different rates under different rules.
- **What solutions or workarounds already attempt to address the problem?** Version pins, changelogs, contract tests, integration test suites.

### PR10 The template evolves and its copies drift
- **What is the problem?** The intent template is being refined in the skill, and every registry and checker that copied its fields falls out of date.
- **Who or what type of person has the problem?** Joshua as the template's author, and every AI filling records.
- **Why does this problem matter?** Records then follow an old idea of intent, and the author's refinements never reach the work.
- **Why is the problem hard to resolve?** The template is prose written for people, and changing a field means changing every record that uses it.
- **What solutions or workarounds already attempt to address the problem?** Copy and paste, schema documents, form builders.

### PR11 Others cannot apply ESOI to their own code
- **What is the problem?** There is no worked, checked example of evolvable structure in code, so each team that wants it designs its own from prose.
- **Who or what type of person has the problem?** Other developers and teams, open-source users of this library, AI agents asked to apply ESOI elsewhere.
- **Why does this problem matter?** The approach only produces progress at scale if it is easy to copy.
- **Why is the problem hard to resolve?** A standard has to be general enough for other repositories and concrete enough to follow without its author.
- **What solutions or workarounds already attempt to address the problem?** Articles, framework conventions, project templates (cookiecutter).

### PR12 Structure costs more than it returns
- **What is the problem?** Every rule, record and check adds work to each change, and past a point contributors spend more time satisfying the structure than improving the code.
- **Who or what type of person has the problem?** Contributors making small changes, and Joshua weighing the structure's value.
- **Why does this problem matter?** Overbuilt structure gets bypassed, faked or abandoned, which loses its benefits entirely.
- **Why is the problem hard to resolve?** The value of structure shows up later and spread out, while its cost is felt now on each change.
- **What solutions or workarounds already attempt to address the problem?** Lightweight conventions, opt-in tooling, waivers.

## Ideals

### ID1 Explicit intent
- **Name:** Explicit intent
- **Principle:** Every built part traces to the problems it addresses and the ideals it pursues.
- **State Description:** Opening any file, you can see which solution it serves, why that solution exists and what better would mean for it, without asking anyone.
- **Hints of Measurement:** Every file reaches a solution and every solution reaches a problem and an ideal.
- **Opposes:** PR1, PR5

### ID2 Metric-chosen defaults
- **Name:** Metric-chosen defaults
- **Principle:** The implementation that runs is the one the solution's authoritative metric ranks best.
- **State Description:** When an alternative measures better it becomes the default without debate; when results tie, the record says so and why the default was kept.
- **Hints of Measurement:** Every selected implementation is the measured winner or a declared tie.
- **Opposes:** PR2

### ID3 Trustworthy evidence
- **Name:** Trustworthy evidence
- **Principle:** Every number can be reproduced from a commit and a case set, and only like is compared with like.
- **State Description:** Seeing a result, you know exactly what code and cases produced it and can rerun it; numbers live in one place and are never retyped.
- **Hints of Measurement:** Every result carries its commit and case hash on clean code, and no number appears outside the results.
- **Opposes:** PR3

### ID4 Effortless substitution
- **Name:** Effortless substitution
- **Principle:** Switching the implementation of a solution is a change of data, not of code.
- **State Description:** An operator or an embedding system picks a different implementation by name, and a mistyped name stops with the valid choices.
- **Hints of Measurement:** Switching needs no call-site edit and an unknown name always fails loudly.
- **Opposes:** PR4

### ID5 Purposeful code
- **Name:** Purposeful code
- **Principle:** Nothing exists that serves no solution, and every part is small enough to understand in one reading.
- **State Description:** The repository holds only what earns its place, each module has one role, and deleting dead code is routine.
- **Hints of Measurement:** No file without a component, no component without a solution, no module over the size ceiling.
- **Opposes:** PR5

### ID6 Self-enforcing structure
- **Name:** Self-enforcing structure
- **Principle:** A structural rule is enforced by the structure, at the moment it is broken.
- **State Description:** An agent who has never read the rules still cannot commit a violation unnoticed, and the report names the rule and the path.
- **Hints of Measurement:** Every injected violation is caught and a clean tree is never flagged.
- **Opposes:** PR6

### ID7 Review by metric
- **Name:** Review by metric
- **Principle:** People steer by reviewing problems, ideals, metrics and results, never by reading implementations.
- **State Description:** Joshua opens one sheet, sees each solution's ideal, metric, current result and verdict, corrects any of them there, and the correction reaches the source.
- **Hints of Measurement:** Every review decision can be made and recorded from the sheet.
- **Opposes:** PR7

### ID8 Faithful measurement
- **Name:** Faithful measurement
- **Principle:** What is measured is what ships.
- **State Description:** Every evaluation drives the live code path, so a better score means better behaviour for users.
- **Hints of Measurement:** Every measured implementation calls shipped code, and every case set can tell a broken implementation from a sound one.
- **Opposes:** PR8, PR3

### ID9 Sound integration
- **Name:** Sound integration
- **Principle:** A system built on a library meets the same standard as the library, through the library's own checks and cases.
- **State Description:** The embedding system knows which library solution each of its parts serves, its own stores pass the library's cases, and it sees at once when its pin falls behind.
- **Hints of Measurement:** The embedding's check passes with no unmapped part, no unscored store and no unexplained lag.
- **Opposes:** PR9

### ID10 Living template
- **Name:** Living template
- **Principle:** The template's author changes it in one place and every record follows.
- **State Description:** Joshua refines a field in the skill, the registry learns of it on the next check, and the missing entries are named.
- **Hints of Measurement:** The registry's fields always match the skill's template, and every record fills every required field.
- **Opposes:** PR10

### ID11 Adoptable structure
- **Name:** Adoptable structure
- **Principle:** Another team can apply the same structure to its own code by following one standard and reusing this library's tools.
- **State Description:** A developer reads the standard, adds records and an evaluation folder, runs the same checks, and has measured selection in their own repository.
- **Hints of Measurement:** A new solution or a new repository reaches a passing check by following the standard alone.
- **Opposes:** PR11

### ID12 Proportionate structure
- **Name:** Proportionate structure
- **Principle:** The structure costs less than it returns, and a small change carries a small cost.
- **State Description:** Contributors find the structure helps them, small fixes stay small, and parts of the structure that stop paying are removed.
- **Hints of Measurement:** The effort and time the structure adds to a change stays small next to what it catches.
- **Opposes:** PR12

## Solutions

### SO1 Intent registry
- **Name:** Intent registry
- **Scoped Purpose:** Use for recording every problem, solution, implementation, ideal and metric of a repository as linked records that people and checks both read. Avoids holding results (those belong to the results log) and avoids prose design documents.
- **Goals:** Every intent item is one record with every template field filled; every link resolves both ways; every file reaches a solution through the ownership map.
- **Knowledge:** The intent template in the evolvable-structure skill; Joshua's Project Documentation board (solution definitions apart from implementations); requirements traceability practice.
- **Measures of Success:** A reader can follow any file to its problem and ideal, and every record is complete.
- **Parameters:** The template's fields per type.
- **Inputs:** Hand-edited records of each type, the ownership map.
- **Outputs:** A linked intent network that the check, the tracker and the selection read.
- **Effects (other than outputs):** None.
- **Other information on when and how to use the solution:** Add or edit a record before building a new capability; the check names anything missing.
- **Addresses:** PR1, PR5, PR7
- **Pursues:** ID1, ID5

### SO2 Template sync
- **Name:** Template sync
- **Scoped Purpose:** Use for deriving the registry's fields from the intent template in the skill, so the author's wording is the only definition. Avoids adding fields of its own or interpreting the template.
- **Goals:** The registry's fields equal the template's fields after every refinement.
- **Knowledge:** The skill's `SKILL.md` as the source of truth; derived-copy practice already used for the standing instructions.
- **Measures of Success:** A template refinement shows up as named missing fields on the next check, with no hand edit of any schema.
- **Parameters:** Path to the skill.
- **Inputs:** The skill's intent template.
- **Outputs:** A committed field list per type.
- **Effects (other than outputs):** Fails the check when the committed field list is stale.
- **Other information on when and how to use the solution:** Run after Joshua edits the template; public CI, which cannot read the skill, checks records against the committed list.
- **Addresses:** PR10
- **Pursues:** ID10

### SO3 Ownership map
- **Name:** Ownership map
- **Scoped Purpose:** Use for assigning every file to exactly one component and every component to the solutions it serves. Avoids describing what the code does (the solution records do that).
- **Goals:** No file unowned, no component serving nothing, no module past the size ceiling, imports pointing inward.
- **Knowledge:** Layered and hexagonal architecture; code owners practice; the repository's split rule.
- **Measures of Success:** Code that serves no solution is found and removed.
- **Parameters:** Layer order, size ceiling.
- **Inputs:** The file tree and the component records.
- **Outputs:** File-to-solution links and the generated component index.
- **Effects (other than outputs):** None.
- **Other information on when and how to use the solution:** A new file joins a component in the same change; a file that fits no solution is a sign the code should go.
- **Addresses:** PR5, PR1
- **Pursues:** ID5, ID1

### SO4 Implementation selection
- **Name:** Implementation selection
- **Scoped Purpose:** Use for choosing which implementation serves a swappable solution by name, configuration or table default. Avoids deciding which one is best (the leaderboard does) and avoids per-call branching.
- **Goals:** Switching is a data change; an unknown name fails with the choices; every listed implementation loads.
- **Knowledge:** Ports and adapters; plugin registries; lazy loading of optional dependencies.
- **Measures of Success:** Every switch works from configuration alone and no typo falls back silently.
- **Parameters:** Solution id, implementation name, configuration overrides.
- **Inputs:** The selection table.
- **Outputs:** The chosen implementation's class and its configuration type.
- **Effects (other than outputs):** Imports the chosen implementation lazily.
- **Other information on when and how to use the solution:** Every solution with a port has a table entry whose default equals the measured winner or a declared tie.
- **Addresses:** PR4, PR2
- **Pursues:** ID4, ID2

### SO5 Measurement harness
- **Name:** Measurement harness
- **Scoped Purpose:** Use for running each implementation of a solution against that solution's cases through the live code and recording the result with its provenance. Avoids ranking and avoids tests that only check code runs.
- **Goals:** Every eval solution has cases, a scorer and implementations that drive shipped code; every recorded result carries its commit, case hash, cost and tokens; a call budget stops a run.
- **Knowledge:** Evaluation practice for language models (held-out cases, staged sample sizes, judged rubrics); experiment tracking; the eval ladder of three, ten and thirty cases.
- **Measures of Success:** Any result can be rerun from its record, and no result was produced by code other than what ships.
- **Parameters:** Solution, implementation, case subset, call budget.
- **Inputs:** Case files, the implementation, any live services the cases need.
- **Outputs:** A results row per run.
- **Effects (other than outputs):** Model spend on live runs; refuses to run against production.
- **Other information on when and how to use the solution:** Start live runs small and stop at the budget; re-record on committed code after any change to measured code or cases.
- **Addresses:** PR2, PR3, PR8
- **Pursues:** ID3, ID8

### SO6 Leaderboard
- **Name:** Leaderboard
- **Scoped Purpose:** Use for deciding, from recorded results, which implementation of a solution is best or whether they tie. Avoids running anything and avoids comparing results from different case sets.
- **Goals:** A win is called only outside the noise margin; ties, losses and unmeasured arms are labelled as such; comparison-only arms are never rivals.
- **Knowledge:** Statistical noise in small judged samples; cost and token accounting; Pareto comparison of quality and cost.
- **Measures of Success:** Its verdicts match known rankings on pinned cases and never call a tie a win.
- **Parameters:** Noise margin and spend tolerance per component.
- **Inputs:** The results log.
- **Outputs:** A verdict per solution and a ranked board.
- **Effects (other than outputs):** None.
- **Other information on when and how to use the solution:** The check requires the selected implementation to be the winner or a declared tie with a reason.
- **Addresses:** PR2, PR3
- **Pursues:** ID2, ID3

### SO7 Discriminating cases
- **Name:** Discriminating cases
- **Scoped Purpose:** Use for proving that a solution's cases can tell a sound implementation from a naive one, especially for rules where best cannot vary. Avoids inventing rivals that exist only to lose a comparison.
- **Goals:** Every invariant solution has at least one naive baseline that fails its cases.
- **Knowledge:** Mutation testing; the gap between a passing test and a meaningful one.
- **Measures of Success:** No case set passes everything that is put in front of it.
- **Parameters:** None.
- **Inputs:** A solution's cases and its naive baselines.
- **Outputs:** A pass or fail per baseline.
- **Effects (other than outputs):** None.
- **Other information on when and how to use the solution:** Write the naive version a first draft would produce, not a deliberately silly one.
- **Addresses:** PR8, PR3
- **Pursues:** ID8

### SO8 Structure check
- **Name:** Structure check
- **Scoped Purpose:** Use for enforcing every structural rule on each change, before commit and in tests. Avoids judging code quality beyond the rules, and avoids rules no one can fix.
- **Goals:** Every rule violation is reported by rule and path; a clean tree passes; strict mode refuses results from uncommitted code; an exception lives only as a waiver with a reason that disappears when it stops applying.
- **Knowledge:** Architecture tests and linters; the repository's numbered rules; the leaderboard (reused, not copied).
- **Measures of Success:** Every injected violation is caught, nothing clean is flagged, and it runs fast enough that nobody skips it.
- **Parameters:** Strict mode.
- **Inputs:** The repository, the registry, the results log, the waivers.
- **Outputs:** A list of violations and an exit code.
- **Effects (other than outputs):** Blocks a commit or a test run that breaks a rule.
- **Other information on when and how to use the solution:** Add a rule when a mistake has happened twice; delete a rule that stops catching anything.
- **Addresses:** PR6, PR3, PR5
- **Pursues:** ID6, ID3

### SO9 Review tracker
- **Name:** Review tracker
- **Scoped Purpose:** Use for putting the whole intent network and its current results in front of a human reviewer, and carrying their edits back. Avoids being a second source of truth for anything but review columns.
- **Goals:** Every record and its latest verdict appears in one sheet; reviewer edits survive rebuilds and flow back to the repository.
- **Knowledge:** Spreadsheets as the team's review medium; two-way sync keyed by record id.
- **Measures of Success:** Joshua can make and record every review decision from the sheet.
- **Parameters:** Which tabs, which columns a reviewer may edit.
- **Inputs:** The registry and the results log.
- **Outputs:** Generated tracker tables and the synced sheet.
- **Effects (other than outputs):** Writes the sheet.
- **Other information on when and how to use the solution:** Rebuild after any registry or result change; the check fails when the tracker is stale.
- **Addresses:** PR7
- **Pursues:** ID7

### SO10 Consumer check
- **Name:** Consumer check
- **Scoped Purpose:** Use for letting a system built on a library record which library solution each of its parts serves, score its own implementations with the library's cases, and see its version lag. Avoids copying the library's checks into the consumer and avoids putting the consumer's private data in the library.
- **Goals:** Every integration point maps to a library solution; every consumer store is scored by the library's cases; the pin's lag is visible.
- **Knowledge:** Consumer-driven contract testing; the library's own structure check and cases.
- **Measures of Success:** The consumer passes with nothing unmapped, unscored or unexplained.
- **Parameters:** The consumer's registry, root, requirements, solutions and results files; whether lag fails.
- **Inputs:** The consumer repository.
- **Outputs:** Violations and notes.
- **Effects (other than outputs):** None.
- **Other information on when and how to use the solution:** Run in the consumer's tests; bump the pin after the library's changes land.
- **Addresses:** PR9
- **Pursues:** ID9

### SO11 The standard
- **Name:** The standard
- **Scoped Purpose:** Use for teaching anyone, person or AI, how a solution is shaped in this structure and how another repository adopts it. Avoids repeating what the checks already enforce.
- **Goals:** One document gives the shape of a solution end to end and the steps to adopt it elsewhere.
- **Knowledge:** the adopting repositories as worked examples; the evolvable-structure skill.
- **Measures of Success:** Someone following it alone reaches a passing check.
- **Parameters:** None.
- **Inputs:** The registry's rules and examples.
- **Outputs:** The standard document.
- **Effects (other than outputs):** None.
- **Other information on when and how to use the solution:** Read first; update in the same change as any rule.
- **Addresses:** PR11, PR6
- **Pursues:** ID11

### SO12 Structure budget
- **Name:** Structure budget
- **Scoped Purpose:** Use for keeping the structure's own cost in view and pruning what stops paying. Avoids removing rules that still catch real mistakes.
- **Goals:** The effort the structure adds to a change is known, and rules, records and checks that catch nothing are removed.
- **Knowledge:** Principle 12 (minimalism) and the skill's difficulties; developer-experience research.
- **Measures of Success:** Small changes stay small and every rule has caught something real.
- **Parameters:** None yet.
- **Inputs:** The check's history, time per check, files touched per change.
- **Outputs:** A periodic report of cost against catches.
- **Effects (other than outputs):** Proposes removals.
- **Other information on when and how to use the solution:** Not built yet; this record holds the place so the cost is not forgotten.
- **Addresses:** PR12
- **Pursues:** ID12

## Implementations

### IM1 Hand-edited CSV records in the repository (Intent registry, selected)
- **Name:** CSV records in the repository
- **Description:** One CSV per intent type under `docs/structure/`, edited by hand and read by the check, the tracker and the selection.
- **Advantages:** Versioned with the code it describes, diffable, readable by any tool and any AI, public with the repository.
- **Disadvantages:** Long text is awkward in CSV, and concurrent edits by several agents can collide.
- **Implements:** SO1

### IM2 Records beside the code (Intent registry, alternative)
- **Name:** Records beside the code
- **Description:** Each solution's intent lives in a small file inside its own folder, gathered by a script.
- **Advantages:** Intent sits next to the code it describes and moves with it.
- **Disadvantages:** Cross-cutting problems and ideals have no natural home, and the network is harder to see whole.
- **Implements:** SO1

### IM3 The sheet as source (Intent registry, alternative)
- **Name:** Sheet as source
- **Description:** The Google Sheet holds the records and the repository pulls a copy.
- **Advantages:** The easiest place for a person to write and refine.
- **Disadvantages:** Not versioned with the code, needs credentials, and a public repository cannot depend on a private sheet.
- **Implements:** SO1

### IM4 Parse the skill's template (Template sync, selected)
- **Name:** Template parser
- **Description:** A script reads the intent template's sections and fields from `SKILL.md` and writes the committed field list.
- **Advantages:** The author's words are the only definition, and a refinement needs no schema edit.
- **Disadvantages:** Depends on the template keeping a parseable shape; wording changes can rename fields.
- **Implements:** SO2

### IM5 Hand-kept field list (Template sync, alternative)
- **Name:** Hand-kept field list
- **Description:** Someone copies the template's fields into a schema when the template changes.
- **Advantages:** No parser to maintain.
- **Disadvantages:** Drifts exactly as the problem describes.
- **Implements:** SO2

### IM6 Component rows with path globs (Ownership map, selected)
- **Name:** Component rows
- **Description:** `components.csv` lists each component's layer, path globs, role and solutions; the check matches every file to exactly one row.
- **Advantages:** Small, explicit, checked on every change.
- **Disadvantages:** Globs need upkeep as files move.
- **Implements:** SO3

### IM7 Data table and resolver (Implementation selection, selected)
- **Name:** Selection table
- **Description:** A pure-data table lists each solution's implementations and default; a resolver turns a name, an override or the default into the class, loading it lazily.
- **Advantages:** No logic at call sites, optional dependencies load only when chosen, typos fail with the choices.
- **Disadvantages:** One more indirection to follow when reading code.
- **Implements:** SO4

### IM8 Package entry points (Implementation selection, alternative)
- **Name:** Entry-point plugins
- **Description:** Implementations register through Python package entry points.
- **Advantages:** Third parties add implementations without touching the library.
- **Disadvantages:** Discovery depends on installation state, and the default is harder to see.
- **Implements:** SO4

### IM9 In-repository harness (Measurement harness, selected)
- **Name:** Component harness
- **Description:** One folder per solution with cases, a scorer and implementation files that drive live code; `esoi run --record` appends provenance-stamped rows to `results.csv`.
- **Advantages:** Measures shipped code, versioned with it, no outside service.
- **Disadvantages:** Built and maintained by us; less tooling than dedicated eval platforms.
- **Implements:** SO5

### IM10 External eval platform (Measurement harness, alternative)
- **Name:** External eval platform
- **Description:** promptfoo, LangSmith or a similar tool runs the cases and stores results.
- **Advantages:** Mature reporting and comparison views.
- **Disadvantages:** Results outside the repository, harder to tie to the selection and the check, often tests prompts apart from the shipped code.
- **Implements:** SO5

### IM11 Margin-aware leaderboard (Leaderboard, selected)
- **Name:** Margin leaderboard
- **Description:** Compares the latest result of each implementation on the same case hash, calls a win only beyond a pass-rate margin or spend tolerance, and labels ties, losses, unmeasured and comparison-only arms.
- **Advantages:** Honest about noise; one ranking reused by the check.
- **Disadvantages:** Fixed margins are a rough stand-in for proper confidence intervals.
- **Implements:** SO6

### IM12 Naive baselines in `broken/` (Discriminating cases, selected)
- **Name:** Broken baselines
- **Description:** Each invariant solution keeps naive implementations in its `broken/` folder, and one test proves each fails the cases.
- **Advantages:** Cheap proof that the cases mean something.
- **Disadvantages:** Proves only against the naive versions someone thought to write.
- **Implements:** SO7

### IM13 Numbered rule script (Structure check, selected)
- **Name:** Rule script
- **Description:** `esoi check` runs numbered rules over the tree, registry and results, with strict mode and waivers.
- **Advantages:** One place for every rule, fast, runs before commit and in tests.
- **Disadvantages:** A custom tool to maintain; rules can accumulate.
- **Implements:** SO8

### IM14 Generated tracker and two-way sheet (Review tracker, selected)
- **Name:** Tracker and sheet
- **Description:** `esoi tracker build` generates the tracker tables from the registry and results; `esoi sheet-sync` merges them two-way with the Google Sheet by record id, keeping reviewer columns.
- **Advantages:** The reviewer works in a sheet while the repository stays the source.
- **Disadvantages:** Only review columns flow back, so other edits in the sheet are overwritten.
- **Implements:** SO9

### IM15 Library command for consumers (Consumer check, selected)
- **Name:** Consumer command
- **Description:** `esoi consumer check` reads the consumer's own registry, requirements and results, and the library's cases score the consumer's stores through `--impl module:build`.
- **Advantages:** One implementation of the checks for every consumer; private cases stay private.
- **Disadvantages:** The consumer must keep its registry in the library's shape.
- **Implements:** SO10

### IM16 STANDARD.md (The standard, selected)
- **Name:** Standard document
- **Description:** `docs/structure/STANDARD.md` gives the shape of a solution end to end and the adoption steps.
- **Advantages:** One short document to read first.
- **Disadvantages:** Prose can drift from the rules unless updated with them.
- **Implements:** SO11

## Metrics

Metric has only a name in the template so far; the other fields wait for it.

### ME1 Trace completeness
- **Name:** Trace completeness: share of files that reach a problem and an ideal through a component and a solution, and share of records with every template field filled
- **Solution:** SO1, SO3
- **Ideals:** ID1, ID5

### ME2 Template agreement
- **Name:** Template agreement: whether the registry's fields equal the skill template's fields, and the count of required fields left empty after a refinement
- **Solution:** SO2
- **Ideals:** ID10

### ME3 Resolution correctness
- **Name:** Resolution correctness: share of selection cases (name, override, default, typo, every listed implementation) that resolve as specified
- **Solution:** SO4
- **Ideals:** ID4

### ME4 Provenance completeness
- **Name:** Provenance completeness: share of latest results with a clean commit, a case hash, cost and tokens, run through shipped code
- **Solution:** SO5
- **Ideals:** ID3, ID8

### ME5 Ranking correctness
- **Name:** Ranking correctness: share of pinned result sets where the leaderboard's verdict matches the known right verdict, including ties and different case sets
- **Solution:** SO6
- **Ideals:** ID2, ID3

### ME6 Case discrimination
- **Name:** Case discrimination: share of invariant solutions whose naive baselines all fail the cases
- **Solution:** SO7
- **Ideals:** ID8

### ME7 Violation detection
- **Name:** Violation detection: share of injected violations reported by the right rule and path, with no flag on a clean tree, and the check's run time
- **Solution:** SO8
- **Ideals:** ID6

### ME8 Review coverage
- **Name:** Review coverage: share of records and verdicts present in the sheet, and share of reviewer edits that survive a rebuild and reach the repository
- **Solution:** SO9
- **Ideals:** ID7

### ME9 Consumer soundness
- **Name:** Consumer soundness: unmapped integration points, consumer stores not scored by the library's cases, and commits of pin lag
- **Solution:** SO10
- **Ideals:** ID9

### ME10 Adoption effort
- **Name:** Adoption effort: steps and files needed for a newcomer, following only the standard, to add a passing solution or a passing new repository
- **Solution:** SO11
- **Ideals:** ID11

### ME11 Structure cost against catches
- **Name:** Structure cost against catches: time and files the structure adds per change, against real violations it caught
- **Solution:** SO12
- **Ideals:** ID12

## Open questions for review

1. Should each type link both ways as written here (a problem lists its ideals and solutions; an ideal lists the problems it opposes), or only in the direction "Connects to" names?
2. Do SO5 Measurement harness and SO6 Leaderboard deserve separate solutions? They are separate here because their "best" differs: faithful recording against honest ranking.
3. SO12 Structure budget has no implementation yet. Keep it as a placeholder, or drop it until it is needed?
4. The behaviour of AI under ESOI (behave-by-esoi) and its judge are runtime solutions of an adopting repository and are not in this network. Should they move here?
