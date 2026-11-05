These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Evolvable structure that optimizes intent (ESOI)

ESOI turns an intention into a structure that keeps fulfilling it while both change, and Apply ESOI to a Project is how a project takes that up, in the order the work happens. Apply ESOI to a Project teaches people through The Standard, guides agents through ESOI Applied to AI Behaviour, keeps the records true through the Rule Engine, moves each selection to the measured winner through Promote the Winner, serves each call through Implementation Selection, finds the records a request concerns through Spec Search, records one piece of work's metric before and after through Keep a Metric Record, finds which projects apply ESOI through the Local ESOI Index, and checks a system built on the library through Consumer Check. The Standard shows how a solution is shaped and how a repository adopts it, drawing on Documentation and Templates, The ESOI Steps and the public skill that Skill Distribution publishes. ESOI Applied to AI Behaviour gives an agent the skill as standing instructions and measures its replies case by case, with the ESOI Behaviour Judge grading the replies a pattern cannot settle. To keep the records true, the Rule Engine applies every rule it holds through the Structure Rules, each rule kept only while the Structure Budget says it pays and with the Ownership Map tying every file to a component, keeps the record fields in step with the author's template through Template Sync, regenerates the pages of Readable Records and the Review Tracker sheet, and reads standings from the Implementation Leaderboard. Template Sync parses the template that the Intent Registry records follow. The Review Tracker puts the Intent Registry records, the Implementation Leaderboard standings and the fields kept in step by Template Sync in front of a reviewer. Behind each selection, the Measurement Harness runs each implementation on its solution's cases, proves through Discriminating Cases that those cases can fail, follows When Metrics Are Run for when a stage may run and what it may spend, asks Know What a Result Measures which recorded rows are stale, consults Grade Public Evidence before it pays to measure what others have measured, and hands its rows to the Implementation Leaderboard, which Grade Public Evidence reads as well. Promote the Winner switches a solution's selection when the Implementation Leaderboard shows a clear winner among the rows the Measurement Harness recorded, then updates the Review Tracker sheet and the declarations that Specify from the Code keeps in step with the Intent Registry. Implementation Selection then serves each call with the selected implementation by name, configuration or recorded default, and its declarations grow into the sub-intent ESOI Inside Other People's Running Code. When new work starts, Spec Search ranks the records a request concerns over the narrowed set the Specification Index gives it. Keep a Metric Record reads the slice the Specification Index gives for the work it records. The Local ESOI Index says where to look first in each project. Consumer Check scores a system built on the library with the library's own cases and shows how far its pinned version lags.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Local ESOI index<br/><i>local-application-index</i>"]
    s1["Apply ESOI to a project<br/><i>apply-esoi</i>"]
    s2["Intent registry<br/><i>intent-registry</i>"]
    s3["Template sync<br/><i>template-sync</i>"]
    s4["Ownership map<br/><i>ownership-map</i>"]
    s5["Implementation selection<br/><i>implementation-selection</i>"]
    s6["Measurement harness<br/><i>measurement-harness</i>"]
    s7["Implementation leaderboard<br/><i>leaderboard</i>"]
    s8["Discriminating cases<br/><i>discriminating-cases</i>"]
    s9["Rule engine<br/><i>structure-check</i>"]
    s10["Structure rules<br/><i>structure-rules</i>"]
    s11["Review tracker<br/><i>review-tracker</i>"]
    s12["Consumer check<br/><i>consumer-check</i>"]
    s13["The standard<br/><i>the-standard</i>"]
    s14["Structure budget<br/><i>structure-budget</i>"]
    s15["When metrics are run<br/><i>when-metrics-are-run</i>"]
    s16["Skill distribution<br/><i>skill-distribution</i>"]
    s17["ESOI applied to AI behaviour<br/><i>esoi-for-ai</i>"]
    s18["The ESOI steps<br/><i>the-steps</i>"]
    s19["Documentation and templates<br/><i>docs-and-templates</i>"]
    s20["ESOI behaviour judge<br/><i>esoi-behaviour-judge</i>"]
    s21["Specify from the code<br/><i>specify-from-code</i>"]
    s22["Readable records<br/><i>readable-records</i>"]
    s23["Promote the winner<br/><i>promote-the-winner</i>"]
    s24["Specification index<br/><i>spec-index</i>"]
    s25["Keep a metric record<br/><i>keep-metric-record</i>"]
    s26["Spec search<br/><i>spec-search</i>"]
    s27["Grade public evidence<br/><i>public-evidence</i>"]
    s28["Know what a result measures<br/><i>know-what-a-result-measures</i>"]
    s0 -->|"The project containing the path with its first file to read and its specifications, the ids related in a given way, or the listed ids"| s1
    s2 -->|"A linked intent network that the check, the tracker and the selection read"| s3
    s2 -->|"A linked intent network that the check, the tracker and the selection read"| s11
    s2 -->|"A linked intent network that the check, the tracker and the selection read"| s21
    s3 -->|"A committed field list per type"| s9
    s3 -->|"A committed field list per type"| s11
    s4 -->|"File-to-solution links and the generated component index"| s10
    s5 -->|"The chosen implementation's class and its configuration type"| s1
    s6 -->|"A results row per run"| s23
    s7 -->|"A verdict per solution and a ranked board"| s6
    s7 -->|"A verdict per solution and a ranked board"| s9
    s7 -->|"A verdict per solution and a ranked board"| s11
    s7 -->|"A verdict per solution and a ranked board"| s23
    s7 -->|"A verdict per solution and a ranked board"| s27
    s8 -->|"A pass or fail per baseline"| s6
    s9 -->|"A list of violations, each led by its rule id, and an exit code"| s1
    s10 -->|"One problem line per violation, led by the rule id"| s9
    s11 -->|"Generated tracker tables and the synced sheet"| s9
    s11 -->|"Generated tracker tables and the synced sheet"| s23
    s12 -->|"Violations and notes"| s1
    s13 -->|"The standard document"| s1
    s14 -->|"A periodic report of cost against catches"| s10
    s15 -->|"A row per run in the results log with the commit and the hash of the cases; the strict check's verdict"| s6
    s16 -->|"A public skill folder, a plugin manifest and marketplace file, and an installed copy"| s13
    s17 -->|"The agent's reply and, for a judged run, a verdict with a reason"| s1
    s18 -->|"Linked records, a checked metric, measured implementations and a recorded selection; a short summary of how the steps were applied"| s1
    s18 -->|"Linked records, a checked metric, measured implementations and a recorded selection; a short summary of how the steps were applied"| s13
    s19 -->|"Explanations, guides and generated templates"| s1
    s19 -->|"Explanations, guides and generated templates"| s13
    s20 -->|"A verdict (pass or fail) and a one-line reason"| s17
    s21 -->|"Findings (rule S30), the rows written, and for a new solution the records, a code skeleton and an evaluation folder"| s23
    s22 -->|"A README.md in the intent's folder"| s9
    s23 -->|"Edits to selected, selected_by and the metric's command, or a printed proposal"| s1
    s24 -->|"An index (JSON-serializable: entries with id, kind, title, summary, links, weighted terms, digest, plus document frequencies), a ranked list of record ids, or a record shown at a tier"| s25
    s24 -->|"An index (JSON-serializable: entries with id, kind, title, summary, links, weighted terms, digest, plus document frequencies), a ranked list of record ids, or a record shown at a tier"| s26
    s25 -->|"From begin, the NEXT PRIORITY block for the brief; from finish, the reconciled MetricResult rows (solution_id, metric_id, name, milestone, before, after, delta, source, reason, disagrees) and whether the work did anything for them to describe"| s1
    s26 -->|"A Selection: ranked items best first with their linked items, the candidates, which search proposed each, the number of judge calls, the route and the no-solution cue"| s1
    s27 -->|"Dict(Tuple(str, str), Estimate)"| s6
    s28 -->|"Stale or current for the row, the reason naming the changed file and its owner, and the files that were ignored with their owners"| s6
```
