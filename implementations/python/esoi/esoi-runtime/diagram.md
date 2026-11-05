These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.

# Solution diagram: ESOI inside other people's running code

Inside a running program, Implementation selection hands each call to Select an implementation while the program runs, which picks the declared implementation of a solution by name, override, environment or default and refuses an unknown name with the valid choices, and to Assemble parts by name, which builds whole assemblies of named implementations and their needs. Assemble parts by name makes each of its choices through Select an implementation while the program runs, with a parent's defaults beneath a child's own.

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["Select an implementation while the program runs<br/><i>runtime-selection</i>"]
    s1["Assemble parts by name<br/><i>assemble-by-name</i>"]
    s0 -->|"The chosen implementation, and for a table its config class"| s1
```
