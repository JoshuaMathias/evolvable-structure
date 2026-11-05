# Evolvable Structure that Optimizes Intent (ESOI)

Every intention is turned into a structure that optimizes the fulfilling of that intent while supporting changes to it, and the intent and the structure evolve together in a continual feedback loop.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

## How the solutions fit together

ESOI turns an intention into a structure that keeps fulfilling it while both change, and Apply ESOI to a Project is how a project takes that up, in the order the work happens. Apply ESOI to a Project teaches people through The Standard, guides agents through ESOI Applied to AI Behaviour, keeps the records true through the Rule Engine, moves each selection to the measured winner through Promote the Winner, serves each call through Implementation Selection, finds the records a request concerns through Spec Search, records one piece of work's metric before and after through Keep a Metric Record, finds which projects apply ESOI through the Local ESOI Index, and checks a system built on the library through Consumer Check. The Standard shows how a solution is shaped and how a repository adopts it, drawing on Documentation and Templates, The ESOI Steps and the public skill that Skill Distribution publishes. ESOI Applied to AI Behaviour gives an agent the skill as standing instructions and measures its replies case by case, with the ESOI Behaviour Judge grading the replies a pattern cannot settle. To keep the records true, the Rule Engine applies every rule it holds through the Structure Rules, each rule kept only while the Structure Budget says it pays and with the Ownership Map tying every file to a component, keeps the record fields in step with the author's template through Template Sync, regenerates the pages of Readable Records and the Review Tracker sheet, and reads standings from the Implementation Leaderboard. Template Sync parses the template that the Intent Registry records follow. The Review Tracker puts the Intent Registry records, the Implementation Leaderboard standings and the fields kept in step by Template Sync in front of a reviewer. Behind each selection, the Measurement Harness runs each implementation on its solution's cases, proves through Discriminating Cases that those cases can fail, follows When Metrics Are Run for when a stage may run and what it may spend, asks Know What a Result Measures which recorded rows are stale, consults Grade Public Evidence before it pays to measure what others have measured, and hands its rows to the Implementation Leaderboard, which Grade Public Evidence reads as well. Promote the Winner switches a solution's selection when the Implementation Leaderboard shows a clear winner among the rows the Measurement Harness recorded, then updates the Review Tracker sheet and the declarations that Specify from the Code keeps in step with the Intent Registry. Implementation Selection then serves each call with the selected implementation by name, configuration or recorded default, and its declarations grow into the sub-intent ESOI Inside Other People's Running Code. When new work starts, Spec Search ranks the records a request concerns over the narrowed set the Specification Index gives it. Keep a Metric Record reads the slice the Specification Index gives for the work it records. The Local ESOI Index says where to look first in each project. Consumer Check scores a system built on the library with the library's own cases and shows how far its pinned version lags.

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Apply ESOI to a Project<br/><i>apply-esoi</i>"]
    s1["Intent Registry<br/><i>intent-registry</i>"]
    s2["Template Sync<br/><i>template-sync</i>"]
    s3["Ownership Map<br/><i>ownership-map</i>"]
    s4["Implementation Selection<br/><i>implementation-selection</i>"]
    s5["Measurement Harness<br/><i>measurement-harness</i>"]
    s6["Implementation Leaderboard<br/><i>leaderboard</i>"]
    s7["Discriminating Cases<br/><i>discriminating-cases</i>"]
    s8["Rule Engine<br/><i>structure-check</i>"]
    s9["Structure Rules<br/><i>structure-rules</i>"]
    s10["Review Tracker<br/><i>review-tracker</i>"]
    s11["Consumer Check<br/><i>consumer-check</i>"]
    s12["The Standard<br/><i>the-standard</i>"]
    s13["Structure Budget<br/><i>structure-budget</i>"]
    s14["When Metrics Are Run<br/><i>when-metrics-are-run</i>"]
    s15["Skill Distribution<br/><i>skill-distribution</i>"]
    s16["ESOI Applied to AI Behaviour<br/><i>esoi-for-ai</i>"]
    s17["The ESOI Steps<br/><i>the-steps</i>"]
    s18["Documentation and Templates<br/><i>docs-and-templates</i>"]
    s19["ESOI Behaviour Judge<br/><i>esoi-behaviour-judge</i>"]
    s20["Specify from the Code<br/><i>specify-from-code</i>"]
    s21["Readable Records<br/><i>readable-records</i>"]
    s22["Promote the Winner<br/><i>promote-the-winner</i>"]
    s23["Specification Index<br/><i>spec-index</i>"]
    s24["Keep a Metric Record<br/><i>keep-metric-record</i>"]
    s25["Spec Search<br/><i>spec-search</i>"]
    s26["Grade Public Evidence<br/><i>public-evidence</i>"]
    s27["Know What a Result Measures<br/><i>know-what-a-result-measures</i>"]
    s28["Local ESOI Index<br/><i>local-application-index</i>"]
    s1 -->|"A linked intent network that the check, the tracker and the selection read"| s2
    s1 -->|"A linked intent network that the check, the tracker and the selection read"| s10
    s1 -->|"A linked intent network that the check, the tracker and the selection read"| s20
    s2 -->|"A committed field list per type"| s8
    s2 -->|"A committed field list per type"| s10
    s3 -->|"File-to-solution links and the generated component index"| s9
    s4 -->|"The chosen implementation's class and its configuration type"| s0
    s5 -->|"A results row per run"| s22
    s6 -->|"A verdict per solution and a ranked board"| s5
    s6 -->|"A verdict per solution and a ranked board"| s8
    s6 -->|"A verdict per solution and a ranked board"| s10
    s6 -->|"A verdict per solution and a ranked board"| s22
    s6 -->|"A verdict per solution and a ranked board"| s26
    s7 -->|"A pass or fail per baseline"| s5
    s8 -->|"A list of violations, each led by its rule id, and an exit code"| s0
    s9 -->|"One problem line per violation, led by the rule id"| s8
    s10 -->|"Generated tracker tables and the synced sheet"| s8
    s10 -->|"Generated tracker tables and the synced sheet"| s22
    s11 -->|"Violations and notes"| s0
    s12 -->|"The standard document"| s0
    s13 -->|"A periodic report of cost against catches"| s9
    s14 -->|"A row per run in the results log with the commit and the hash of the cases; the strict check's verdict"| s5
    s15 -->|"A public skill folder, a plugin manifest and marketplace file, and an installed copy"| s12
    s16 -->|"The agent's reply and, for a judged run, a verdict with a reason"| s0
    s17 -->|"Linked records, a checked metric, measured implementations and a recorded selection; a short summary of how the steps were applied"| s0
    s17 -->|"Linked records, a checked metric, measured implementations and a recorded selection; a short summary of how the steps were applied"| s12
    s18 -->|"Explanations, guides and generated templates"| s0
    s18 -->|"Explanations, guides and generated templates"| s12
    s19 -->|"A verdict (pass or fail) and a one-line reason"| s16
    s20 -->|"Findings (rule S30), the rows written, and for a new solution the records, a code skeleton and an evaluation folder"| s22
    s21 -->|"A README.md in the intent's folder"| s8
    s22 -->|"Edits to selected, selected_by and the metric's command, or a printed proposal"| s0
    s23 -->|"An index (JSON-serializable: entries with id, kind, title, summary, links, weighted terms, digest, plus document frequencies), a ranked list of record ids, or a record shown at a tier"| s24
    s23 -->|"An index (JSON-serializable: entries with id, kind, title, summary, links, weighted terms, digest, plus document frequencies), a ranked list of record ids, or a record shown at a tier"| s25
    s24 -->|"From begin, the NEXT PRIORITY block for the brief; from finish, the reconciled MetricResult rows (solution_id, metric_id, name, milestone, before, after, delta, source, reason, disagrees) and whether the work did anything for them to describe"| s0
    s25 -->|"A Selection: ranked items best first with their linked items, the candidates, which search proposed each, the number of judge calls, the route and the no-solution cue"| s0
    s26 -->|"Dict(Tuple(str, str), Estimate)"| s5
    s27 -->|"Stale or current for the row, the reason naming the changed file and its owner, and the files that were ignored with their owners"| s5
    s28 -->|"The project containing the path with its first file to read and its specifications, the ids related in a given way, or the listed ids"| s0
