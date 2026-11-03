These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: Evolvable structure that optimizes intent (ESOI)

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Apply ESOI to a project<br/>apply-esoi"]
    s1["Intent registry<br/>intent-registry"]
    s2["Template sync<br/>template-sync"]
    s3["Ownership map<br/>ownership-map"]
    s4["Implementation selection<br/>implementation-selection"]
    s5["Measurement harness<br/>measurement-harness"]
    s6["Leaderboard<br/>leaderboard"]
    s7["Discriminating cases<br/>discriminating-cases"]
    s8["Rule engine<br/>structure-check"]
    s9["Review tracker<br/>review-tracker"]
    s10["Consumer check<br/>consumer-check"]
    s11["The standard<br/>the-standard"]
    s12["Structure budget<br/>structure-budget"]
    s13["When metrics are run<br/>when-metrics-are-run"]
    s14["Skill distribution<br/>skill-distribution"]
    s15["ESOI applied to AI behaviour<br/>esoi-for-ai"]
    s16["The ESOI steps<br/>the-steps"]
    s17["Documentation and templates<br/>docs-and-templates"]
    s18["Follow the steps<br/>follow-the-steps"]
    s19["Local ESOI index<br/>local-application-index"]
    s20["ESOI behaviour judge<br/>esoi-behaviour-judge"]
    s21["Judge ESOI behaviour<br/>judge-esoi-behaviour"]
    s1 -->|"A linked intent network that the check, the tracker and the..."| s0
    s2 -->|"A committed field list per type"| s0
    s3 -->|"File-to-solution links and the generated component index"| s0
    s4 -->|"The chosen implementation's class and its configuration..."| s0
    s5 -->|"A results row per run"| s0
    s6 -->|"A verdict per solution and a ranked board"| s0
    s7 -->|"A pass or fail per baseline"| s0
    s8 -->|"A list of violations, each led by its rule id, and an exit..."| s0
    s9 -->|"Generated tracker tables and the synced sheet"| s0
    s10 -->|"Violations and notes"| s0
    s11 -->|"The standard document"| s0
    s12 -->|"A periodic report of cost against catches"| s0
    s13 -->|"A row per run in the results log with the commit and the..."| s0
    s14 -->|"A public skill folder, a plugin manifest and marketplace..."| s0
    s15 -->|"The agent's reply and, for a judged run, a verdict with a..."| s0
    s16 -->|"Linked records, a checked metric, measured implementations..."| s0
    s17 -->|"Explanations, guides and generated templates"| s0
    s17 -->|"Explanations, guides and generated templates"| s11
    s18 -->|"The steps in the public skill and the guides that point to..."| s16
    s19 -->|"The project containing the path with its first file to read..."| s0
    s21 -->|"A verdict and a reason, scored against the label"| s20
```
