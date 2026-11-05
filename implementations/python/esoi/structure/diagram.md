These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: A Project's Records and Code as One Structure

Structure keeps a project's records and code one true and lean whole. The Intent Registry holds every problem, solution, implementation, ideal and metric as linked records beside the code they describe. It takes its fields from the author's template through Template Sync and fills the rows the code already declares through Specify from the Code, leaving a person's words untouched. The Ownership Map ties every file to the solution it serves, so code that serves nothing has nowhere to hide. Structure Check runs every rule on each change, reading the files the Ownership Map assigns and the fields Template Sync reads from the template, and reports each finding by rule and path with the next action. Structure Budget weighs what the rules that Structure Check runs cost each change against the real mistakes they catch, admits a new rule only with the mistake that justifies it, and prunes what stops paying.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Intent Registry<br/><i>intent-registry</i>"]
    s1["Ownership Map<br/><i>ownership-map</i>"]
    s2["Structure Budget<br/><i>structure-budget</i>"]
    s3["Structure Check<br/><i>structure-check</i>"]
    s4["Specify from the Code<br/><i>specify-from-code</i>"]
    s5["Template Sync<br/><i>template-sync</i>"]
    s1 -->|"File-to-solution links and the generated component index"| s3
    s3 -->|"A list of violations, each led by its rule id, and an exit code"| s2
    s4 -->|"Findings (rule S30), the rows written, and for a new solution the records, a code skeleton and an evaluation folder"| s0
    s5 -->|"A committed field list per type"| s0
    s5 -->|"A committed field list per type"| s3
```
