# Evolvable structure: patterns of the core

Part of `../principles.md`. Patterns 1, 2, 4, 6 and 7: one core, names, settings in one place, generic capability, readable definitions. Each ideal states its aim, then its evidence. Source pointers read `file > heading`, with files in `../sources/`. Quotes are verbatim, and Joshua's typed inputs keep their typos.

## Patterns

1. **One core, varied at the edge.** One mechanism does the work. What changes between cases is
   data: a config, a definition, a context, a plan. When a real new case needs the core edited, move
   what varied out to the edge in that same change, instead of adding a branch for the case.
   In his words: "use same code for all" (2026-05-21), and "The questions will be repeated over and
   over but the answers will change a lot" (2026-07-16). A reusable part is one contract: given an
   input of a known kind, it performs any operation on it. A shared library holds no consumer-specific
   logic, and a deployment is described by one config file, not a program. Where AI wrote code without such a design, per-feature classes and endpoints accumulate
   instead.

2. **Swappable parts are referred to by name.** Callers pass a name (a definition, a version, a
   domain, a mode) rather than a path or a copy. Swapping the implementation is then a one-value change and no
   caller moves. Identity is separate from version: a version number marks updates, and equality
   compares kind and variant only, so an updated part still matches. One scorer can keep its name and
   description while the model behind it changes. Code asks for a model tier by name and each
   deployment maps the tier to a model. His own code
   finds parts by name and keeps each definition in a file named for it, a convention nearly absent in
   the AI-written codebases.

4. **Each setting lives in one place.** Every setting that varies between runs, users or environments is
   set in one spot, and the rest of the code reads it. Environments differ by a few substitutions, not
   by forks. Parameters cascade: set a value once on the outer part and the inner parts inherit it
   unless set differently ("Update or pass a parameter in only one location"). Every tuned constant
   becomes a keyword parameter with a default. A data model grows one optional field at a time, each
   defaulting to empty so an existing record is unaffected.

6. **Generic capability, with the specific connected from outside.** When a need is one party's,
   the general feature every party could use is built, and the specific party attaches through a
   public interface (an API, a webhook, a definition file), so the core stays free of one party's logic.
   A capability needed by a second case moves into the shared core and the callers become thin
   wrappers. A library has one front door to an outside service, with no per-deployment client module
   and no import-path workarounds.

7. **Behaviour comes from definitions a person can read.** What varies lives in a definition a person
   can read and edit (YAML, a prompt, a card, a config table), and the code stays general. When
   behaviour is wrong, the definition it reads improves, rather than a keyword list or special case:
   a keyword net is retired, not extended. Variants such as roles or personas are a config table,
   activated by judgment, never by a bare name mention. He rejected a hardcoded emoji list twice (2025-10-04 and 2025-10-05).

## Examples from his frameworks (evidence, not principles)

A principle above must not depend on any of these, and each stays true if the framework is retired.

**Pattern 1**
- Writealyze: a box is one class contract: "Given an input object of the same class, perform any
  desired operation on that input object."
- QAR: the library is "Generic, no consumer-specific logic.", and a lane is one config file, not a
  program.

**Pattern 2**
- Writealyze (Atom notebook): "Number of electrons defines version (for updates)", and equality
  compares kind and variant only, so an updated atom still matches.
- Writealyze (NLP notebook): keeps one scorer name and docstring while the model changes.
- QAR: code asks for a model tier by name ("fast", "balanced", "best") and each deployment maps it.

**Pattern 4**
- Writealyze (NLP notebook): every tuned constant became a keyword parameter with a default.
- Quest: the autopilot grew one optional field at a time, "all optional and defaulting to None so an
  existing quest is unaffected".

**Pattern 6**
- Concept AI: a capability needed by a second domain moves into the framework and the callers
  become thin wrappers.
- QAR: one front door for the Quest API, `load_client`, with "No per-deployment client module, no
  ``sys.path`` surgery".
- Writealyze: the roadmap's "Versatility" goal includes "Wrap a third-party API with atoms."

**Pattern 7**
- QAR: "Joshua's rule: retire the net, don't extend it", and personas are a config table, activated
  by judgment, never by a bare name mention.

