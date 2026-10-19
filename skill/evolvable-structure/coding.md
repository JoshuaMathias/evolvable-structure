# evolvable-structure: coding

The ideals in `SKILL.md` apply to every codebase. The project examples do not: each shows how one of
Joshua's projects met an ideal with that project's own mechanism. Carry over the purpose, and copy a
mechanism only when the codebase already uses it or truly has the same problem. The codebase's own
conventions and playbook come first (the local ESOI index, if any, says where they are). Load only the subfile the current task needs.

## Where to look

| File | Technique it teaches (examples) | Load when |
|---|---|---|
| `coding/components.md` | making a part other systems reuse, with versions and no consumer logic inside (17) | building a part meant for other systems, versioning or publishing it |
| `coding/registry_and_templates.md` | finding code by name, scaffolding from templates, dependency-pruned packaging, documenting parameters (1, 2, 8, 12) | finding code by name, scaffolding, packaging, documenting parameters |
| `coding/pipelines_and_experiments.md` | declaring pipeline stages once, data model and storage routing, environments, experiments compared by a metric, one function for every entry point (3 to 7) | pipeline stages, data model and storage routing, environments, experiments, one function for many entry points |
| `coding/writealyze.md` | versions and swappable implementations, class contracts, tuning several implementations against one metric (9, 13, 14, 15) | versions and swappable implementations, class contracts, tuning against one metric |
| `coding/concept_ai_quest_qar.md` | one engine with domains as data and measured weights (10), keeping a product core generic while specific tools connect from outside (11), a deployment as one config file behind one front door (16) | a second case that differs only in data, a core one party's logic is creeping into, or many deployments of one program |

Each project file ends with what went wrong in that project, so it is not copied.

## When AI writes the code

Joshua's own code and AI-written code differ mostly in how code is grouped and found, not in function
length: his is many small files, one or two functions each, named for what they are and found by
name; AI code tends toward large modules that grow a method or route per feature. These are tendencies to move toward, not a style to copy:
- Start from how the part is called: write the interface and one example call first, and keep one
  call shape across siblings, as one project's draft did for `domain(...)`, `decision(...)` and
  `action(...)`.
- Prefer small parts named for what they are and found by that name over a new section in a big
  module. A file that keeps growing is a signal to split by definition.
- When a second case arrives, look for the parameter, definition file or shared function before adding
  a class or a route.
- Let one function serve every entry point (pattern 8; example 7).
- Keep the tests, error handling and docs AI code already does well; the aim is his structure with
  that rigor.
- Size and counts are signals, not targets: no splitting to hit a number, and no copying his old code
  literally. Studies disagree on size and defects; the support is for named, stable interfaces that
  hide change (`public_research.md > Koru`, `> Hatton`, `> Fenton and Ohlsson`, `> Parnas`).

## Checks for any codebase

These hold in any project; the example numbers only show one place each was done.

1. Two functions that differ only in constants, names or one dependency are usually one function with
   parameters (examples 6, 15).
2. Settings that vary by run, user or environment sit in one place with a default (patterns 3 and 4).
3. Import paths, if-chains over names and phrase lists give way to a lookup by name (example 1) or a
   definition file (examples 10, 16).
4. Each function stands alone: arguments in, result out, storage optional (examples 3, 7, 13).
5. The next run is comparable to this one: saved parameters, a fixed dataset, a baseline (example 6).
6. The structure stops where the evidence stops: no parameter or registry for a case nobody has named,
   no override on a measured value, no README promise before it is built and tested.
7. The codebase's own rules come first: its naming rules, where prompts live, and the standards and
   playbook it documents.
8. Applying ESOI to an existing codebase removes what serves no solution (principle 11). Code AI wrote
   piles up unused modules, routes, scripts and summary docs, so mapping every file to a solution is
   also the dead-code sweep: a file nothing reachable uses, and that no named problem needs, is
   deleted (git keeps it), not given a solution row. Check reachability first (imports from used
   code, router registration, scripts and services that run, frontend calls); a route no frontend
   calls may still be public API, so confirm before removing it. (Joshua, 2026-10-17.)
