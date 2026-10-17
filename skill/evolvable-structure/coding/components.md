# evolvable-structure coding: a check for any component

Part of `../coding.md`. Unlike the project examples, this check applies to any codebase. It is the
code form of pattern 15 (`../principles/patterns_change.md`). Evidence pointers read `file > heading`,
with files in `../sources/`.

**17. A component iterates inside and is reused across systems.** Unlike the examples above, this
applies to any project. Treat a piece of a larger system as a component (pattern 15): defined by what it does and its measure of success, improved inside through
versions, tuning and swapped implementations, and used by any system unmodified, with only parameters
changed. A way to check each half:
- Stable interface: the same inputs and outputs, with changes announced (pattern 13). Tests pin the
  behaviour callers rely on, not only the signature, since callers depend on whatever it does
  (`components_research.md > Wright (named by Winters), "Hyrum's Law"`, `> Liskov and Wing, 1994`).
- Versions people can pin, latest by default, and published only after tests pass.
- Callable on its own: a standalone mode with no database or framework, so another system can use it.
- No consumer logic inside it: each system supplies its specifics as config, as quest-ai-runner does.
  A system that needs something different gets a parameter or a new version, never an edited copy.
- Its assumptions are written down: control flow, process model, data format. Remove any that only
  the framework satisfies (`components_research.md > Garlan, Allen, Ockerbloom, 1995`).
- As easy to write as a plain function ("Writing a molecule must be as simple or simpler than writing a
  normal function",), or
  people will not build components.
- A small default install, with optional packages per domain or user.
The cost to weigh: reuse evidence leans toward quality, is thin and mixed on effort, and pays back
only with enough reuse (`components_research.md > Mohagheghi and Conradi, 2007`; Krüger and Berger
2020 in `public_research.md`). Build the component when a second system needs it, and keep it
improvable meanwhile.
