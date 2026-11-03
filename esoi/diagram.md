These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Evolvable structure that optimizes intent (ESOI)

esoi turns an intention into a structure that keeps fulfilling it while both change, and apply-esoi is how a project takes that up: apply-esoi teaches people through the-standard, guides AI agents through esoi-for-ai, holds the records and the code to their rules through structure-check, measures alternatives and moves the selection to the winner through promote-the-winner, chooses the implementation that serves each call through implementation-selection, finds the records a request concerns through spec-search, records one piece of work's metric before and after through keep-metric-record, finds which projects apply ESOI through local-application-index, and checks a project built on a library through consumer-check. the-standard explains ESOI and its fill-in templates in docs-and-templates, gives the order of the work in the-steps and ships the author's skill as a public folder through skill-distribution; the-steps is written down for readers in follow-the-steps. esoi-for-ai gives an agent the skill as standing instructions, behave-by-esoi measures case by case whether its replies act by the principles, and esoi-behaviour-judge grades the replies a pattern cannot settle, through judge-esoi-behaviour. structure-check applies every rule it holds through structure-rules, each rule kept only while structure-budget says it still pays and with ownership-map tying every file to a component, keeps the record fields in step with the template through template-sync, regenerates the pages of readable-records and the review-tracker sheet, and reads standings from leaderboard; template-sync parses the template that the intent-registry records follow. review-tracker puts the intent-registry records, the leaderboard standings and the fields kept in step by template-sync in front of a reviewer. promote-the-winner switches a solution's selected implementation when leaderboard shows a clear winner among the rows measurement-harness recorded, then updates the review-tracker sheet and the declarations that specify-from-code keeps in step with the intent-registry records; measurement-harness runs each implementation on its solution's cases, proves through discriminating-cases that those cases fail a naive implementation, follows when-metrics-are-run for when a stage may run and what it may spend, consults public-evidence before it pays to measure a candidate others have measured, and hands its rows to leaderboard, which public-evidence reads as well. implementation-selection chooses which implementation serves a solution by name, configuration or table default, and its declarations grow into the esoi-runtime sub-intent. spec-search ranks the records a request concerns over the narrowed set spec-index gives it. keep-metric-record reads the slice spec-index gives for the work it records. local-application-index says where to look first in each project. consumer-check scores a consumer's own implementations with the library's cases and shows its version lag.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Follow the steps<br/>follow-the-steps"]
    s1["Local ESOI index<br/>local-application-index"]
    s2["Behave by ESOI<br/>behave-by-esoi"]
    s3["Judge ESOI behaviour<br/>judge-esoi-behaviour"]
    s4["Apply ESOI to a project<br/>apply-esoi"]
    s5["Intent registry<br/>intent-registry"]
    s6["Template sync<br/>template-sync"]
    s7["Ownership map<br/>ownership-map"]
    s8["Implementation selection<br/>implementation-selection"]
    s9["Measurement harness<br/>measurement-harness"]
    s10["Leaderboard<br/>leaderboard"]
    s11["Discriminating cases<br/>discriminating-cases"]
    s12["Rule engine<br/>structure-check"]
    s13["Structure rules<br/>structure-rules"]
    s14["Review tracker<br/>review-tracker"]
    s15["Consumer check<br/>consumer-check"]
    s16["The standard<br/>the-standard"]
    s17["Structure budget<br/>structure-budget"]
    s18["When metrics are run<br/>when-metrics-are-run"]
    s19["Skill distribution<br/>skill-distribution"]
    s20["ESOI applied to AI behaviour<br/>esoi-for-ai"]
    s21["The ESOI steps<br/>the-steps"]
    s22["Documentation and templates<br/>docs-and-templates"]
    s23["ESOI behaviour judge<br/>esoi-behaviour-judge"]
    s24["Specify from the code<br/>specify-from-code"]
    s25["Readable records<br/>readable-records"]
    s26["Promote the winner<br/>promote-the-winner"]
    s27["Specification index<br/>spec-index"]
    s28["keep-metric-record<br/>keep-metric-record"]
    s29["Spec search<br/>spec-search"]
    s30["Grade evidence<br/>public-evidence"]
    s0 -->|"The steps in the public skill and the guides that point to..."| s21
    s1 -->|"The project containing the path with its first file to read..."| s4
    s2 -->|"A reply per case, a pass or fail with a note, and a..."| s20
    s3 -->|"A verdict and a reason, scored against the label"| s23
    s5 -->|"A linked intent network that the check, the tracker and the..."| s6
    s5 -->|"A linked intent network that the check, the tracker and the..."| s14
    s5 -->|"A linked intent network that the check, the tracker and the..."| s24
    s6 -->|"A committed field list per type"| s12
    s6 -->|"A committed field list per type"| s14
    s7 -->|"File-to-solution links and the generated component index"| s13
    s8 -->|"The chosen implementation's class and its configuration..."| s4
    s9 -->|"A results row per run"| s26
    s10 -->|"A verdict per solution and a ranked board"| s9
    s10 -->|"A verdict per solution and a ranked board"| s12
    s10 -->|"A verdict per solution and a ranked board"| s14
    s10 -->|"A verdict per solution and a ranked board"| s26
    s10 -->|"A verdict per solution and a ranked board"| s30
    s11 -->|"A pass or fail per baseline"| s9
    s12 -->|"A list of violations, each led by its rule id, and an exit..."| s4
    s13 -->|"One problem line per violation, led by the rule id"| s12
    s14 -->|"Generated tracker tables and the synced sheet"| s12
    s14 -->|"Generated tracker tables and the synced sheet"| s26
    s15 -->|"Violations and notes"| s4
    s16 -->|"The standard document"| s4
    s17 -->|"A periodic report of cost against catches"| s13
    s18 -->|"A row per run in the results log with the commit and the..."| s9
    s19 -->|"A public skill folder, a plugin manifest and marketplace..."| s16
    s20 -->|"The agent's reply and, for a judged run, a verdict with a..."| s4
    s21 -->|"Linked records, a checked metric, measured implementations..."| s4
    s21 -->|"Linked records, a checked metric, measured implementations..."| s16
    s22 -->|"Explanations, guides and generated templates"| s4
    s22 -->|"Explanations, guides and generated templates"| s16
    s23 -->|"A verdict (pass or fail) and a one-line reason"| s20
    s24 -->|"Findings (rule S30), the rows written, and for a new..."| s26
    s25 -->|"A README.md in the intent's folder"| s12
    s26 -->|"Edits to selected, selected_by and the metric's command, or..."| s4
    s27 -->|"An index (JSON-serializable: entries with id, kind, title..."| s28
    s27 -->|"An index (JSON-serializable: entries with id, kind, title..."| s29
    s28 --> s4
    s29 -->|"A Selection: ranked items best first with their linked..."| s4
    s30 -->|"Dict(Tuple(str, str), Estimate)"| s9
```
