These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Evolvable Structure that Optimizes Intent (ESOI)

ESOI turns an intention into a structure that keeps fulfilling it while both change, and Apply ESOI to a Project is how a project takes that up, in the order the work happens. Apply ESOI to a Project teaches people through The Standard, guides agents through ESOI Applied to AI Behaviour, keeps the records true through the Rule Engine, moves each selection to the measured winner through Promote the Winner, serves each call through Implementation Selection, finds the records a request concerns through Spec Search, records one piece of work's metric before and after through Keep a Metric Record, finds which projects apply ESOI through the Local ESOI Index, and checks a system built on the library through Consumer Check. The Standard shows how a solution is shaped and how a repository adopts it, drawing on Documentation and Templates, The ESOI Steps and the public skill that Skill Distribution publishes. ESOI Applied to AI Behaviour gives an agent the skill as standing instructions and measures its replies case by case, with the ESOI Behaviour Judge grading the replies a pattern cannot settle. To keep the records true, the Rule Engine applies every rule it holds through the Structure Rules, each rule kept only while the Structure Budget says it pays and with the Ownership Map tying every file to a component, keeps the record fields in step with the author's template through Template Sync, regenerates the pages of Readable Records and the Review Tracker sheet, and reads standings from the Implementation Leaderboard. Template Sync parses the template that the Intent Registry records follow. The Review Tracker puts the Intent Registry records, the Implementation Leaderboard standings and the fields kept in step by Template Sync in front of a reviewer. Behind each selection, the Measurement Harness runs each implementation on its solution's cases, proves through Discriminating Cases that those cases can fail, follows When Metrics Are Run for when a stage may run and what it may spend, asks Know What a Result Measures which recorded rows are stale, consults Grade Public Evidence before it pays to measure what others have measured, and hands its rows to the Implementation Leaderboard, which Grade Public Evidence reads as well. Promote the Winner switches a solution's selection when the Implementation Leaderboard shows a clear winner among the rows the Measurement Harness recorded, then updates the Review Tracker sheet and the declarations that Specify from the Code keeps in step with the Intent Registry. Implementation Selection then serves each call with the selected implementation by name, configuration or recorded default, and its declarations grow into the sub-intent ESOI Inside Other People's Running Code. When new work starts, Spec Search ranks the records a request concerns over the narrowed set the Specification Index gives it. Keep a Metric Record reads the slice the Specification Index gives for the work it records. The Local ESOI Index says where to look first in each project. Consumer Check scores a system built on the library with the library's own cases and shows how far its pinned version lags.

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
