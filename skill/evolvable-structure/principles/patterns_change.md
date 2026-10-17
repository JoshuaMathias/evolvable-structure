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
   before it counts.

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
  better than another in achieving the Definition's goals."
- quest-ai-runner: one library with no consumer logic, and each consumer supplies its specifics
  through config.
- Writealyze: McIlroy's 1968 family of components is an early form of atoms and molecules. Both have
  one named family whose members differ by parameters, and a cheap swap to another member.
  Source: `components_research.md > McIlroy, 1968`.


