# Evolvable structure: patterns for change and components

Part of `../principles.md`. Patterns 8, 9, 13, 14 and 15: one path from experiment to production, comparable alternatives, stable interfaces, layers by rate of change, functional components. Each ideal states its aim, then its evidence. Source pointers read `file > heading`, with files in `../sources/`. Quotes are verbatim, and Joshua's typed inputs keep their typos.

## Patterns

8. **Experiment and production share one path, and one function serves every entry point.** The
   first draft is written the way the reusable version is written, so publishing is a small step. The same
   function serves the notebook, the command line, the pipeline and the test. The standard: writing a
   reusable part must be as simple as, or simpler than, writing a normal function. A design starts
   from the interface: one consistent input and output format across all operations, with one example
   call per class.

9. **Alternatives are comparable.** The work is structured so options can run side by side: a frozen
   dataset, parameters saved with every result, the metric as a fixed or swappable part, a baseline to
   beat. Weights and defaults come from measurement, not guesses, and a part that has not been
   measured contributes nothing until it is. Default constants are measured from a corpus, and any
   set of parameters is tuned against one fixed metric. Re-measurement is enforced by a check, not
   left as advice. A general claim has to beat the real baseline
   before it counts. **The highest-scoring implementation is used by default**, labelled with whether
   its lead is statistically significant (a paired test on shared cases) or a best guess, so better
   solutions are adopted right away, especially for a new solution without end users or before the
   higher cascade stages run; the highest stage should be sized so a real difference can reach
   significance. Requiring significance before switching is opt-in per solution or project (for
   solutions with production end users), and consumers can lock selections and update on their own
   schedule (Joshua, 2026-10-31: "where there isn't statistical significance, the highest scoring
   implementation should still be used by default"). **Which alternatives to build
   and compare** is guided first by public research and public evaluations on similar tasks (Joshua,
   2026-10-31: "leverage public research and evals for what methods or combination of methods are most
   likely effective on similar tasks to guide what implementations are compared or considered or
   improved"), graded by who ran them, and never mixed into our own numbers. **Run our own evaluation
   only where it differs from what is public**: when an independent public evaluation already measured
   the same implementation on the same metric, use it as the stage instead of re-running it; run ours
   only when our implementation, method (prompt, harness, settings) or metric differs. And **stop a
   cascade at the ceiling**: once a cheaper arm passes every case, a costlier arm cannot win on that
   metric and is not run (Joshua, 2026-10-31: "if haiku has perfect score then higher tier models aren't
   necessary to consider ... you only need to do eval if the implementation/method or metric is
   different than what's known publicly"). Never invent a fixed margin
   or tie-break threshold: Joshua, 2026-10-31, on finding the library used one: "i never authorized
   that ... it should be pragmatic for individual cases, metrics can be best guesses but
   statistically significant improvement where possible to justify switching".
   **A cascade runs ONE criterion at rising cost; it never changes the criterion.** Every stage's
   metric is a single number that says which alternative is best across all factors (accuracy, cost,
   time, size), with the weights fixed and written down before any alternative is scored. Later
   stages estimate the same number more faithfully (more cases, real inputs, a live model), and a
   cheap stage may exclude an alternative only on that number, never on a different criterion.
   Different kinds of cases (a single file, a whole topic, real inputs) are case sources of the one
   metric, mixed in proportion to how real inputs occur, not stages with their own pass tests and
   not separate leaderboards. A "must not regress" guard from one stage into the next is a second
   criterion in disguise. Joshua, 2026-11-04, after an AI laid file finding, topic needs and real
   inputs out as sequential stages and reported three leaderboards: "that's not how cascade is used,
   that could cause huge problems, every stage metric must be a single number which represents
   what alternative is best across all factors".
   **Aim the metric at what the solution is for, not at what is easy to score.** Context cards
   group information on one topic from many files and sources; a card per file is a file index, a
   different thing. Scoring cards only on single-file lookup picked the file index and would have
   put a card per file in the Quest database (Joshua, 2026-11-04). Before trusting a leaderboard,
   ask whether the cases look like the real inputs (use real inputs to calibrate the case mix),
   whether the unit being scored is the thing the solution produces. No arm is excluded by a mark
   (Joshua, 2026-11-04: "a metric should determine whether something is used, not marking as
   baseline"): every implementation competes on the one balanced metric, and if a trivial arm (one
   card per file) wins, the metric lacks a factor (cost, size, efficiency, accessibility), so put it
   into the number.

13. **A stable interface, with changes announced.** What lets an implementation be swapped is a
    contract that does not move: the same inputs, outputs and style rules. Tests pin it, the author
    who would change it is warned, and the people who use it hear about upgrades. When a producer and
    a consumer disagree on keys, the feature silently does nothing. A copied default text drifted from
    its original within hours, so a contract test now asserts the copies are equal.

14. **Parts are separated by how fast they change.** Stable parts sit underneath, and fast-changing
    parts sit at the edge, so fast parts never wait on slow ones. The evidence is practitioner and
    theory, not experiment: shearing layers in buildings (Duffy, Brand), near-decomposable systems
    (Simon 1962), and modifiability tactics (Bass et al.). Qiu et al. 2013 and Fenton and Ohlsson 2000
    support that change is concentrated in few parts. In his own work the version of a part is kept
    apart from its identity, and the differences between deployments are kept in config.
    Sources: `definitions_and_advice.md > Brand 1994 and the Long Now talk: separate by rate of
    change`; `public_research.md > Simon, 1962`.

15. **Build functional components: iterate inside, reuse across systems.** The working unit is a
    piece of a larger system with a stable interface, built to be improved inside (new versions,
    tuning, swapped implementations) and used in other systems with only parameters changed. Both
    halves are required: reuse with no way to improve is brittle, and iteration that breaks callers is
    not reusable.
    - *Defined by what it does.* Each component is defined by what it does and its measure of
      success, not only by its inputs and outputs (Joshua, 2026-10-14: "defining for each component
      what it does, not just output and input, and what its metric(s) of success is"). Its
      implementations are alternatives judged by that measure, and a measure can itself be a
      component, so the best measure for a task is chosen the same way.
    - *Composed without modification.* A second system uses the component as it is and changes only
      parameters or configuration; a copy edited per system is a fork, not the same component
      (Heineman and Councill's definition, wording known secondhand). Variation is designed as a
      family: named dimensions with parameters bound early, so a user can try another member of the
      family cheaply (McIlroy 1968).
    - *Compatible while it improves.* Callers come to depend on whatever a component actually does
      (Hyrum's law), and version numbers alone do not stop breaking changes (Raemaekers et al.). So
      tests pin behaviour, not only signatures (Liskov and Wing), and callers can pin a version and
      upgrade on purpose (Dietrich et al.).
    - *Says what it assumes.* A part carries assumptions about its surroundings (control flow,
      process model, data format), and parameters cannot fix a clash in structure (Garlan et al.).
      List those assumptions and remove any that only one framework satisfies.
    - *Honest about payoff.* Reuse evidence leans toward quality gains, because a fix in the shared
      part reaches every user, but it is thin and mixed on effort, and the shared part costs someone
      to build and own (Mohagheghi and Conradi; Lim; Krüger and Berger). Do not promise savings, and
      do not componentize a one-off.
    In his work, a definition is found by name, so a function can become an interface without
    changing callers. Versioned parts are composed, latest by default and pinnable. Writing a reusable
    part is as simple as writing a normal function. A pipeline stage runs standalone with no database.
    A shared library holds no consumer logic. A component passes tests before it is published, and the
    default install stays small.
    Sources: `components_research.md > Heineman and Councill (eds.), 2001`, `> McIlroy, 1968`,
    `> Wright (named by Winters), "Hyrum's Law"`, `> Raemaekers, van Deursen, Visser, 2017`,
    `> Liskov and Wing, 1994`, `> Dietrich, Pearce, Stringer, Tahir, Blincoe, 2019`,
    `> Garlan, Allen, Ockerbloom, 1995`, `> Mohagheghi and Conradi, 2007`, `> Lim, 1994`,
    `> Krüger and Berger, 2020 (referenced only)`.

## Examples from his frameworks (evidence, not principles)

A principle above must not depend on any of these, and each stays true if the framework is retired.

**Pattern 8**
- Writealyze (Atom notebook): the standard: "Writing a molecule must be as simple or simpler than
  writing a normal function."
- conceptai: his draft starts from the interface: "Consistent Execution: A consistent input and
  output format is maintained across all class operations", with one example call per class.

**Pattern 9**
- Concept AI: "Those constants encoded guessed importances; here importance is measured.", and
  "Under the Beta(1,1) prior an unmeasured source sits at 0.5 and contributes nothing".
- Concept AI: re-measurement is enforced, which "makes this rule enforceable rather than advisory".
- Writealyze (NLP notebook): measures its default constants from a corpus and tunes any parameter
  dict against one fixed pairwise metric.

**Pattern 13**
- Concept AI: when a producer and a consumer disagree on keys, "Context weighting silently no-ops."
- Quest autopilot and QAR: a copied default text "drifted by paraphrase within hours of being
  written", so a contract test now asserts the copies are equal.

**Pattern 14**
- Writealyze: the version is kept apart from the identity of an atom.
- QAR: keeps lane differences in config.

**Pattern 15**
- A name-keyed registry library of his: a definition is a folder found by name, so a function can become an interface
  without changing callers.
- Writealyze: atoms are versioned and composed, with latest by default and pinning, and a molecule is
  the best atom for a task so callers do not change when the winner changes; "Writing a molecule must
  be as simple or simpler than writing a normal function".
- Writealyze: "Molecules have specific requirements, including a well-defined metric. Metrics
  themselves may be molecules, to determine the best metric for a particular task."
- Project Documentation board: "Measures of Success: ... a way to know whether one implementation is
  better than another in achieving the Definition's goals." Source: `trello_project_documentation.md
  > Definition Template`.
- quest-ai-runner: one library with no consumer logic, and each consumer supplies its specifics
  through config.
- Writealyze: McIlroy's 1968 family of components is an early form of atoms and molecules. Both have
  one named family whose members differ by parameters, and a cheap swap to another member.
  Source: `components_research.md > McIlroy, 1968`.

**Pattern 8 and 9 (collaborative innovation)**
- Cantr governance: an idea is approved before details ("This vote is for a general idea, before too
  much effort is spent working out the details."), a changed proposal gets a new vote without waiting,
  and a rejection must yield "a related alternative suggestion" within a month. Marketing sets
  "measurable goals regarding new players and retaining players." Sources: `cantr_governance_proposals.md > Revising a proposal
  without restarting the process`, `> Silence and rejection have defined outcomes`, `> Measuring what
  works`.


**Pattern 13 (collaborative innovation)**
- Cantr governance: the Player Board is notified of staff proposals, and staff "will be notified if
  the owner overruled the decision". Sources: `cantr_governance_proposals.md > A standard workflow, written down`,
  `> Accountability for the owner's override`.


**Staleness of a measured result (Joshua, 2026-11-04)**
- A metric result goes stale only when the implementation's own code changes, never for a test or fixture, the scorer, or code that another implementation owns even if imported; another solution's code is answered by that solution's own recorded selection.

**Names and ids (Joshua, 2026-11-04)**
- A record's `name` is the human-readable label that leads every output (tables, headings, diagrams, the coherence paragraph); its `id` is the stable handle that commands and links use. Write the paragraph in names; ids are optional.

**Flow first (Joshua, 2026-11-04)**
- Start from the flow, and not only in code (specs, processes, documents, offerings, how an AI behaves; code is one case). Unless told otherwise, first write the FLOW the intent's coherence paragraph describes, in the medium the implementation will be (entry-point calls in code, handoffs and steps in a process, sections that refer to each other in a document, roles and delegations in an organisation), with each solution's interface (what it takes and returns, who is responsible) defined even where nothing implements it yet; then implement what the flow reaches, one level down at a time, at every point of the hierarchy in scope (an implementation may be code, a document, a registry, a process or a person). Revise interfaces and flow from what implementing teaches. Joshua: "always start implementation from top to bottom and code for the conceptual flow which the intent solution coherence paragraph describes, using the entry points for each solution, unless told otherwise; after the flow is implemented, implement the code for what the flow calls; in other words function definitions and calls of solution functions first (interfaces), then implementations, at all points of the hierarchy for everything within scope of the current task (which can be the whole repository); interfaces and flow can be updated as needed based on learnings from implementation."

**A solution holds alternatives of one job (Joshua, 2026-11-04)**
- A solution is a container for alternatives that do the SAME job. When its implementations serve different purposes or very different specificity (an "Acting" whose arms are a one-call file edit, an MCP write and coding-agent runners), it is mis-defined: read the implementation list for purpose and specificity when defining or reviewing a solution, split by purpose (a general solution with general arms, specific solutions nested beneath or composed by it, optionally routed cheapest-first), and name which general alternatives are missing.

**Role scoping of solutions (Joshua, 2026-11-04)**
- Nuances of a solution's scope are easy to miss, so state the role: what it is responsible for (purpose), what it is not and which sibling owns that (out of scope, `delegates_to`), and for a container what kind of change moves its metric (`change_driver`). A solution justified only by a capability a sibling or the world already provides is not a solution. This is specialization and delegation of responsibility.