```

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| Apply ESOI to a Project | `apply-esoi` | `esoi.run("apply-esoi", '.')` | Documents, templates and tools together (`documents-templates-and-tools`) | Adoption effort, Intents whose solutions one paragraph and one diagram explain as the code builds them |
| Intent Registry | `intent-registry` | `esoi.run("intent-registry", '.')` | Records beside the code (`beside_code`) | Navigable records, Record completeness |
| Template Sync | `template-sync` | `esoi.run("template-sync", '.')` | Template parser (`template-parser`) | Template agreement |
| Ownership Map | `ownership-map` | `esoi.run("ownership-map", '.')` | Component rows (`component-rows`) | Trace completeness |
| Implementation Selection | `implementation-selection` | `esoi.run("implementation-selection", 'structure-check')` | Declarations in code (`declarations`) | Resolution correctness |
| Measurement Harness | `measurement-harness` | `esoi.run("measurement-harness", '.')` | Component harness (`component-harness`) | Provenance completeness |
| Implementation Leaderboard | `leaderboard` | `esoi.run("leaderboard", '.')` | Margin leaderboard (`margin-leaderboard`) | Ranking correctness |
| Discriminating Cases | `discriminating-cases` | `esoi.run("discriminating-cases", '.')` | Broken baselines (`broken-baselines`) | Case discrimination |
| Rule Engine | `structure-check` | `esoi.run("structure-check", '.')` | Rule script (`rule-script`) | Check dependability |
| Structure Rules | `structure-rules` | `esoi.run("structure-rules", '.')` | Numbered rule modules (`rule-modules`) | Violation detection |
| Review Tracker | `review-tracker` | `esoi.run("review-tracker", '.')` | Tracker and sheet (`tracker-and-sheet`) | Review coverage |
| Consumer Check | `consumer-check` | `esoi.run("consumer-check", 'esoi')` | Consumer command (`consumer-command`) | Consumer soundness |
| The Standard | `the-standard` | `esoi.run("the-standard", '.')` | Standard document (`standard-document`) | Adoption effort |
| Structure Budget | `structure-budget` | `esoi.run("structure-budget", '.')` | Written weighing rule (`written-weighing-rule`) | Structure cost against catches |
| When Metrics Are Run | `when-metrics-are-run` | `esoi.run("when-metrics-are-run", '.')` | On a decision (`on-a-decision`) | Decisions backed by current results |
| Skill Distribution | `skill-distribution` | `esoi.run("skill-distribution", '.')` | Generated public copy (`generated-public-copy`) | Skill copy agreement and leaks |
| ESOI Applied to AI Behaviour | `esoi-for-ai` | `esoi.run("esoi-for-ai", '.')` | Skill as standing instructions (`skill-as-standing-instructions`) | Behaviour adherence |
| The ESOI Steps | `the-steps` | `esoi.run("the-steps", '.')` | The ESOI steps (`esoi-steps`) | Steps followed |
| Documentation and Templates | `docs-and-templates` | `esoi.run("docs-and-templates", '.')` | Documentation folder (`documentation-folder`) | Newcomer effort |
| ESOI Behaviour Judge | `esoi-behaviour-judge` | `esoi.run("esoi-behaviour-judge", '.')` | Model judge on the rubric (`model-judge-on-the-rubric`) | Judge agreement |
| Specify from the Code | `specify-from-code` | `esoi.run("specify-from-code", '.')` | Declarations read from the code, rows synced (`declarations-and-sync`) | Declaration sync |
| Readable Records | `readable-records` | `esoi.run("readable-records", '.')` | At a glance, full record below (`at_a_glance`) | README glanceability, README fidelity |
| Promote the Winner | `promote-the-winner` | `esoi.run("promote-the-winner", '.')` | Promotion on the leaderboard's verdict (`margin-promotion`) | Promotion correctness |
| Specification Index | `spec-index` | `esoi.run("spec-index", ...)` | Field-weighted TF-IDF over the index (`weighted-tfidf`) | Specification recall at k |
| Keep a Metric Record | `keep-metric-record` | `esoi.run("keep-metric-record", '.')` | Library modules (`library-modules`) | Metric record kept |
| Spec Search | `spec-search` | `esoi.run("spec-search", ...)` | Lexical vector gated (`lexical-vector-gated`) | Spec search correctness |
| Grade Public Evidence | `public-evidence` | `esoi.run("public-evidence", {'evidence': []})` | Letter grades by weighted evidence (`graded`) | Public evidence graded |
| Know What a Result Measures | `know-what-a-result-measures` | `esoi.run("know-what-a-result-measures", '.')` | Import closure (`import_closure`) | Staleness precision |
| Local ESOI Index | `local-application-index` | `esoi.run("local-application-index", '.')` | Index folder in the user's home (`live_index`) | Local index lookup cases |

## Problems and ideals

**Problems**

- Intent lost between person and code (`prob-intent-lost-between-person-and-code`): What someone meant when they asked for a capability lives in their head, a chat or a task, and the code that answers it carries little of that meaning.
- Best alternative unknown (`prob-best-alternative-unknown`): Most parts of a system can be done several ways (a model tier, a router, a retrieval method), and the one in use was chosen by whoever wrote it, not by evidence.
- Measurements untrusted (`prob-measurements-untrusted`): A number recorded on uncommitted code, on a different case set, typed by hand, or copied into prose that goes stale looks like evidence but cannot be reproduced.
- Switching means editing code (`prob-switching-means-editing-code`): Switching a provider, runner or backend means finding and editing the call sites, often an `if` chain, and an embedding system cannot switch without forking.
- Purposeless, oversized code (`prob-purposeless-oversized-code`): Files that cannot be traced to a purpose stay because deleting them feels risky, and modules grow until they are too long to read whole (one adapter file reached thousands of lines).
- Structure rules decay (`prob-structure-rules-decay`): Rules written in prose (where files go, which way imports point, what must be documented) are followed by whoever read them and broken by the next agent, and generated documents drift from what they describe.
- Review needs implementations (`prob-review-needs-implementations`): A person who wants to steer quality has to read implementations, because ideals, metrics and current results are not gathered anywhere they can read and correct.
- Evaluation detached from shipped code (`prob-evaluation-detached-from-shipped-code`): Evaluations built beside production code test copies, stubs or scripts of their own, so their results describe something that does not run.
- Embedding soundness unknown (`prob-embedding-soundness-unknown`): A system builds on a library's solutions with its own stores and prompts, but cannot see which library solution each of its parts serves, whether its parts meet the library's own cases, or how far its pinned version lags.
- Template copies drift (`prob-template-copies-drift`): The intent template is being refined in the skill, and every registry and checker that copied its fields falls out of date.
- and 18 more: all 28 are in [problems](#problems) of the full record below

**Ideals**

- Explicit intent (`ideal-explicit-intent`): Every built part traces to the problems it addresses and the ideals it pursues.
- Metric-chosen defaults (`ideal-metric-chosen-defaults`): The implementation that runs is the one the solution's authoritative metric ranks best.
- Trustworthy evidence (`ideal-trustworthy-evidence`): Every number can be reproduced from the code and the cases that produced it, and only like is compared with like.
- Effortless substitution (`ideal-effortless-substitution`): Switching the implementation of a solution changes no code that depends on it.
- Purposeful code (`ideal-purposeful-code`): Nothing exists that serves no solution, and every part is small enough to understand in one reading.
- Self-enforcing structure (`ideal-self-enforcing-structure`): A broken structural rule is noticed at the moment it is broken, and whoever broke it is told what to do next.
- Review by metric (`ideal-review-by-metric`): People can steer by reviewing problems, ideals, metrics and results alone, without needing to read implementations; anyone may still review or improve an implementation, and that still adds value.
- Faithful measurement (`ideal-faithful-measurement`): What is measured is what ships.
- Sound integration (`ideal-sound-integration`): A system built on a library meets the same standard as the library, through the library's own checks and cases.
- Living template (`ideal-living-template`): When the template's author refines it, every record and every tool that reads records follows.
- and 15 more: all 25 are in [ideals](#ideals) of the full record below

## Metrics and their leaders

- Trace completeness (`metric-trace-completeness`): leader `live_checker`, 12 of 16 cases
- Template agreement (`metric-template-agreement`): leader `live_parser`, 11 of 11 cases
- Resolution correctness (`metric-resolution-correctness`)
- Provenance completeness (`metric-provenance-completeness`): leader `live_harness`, 27 of 28 cases
- Ranking correctness (`metric-ranking-correctness`): leader `live_leaderboard`, 54 of 54 cases
- Case discrimination (`metric-case-discrimination`)
- Violation detection (`metric-violation-detection`): leader `live_checker`, 61 of 76 cases
- Check dependability (`metric-check-dependability`): leader `live_checker`, 61 of 76 cases
- Review coverage (`metric-review-coverage`): leader `live_tracker`, 10 of 10 cases
- Consumer soundness (`metric-consumer-soundness`): leader `live_consumer_check`, 22 of 22 cases
- and 21 more: all 31 are in [metrics](#metrics) of the full record below

## Where to go next

- Sub-intent: [ESOI Inside Other People's Running Code](../implementations/python/esoi/esoi-runtime/README.md) (The esoi package is a dependency of other people's production code, which declares its alternatives gracefully and selects the best implementation while it runs.)
- Repository: [top README](../README.md)
- Records beside the code: [implementations/python/esoi](../implementations/python/esoi/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [implementations.csv](implementations.csv), [metrics.csv](metrics.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- Intent lost between person and code (`prob-intent-lost-between-person-and-code`): What someone meant when they asked for a capability lives in their head, a chat or a task, and the code that answers it carries little of that meaning.
- Best alternative unknown (`prob-best-alternative-unknown`): Most parts of a system can be done several ways (a model tier, a router, a retrieval method), and the one in use was chosen by whoever wrote it, not by evidence.
- Measurements untrusted (`prob-measurements-untrusted`): A number recorded on uncommitted code, on a different case set, typed by hand, or copied into prose that goes stale looks like evidence but cannot be reproduced.
- Switching means editing code (`prob-switching-means-editing-code`): Switching a provider, runner or backend means finding and editing the call sites, often an `if` chain, and an embedding system cannot switch without forking.
- Purposeless, oversized code (`prob-purposeless-oversized-code`): Files that cannot be traced to a purpose stay because deleting them feels risky, and modules grow until they are too long to read whole (one adapter file reached thousands of lines).
- Structure rules decay (`prob-structure-rules-decay`): Rules written in prose (where files go, which way imports point, what must be documented) are followed by whoever read them and broken by the next agent, and generated documents drift from what they describe.
- Review needs implementations (`prob-review-needs-implementations`): A person who wants to steer quality has to read implementations, because ideals, metrics and current results are not gathered anywhere they can read and correct.
- Evaluation detached from shipped code (`prob-evaluation-detached-from-shipped-code`): Evaluations built beside production code test copies, stubs or scripts of their own, so their results describe something that does not run.
- Embedding soundness unknown (`prob-embedding-soundness-unknown`): A system builds on a library's solutions with its own stores and prompts, but cannot see which library solution each of its parts serves, whether its parts meet the library's own cases, or how far its pinned version lags.
- Template copies drift (`prob-template-copies-drift`): The intent template is being refined in the skill, and every registry and checker that copied its fields falls out of date.
- Others cannot adopt (`prob-others-cannot-adopt`): There is no worked, checked example of evolvable structure in code, so each team that wants it designs its own from prose.
- Structure costs more than it returns (`prob-structure-costs-more-than-it-returns`): Every rule, record and check adds work to each change, and past a point contributors spend more time satisfying the structure than improving the code.
- Metrics run at the wrong time (`prob-metrics-run-at-the-wrong-time`): Results are stale when a choice depends on them, or paid runs happen with no decision behind them, so people either decide on numbers that no longer describe the code or stop running the metrics at all.
- Skill cannot be reached safely (`prob-skill-cannot-be-reached-safely`): A person who wants to use the author's skill cannot get it in a form that is both complete and safe to publish.
- Records copy the code (`prob-records-copy-the-code`): The records repeat what the code already says: which alternatives of a solution exist, the file each lives in, and an interface's signature.
- Winner not adopted (`prob-winner-not-adopted`): A rival that clearly beats the selected implementation on the solution's own metric stays unadopted until someone notices and edits the selection, the metric's command and the record of why, by hand.
- Records unreadable at a glance (`prob-records-unreadable-at-a-glance`): An intent's folder of CSV files states it completely, but a person clicking into it cannot tell at a glance what the intent is for, how its solutions fit or where to go next: that takes opening several files and following ids between them.
- Simulated arm shows a false loss (`prob-simulated-arm-false-loss`): An arm that meters a deterministic stand-in for a model counts the calls a real model would make at no cost.
- Rules unjustified (`prob-rules-unjustified`): A rule is kept in code with no record of the mistake that justified it or of what it has caught since, so whether it still earns its place, or why its limit has its value, cannot be told without asking its author.
- Specifications not found for new input (`prob-intent-specs-not-found-for-new-input`): A new use case or input arrives, and it is hard for a person or an AI to tell which of a project's problems, ideals, solutions, implementations and metrics apply without reading most of them.
- Metric measures a stand-in (`prob-metric-measures-a-stand-in`): A metric scores a scripted judge, a mocked model or a canned answer instead of the real thing, so its number measures the plumbing around the thing and not the thing.
- Specifications hard to search (`prob-spec-search`): A system that finds a repository's records for a request, or finds them together with its own notes or documents, rebuilds the same stages inside its own code: lexical scoring, a semantic search, rank fusion, a confidence gate, one judging call and the way a ranked record brings its links.
- Specification far from the code (`prob-spec-far-from-code`): A person reading the code of a solution cannot find its specification without leaving the code tree: the records sit in a separate folder, a code folder carries no page that says what it is for, and a change to the code and to its spec happen in two places.
- Results called stale when what they measure did not change (`prob-results-stale-when-nothing-measured-changed`): A recorded result is called stale when any file of the repository's measured code changed, so every component's metrics are re-run after every commit although what most of them measure did not change.
- AI behaviour drifts from the principles (`prob-ai-behaviour-drifts-from-principles`): An AI agent asked to do work applies the principles inconsistently, and how often is rarely measured.
- No order to follow (`prob-no-order-to-follow`): People who want to apply ESOI have the five record types and the principles but no order to follow.
- Applied structure is rediscovered (`prob-applied-structure-is-rediscovered`): Where ESOI is already applied, how those projects relate and where to look in each is rediscovered in every session.
- Behaviour verdicts uncalibrated (`prob-behaviour-verdicts-uncalibrated`): A model that grades whether a reply acts by the principles can disagree with the people whose intent the principles express, can favour its own phrasing when it wrote the reply, and can pass a reply that uses the right words while doing the opposite.

### Ideals

- Explicit intent (`ideal-explicit-intent`): Every built part traces to the problems it addresses and the ideals it pursues.
- Metric-chosen defaults (`ideal-metric-chosen-defaults`): The implementation that runs is the one the solution's authoritative metric ranks best.
- Trustworthy evidence (`ideal-trustworthy-evidence`): Every number can be reproduced from the code and the cases that produced it, and only like is compared with like.
- Effortless substitution (`ideal-effortless-substitution`): Switching the implementation of a solution changes no code that depends on it.
- Purposeful code (`ideal-purposeful-code`): Nothing exists that serves no solution, and every part is small enough to understand in one reading.
- Self-enforcing structure (`ideal-self-enforcing-structure`): A broken structural rule is noticed at the moment it is broken, and whoever broke it is told what to do next.
- Review by metric (`ideal-review-by-metric`): People can steer by reviewing problems, ideals, metrics and results alone, without needing to read implementations; anyone may still review or improve an implementation, and that still adds value.
- Faithful measurement (`ideal-faithful-measurement`): What is measured is what ships.
- Sound integration (`ideal-sound-integration`): A system built on a library meets the same standard as the library, through the library's own checks and cases.
- Living template (`ideal-living-template`): When the template's author refines it, every record and every tool that reads records follows.
- Adoptable structure (`ideal-adoptable-structure`): Another team can apply the same structure to its own code by following one standard and reusing this library's tools.
- Proportionate structure (`ideal-proportionate-structure`): The structure costs less than it returns, and a small change carries a small cost.
- Timely affordable evidence (`ideal-timely-affordable-evidence`): Every choice between alternatives is backed by a current result, and what it cost to get was proportionate to the choice and approved.
- Installable skill (`ideal-installable-skill`): A stranger gets the author's current skill, complete and public-safe, in one step, while the author keeps one source of truth.
- Declared once (`ideal-declared-once`): Each fact is stated once, where it belongs, and every place that shows it agrees with it without anyone keeping a copy in step.
- Rules earn their place (`ideal-rules-earn-their-place`): Every rule can say which mistake it prevents, and is removed when it stops catching any.
- Right specification at the right time (`ideal-right-spec-at-the-right-time`): For any new use case or input, whoever applies a project's specifications works from the few that bear on it, at a small fraction of the cost of reading them all.
- Shared specification search (`ideal-spec-search`): An application that finds specifications for a request writes only what is its own, and every improvement to finding them reaches it without a change on its side.
- Glanceable intent (`ideal-glanceable-intent`): Anyone clicking into an intent folder sees on the first screen what the intent is, how its solutions fit together and where to go next.
- Navigable records (`ideal-navigable-records`): A person opening a code folder finds the specification of what it holds beside it, and a person opening a specification finds its code one folder away.
- Stale only when what it measures changed (`ideal-stale-only-when-measured-changed`): A recorded result goes stale if and only if the code, cases or circumstances it measures changed.
- Principled behaviour (`ideal-principled-behaviour`): An AI agent acts by the principles in its own work, including holding back where structure costs more than it returns, and keeps every qualifier when it restates one.
- Followable process (`ideal-followable-process`): Anyone applying ESOI can follow one stated order from purpose to selection by metric, sized to the work, and knows where to return when something changes.
- Found structure (`ideal-found-structure`): Structure that already exists is found and reused instead of rediscovered.
- Calibrated judging (`ideal-calibrated-judging`): A judge's verdicts agree with the human verdicts they stand in for, and where they disagree is known.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| Apply ESOI to a Project | `apply-esoi` | Documents, templates and tools together (`documents-templates-and-tools`) | Adoption effort, Intents whose solutions one paragraph and one diagram explain as the code builds them |
| Intent Registry | `intent-registry` | Records beside the code (`beside_code`) | Navigable records, Record completeness |
| Template Sync | `template-sync` | Template parser (`template-parser`) | Template agreement |
| Ownership Map | `ownership-map` | Component rows (`component-rows`) | Trace completeness |
| Implementation Selection | `implementation-selection` | Declarations in code (`declarations`) | Resolution correctness |
| Measurement Harness | `measurement-harness` | Component harness (`component-harness`) | Provenance completeness |
| Implementation Leaderboard | `leaderboard` | Margin leaderboard (`margin-leaderboard`) | Ranking correctness |
| Discriminating Cases | `discriminating-cases` | Broken baselines (`broken-baselines`) | Case discrimination |
| Rule Engine | `structure-check` | Rule script (`rule-script`) | Check dependability |
| Structure Rules | `structure-rules` | Numbered rule modules (`rule-modules`) | Violation detection |
| Review Tracker | `review-tracker` | Tracker and sheet (`tracker-and-sheet`) | Review coverage |
| Consumer Check | `consumer-check` | Consumer command (`consumer-command`) | Consumer soundness |
| The Standard | `the-standard` | Standard document (`standard-document`) | Adoption effort |
| Structure Budget | `structure-budget` | Written weighing rule (`written-weighing-rule`) | Structure cost against catches |
| When Metrics Are Run | `when-metrics-are-run` | On a decision (`on-a-decision`) | Decisions backed by current results |
| Skill Distribution | `skill-distribution` | Generated public copy (`generated-public-copy`) | Skill copy agreement and leaks |
| ESOI Applied to AI Behaviour | `esoi-for-ai` | Skill as standing instructions (`skill-as-standing-instructions`) | Behaviour adherence |
| The ESOI Steps | `the-steps` | The ESOI steps (`esoi-steps`) | Steps followed |
| Documentation and Templates | `docs-and-templates` | Documentation folder (`documentation-folder`) | Newcomer effort |
| ESOI Behaviour Judge | `esoi-behaviour-judge` | Model judge on the rubric (`model-judge-on-the-rubric`) | Judge agreement |
| Specify from the Code | `specify-from-code` | Declarations read from the code, rows synced (`declarations-and-sync`) | Declaration sync |
| Readable Records | `readable-records` | At a glance, full record below (`at_a_glance`) | README glanceability, README fidelity |
| Promote the Winner | `promote-the-winner` | Promotion on the leaderboard's verdict (`margin-promotion`) | Promotion correctness |
| Specification Index | `spec-index` | Field-weighted TF-IDF over the index (`weighted-tfidf`) | Specification recall at k |
| Keep a Metric Record | `keep-metric-record` | Library modules (`library-modules`) | Metric record kept |
| Spec Search | `spec-search` | Lexical vector gated (`lexical-vector-gated`) | Spec search correctness |
| Grade Public Evidence | `public-evidence` | Letter grades by weighted evidence (`graded`) | Public evidence graded |
| Know What a Result Measures | `know-what-a-result-measures` | Import closure (`import_closure`) | Staleness precision |
| Local ESOI Index | `local-application-index` | Index folder in the user's home (`live_index`) | Local index lookup cases |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Documents only, applied by hand | `apply-esoi:documents-only` |  |  |
| Sheet as source | `intent-registry:sheet-as-source` |  |  |
| Hand-kept field list | `template-sync:hand-kept-field-list` |  |  |
| Entry-point plugins | `implementation-selection:entry-point-plugins` |  |  |
| External eval platform | `measurement-harness:external-eval-platform` |  |  |
| Rules in prose | `structure-rules:prose-rules` |  |  |
| On every change | `when-metrics-are-run:on-every-change` |  |  |
| On a schedule | `when-metrics-are-run:on-a-schedule` |  |  |
| On drift | `when-metrics-are-run:on-drift` |  |  |
| Hand-copied folder | `skill-distribution:hand-copied-folder` |  |  |
| Publish the private folder | `skill-distribution:publish-the-private-folder` |  |  |
| Measured cost and catches | `structure-budget:measured-cost-and-catches` |  |  |
| Perspective review | `esoi-for-ai:perspective-review` |  |  |
| Project Documentation board checklist | `the-steps:board-checklist` |  |  |
| One-hour first pass | `the-steps:one-hour-pass` |  |  |
| No stated order | `the-steps:no-stated-order` |  |  |
| Human review of every reply | `esoi-behaviour-judge:human-review-of-every-reply` |  |  |
| Records kept by hand | `specify-from-code:hand-kept-records` |  |  |
| README written by hand | `readable-records:hand-written-readme` |  |  |
| A person edits the records | `promote-the-winner:person-edits-the-records` |  |  |
| Documents, templates and tools together | `apply-esoi:documents-templates-and-tools` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Records in the esoi folder | `intent-registry:esoi_folder` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Records beside the code | `intent-registry:beside_code` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Template parser | `template-sync:template-parser` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Component rows | `ownership-map:component-rows` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Declarations in code | `implementation-selection:declarations` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) | [esoi-runtime](esoi-runtime/README.md) |
| Component harness | `measurement-harness:component-harness` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Margin leaderboard | `leaderboard:margin-leaderboard` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Broken baselines | `discriminating-cases:broken-baselines` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Rule script | `structure-check:rule-script` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Numbered rule modules | `structure-rules:rule-modules` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Tracker and sheet | `review-tracker:tracker-and-sheet` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Consumer command | `consumer-check:consumer-command` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Standard document | `the-standard:standard-document` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| On a decision | `when-metrics-are-run:on-a-decision` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Generated public copy | `skill-distribution:generated-public-copy` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Written weighing rule | `structure-budget:written-weighing-rule` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Skill as standing instructions | `esoi-for-ai:skill-as-standing-instructions` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| The ESOI steps | `the-steps:esoi-steps` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Documentation folder | `docs-and-templates:documentation-folder` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Index folder in the user's home | `local-application-index:live_index` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Model judge on the rubric | `esoi-behaviour-judge:model-judge-on-the-rubric` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Declarations read from the code, rows synced | `specify-from-code:declarations-and-sync` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Record tables only | `readable-records:full_page` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| At a glance, full record below | `readable-records:at_a_glance` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Compact page of links | `readable-records:links_page` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Promotion on the leaderboard's verdict | `promote-the-winner:margin-promotion` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Field-weighted TF-IDF over the index | `spec-index:weighted-tfidf` | [implementations/python/esoi/spec_index.py](../implementations/python/esoi/spec_index.py) |  |
| Plain term overlap | `spec-index:term-overlap` | [implementations/python/esoi/spec_index.py](../implementations/python/esoi/spec_index.py) |  |
| Library modules | `keep-metric-record:library-modules` | [implementations/python/esoi/interfaces.py](../implementations/python/esoi/interfaces.py) |  |
| Lexical only | `spec-search:lexical-only` | [implementations/python/esoi/spec_search.py](../implementations/python/esoi/spec_search.py) |  |
| Lexical vector gated | `spec-search:lexical-vector-gated` | [implementations/python/esoi/spec_search.py](../implementations/python/esoi/spec_search.py) |  |
| Letter grades by weighted evidence | `public-evidence:graded` | [implementations/python/esoi/evidence.py](../implementations/python/esoi/evidence.py) |  |
| Repo wide | `know-what-a-result-measures:repo_wide` | [implementations/python/esoi/staleness.py](../implementations/python/esoi/staleness.py) |  |
| Component paths | `know-what-a-result-measures:component_paths` | [implementations/python/esoi/staleness.py](../implementations/python/esoi/staleness.py) |  |
| Import closure | `know-what-a-result-measures:import_closure` | [implementations/python/esoi/staleness.py](../implementations/python/esoi/staleness.py) |  |
| Skill on request | `esoi-for-ai:skill-on-request` | [implementations/python/evaluation/components/behave_by_esoi/impls/skill_on_request.py](../implementations/python/evaluation/components/behave_by_esoi/impls/skill_on_request.py) |  |
| No skill | `esoi-for-ai:no-skill` | [implementations/python/evaluation/components/behave_by_esoi/impls/no_skill.py](../implementations/python/evaluation/components/behave_by_esoi/impls/no_skill.py) |  |
| Routing rows in the skill's index | `local-application-index:skill_rows` | [implementations/python/evaluation/components/index_projects/impls/skill_rows.py](../implementations/python/evaluation/components/index_projects/impls/skill_rows.py) |  |
| Each project's own records only | `local-application-index:records_only` | [implementations/python/evaluation/components/index_projects/impls/records_only.py](../implementations/python/evaluation/components/index_projects/impls/records_only.py) |  |
| Regex checks only | `esoi-behaviour-judge:regex-checks-only` | [implementations/python/evaluation/components/judge_esoi_behaviour/impls/regex_only.py](../implementations/python/evaluation/components/judge_esoi_behaviour/impls/regex_only.py) |  |

### Metrics

- Trace completeness (`metric-trace-completeness`): `esoi run own_every_file --impl live_checker`
- Template agreement (`metric-template-agreement`): `esoi run sync_the_template --impl live_parser`
- Resolution correctness (`metric-resolution-correctness`): `none`
- Provenance completeness (`metric-provenance-completeness`): `esoi run measure_implementations --impl live_harness`
- Ranking correctness (`metric-ranking-correctness`): `esoi run rank_implementations --impl live_leaderboard`
- Case discrimination (`metric-case-discrimination`): `none`
- Violation detection (`metric-violation-detection`): `esoi run check_the_structure --impl live_checker`
- Check dependability (`metric-check-dependability`): `esoi run check_the_structure --impl live_checker`
- Review coverage (`metric-review-coverage`): `esoi run review_tracker --impl live_tracker`
- Consumer soundness (`metric-consumer-soundness`): `esoi run check_a_consumer --impl live_consumer_check`
- Adoption effort (`metric-adoption-effort`): `none`
- Structure cost against catches (`metric-structure-cost-against-catches`): `none`
- Decisions backed by current results (`metric-decisions-backed-by-current-results`): `esoi run know_stale_results --impl live_checker`
- Skill copy agreement and leaks (`metric-skill-copy-agreement`): `esoi run sync_the_skill --impl live_skill`
- Behaviour adherence (`metric-esoi-behaviour-adherence`): `esoi run behave_by_esoi --impl standing_instructions`
- Steps followed (`metric-steps-followed`): `none`
- Newcomer effort (`metric-docs-and-templates`): `none`
- Judge agreement (`metric-esoi-judge-agreement`): `esoi run judge_esoi_behaviour --impl model_judge`
- Record completeness (`metric-record-completeness`): `esoi run record_intent --impl live_checker`
- Declaration sync (`metric-declaration-sync`): `esoi run specify_from_code --impl live_declarations`
- README fidelity (`metric-readme-fidelity`): `esoi run readable_records --impl live_readme`
- README glanceability (`metric-readme-glanceability`): `esoi run readme_at_a_glance --impl at_a_glance; esoi run readme_at_a_glance --impl full_page; esoi run readme_at_a_glance --impl links_page`
- Promotion correctness (`metric-promotion-correctness`): `esoi run promote_the_winner --impl live_promote`
- Specification recall at k (`metric-spec-index-recall`): `esoi run spec_index --impl weighted_tfidf; esoi run spec_index --impl term_overlap`
- Metric record kept (`metric-keep-metric-record`): `esoi run keep_metric_record --impl live_record`
- Spec search correctness (`metric-spec-search`): `esoi run spec_search --impl gated; esoi run spec_search --impl lexical_only`
- Public evidence graded (`metric-public-evidence`): `esoi run public_evidence --impl graded`
- Intents whose solutions one paragraph and one diagram explain as the code builds them (`metric-solution-coherence`): `python3 -m esoi.coherence --gate`
- Navigable records (`metric-navigable-records`): `esoi run navigable_records --impl beside_code; esoi run navigable_records --impl esoi_folder`
- Staleness precision (`metric-staleness-precision`): `esoi run staleness_precision --impl repo_wide; esoi run staleness_precision --impl component_paths; esoi run staleness_precision --impl import_closure`
- Local index lookup cases (`metric-local-index-lookup`): `esoi run index_projects --impl live_index; esoi run index_projects --impl skill_rows; esoi run index_projects --impl records_only`
