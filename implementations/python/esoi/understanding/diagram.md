These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: How People and Agents Come to Apply ESOI

Understanding is how ESOI reaches the people and agents who apply it. The Standard teaches anyone how a solution is shaped and how a project adopts it, with templates to fill in by hand, and for the order of the work it relies on The ESOI Steps. The Standard also ships the author's skill through Skill Distribution, which publishes a complete public copy that cannot leak or go stale. ESOI Applied to AI Behaviour gives an agent the principles as standing instructions and measures, case by case, whether its replies act on them, asking the ESOI Behaviour Judge to grade what a pattern cannot settle. When a reader needs one part of a project, three parts help. Readable Records gives every intent folder a page made from its records. Spec Search finds the records and standards a request concerns. The Local ESOI Index says which projects apply ESOI and where to look first in each. When a matter concerns several solutions, Solution Consideration forms one prompt per solution and per parent level from the records each connects to, so every solution gets its own consideration. Solution Consideration asks Solution Relevance which solutions a matter concerns, and Solution Relevance ranks them with the records Spec Search finds. The Review Tracker puts the whole intent network and its latest results in front of a reviewer and carries the reviewer's edits back to the records, so people steer by metrics without reading the code.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["ESOI Applied to AI Behaviour<br/><i>esoi-for-ai</i>"]
    s1["Solution Consideration<br/><i>solution-consideration</i>"]
    s2["Solution Relevance<br/><i>solution-relevance</i>"]
    s3["Spec Search<br/><i>spec-search</i>"]
    s4["The Standard<br/><i>the-standard</i>"]
    s5["ESOI Behaviour Judge<br/><i>esoi-behaviour-judge</i>"]
    s6["Skill Distribution<br/><i>skill-distribution</i>"]
    s7["The ESOI Steps<br/><i>the-steps</i>"]
    s2 -->|"Solutions best first, each with a score and the records that reached it; the caller adds the parents"| s1
    s3 -->|"A Selection: ranked items best first with their linked items, the candidates, which search proposed each, the number of judge calls, the route and the no-solution cue"| s2
    s5 -->|"A verdict (pass or fail) and a one-line reason"| s0
    s6 -->|"A public skill folder, a plugin manifest and marketplace file, and an installed copy"| s4
    s7 -->|"Linked records, a checked metric, measured implementations and a recorded selection; a short summary of how the steps were applied"| s4
```
