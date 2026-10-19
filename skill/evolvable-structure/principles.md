# Evolvable structure (ESOI): patterns, difficulties and method

`SKILL.md` is Joshua's own words and the authority: its purpose, definitions and 13 principles (its ideals, in priority order) win
over anything here, and AI never edits it. This file and `principles/` are AI-maintained: the
patterns that put those ideals to work, the evidence for them, when generality is the wrong move,
and how to think, document and review. If something here contradicts `SKILL.md`, fix it here.

Source pointers read `file > heading`, with files in `sources/`. Quotes are verbatim, and
Joshua's typed inputs keep their typos. Each subfile keeps general principles first and puts
framework examples in a final section, so a principle never depends on one framework.

## Which subfile, and when

| Read | When |
|---|---|
| `principles/purpose.md` | deciding how much structure a task deserves, or how one iteration hands its lessons to the next; designing a process (reviews, votes, approval gates) as a structure |
| `principles/vocabulary.md` | writing or explaining the idea, choosing between evolvable, adaptable, adaptive, flexible, modular; defining a component |
| `principles/patterns_core.md` | evidence for patterns 1, 2, 4, 6, 7 (the core, names, settings, generic capability, definitions) |
| `principles/patterns_people.md` | evidence for patterns 3, 5, 10, 11, 12 (defaults, personal content, what people see, ownership, one method) |
| `principles/patterns_change.md` | evidence for patterns 8, 9, 13, 14, 15 (experiment to production, measurement, interfaces, rates of change, components) |
| `principles/difficulties.md` | someone proposes an abstraction, scope is unclear, or a built structure failed |
| `principles/research.md` | you need outside support or counter-evidence, or how strong the evidence is |

The table below is usually enough; open a pattern's subfile only for its evidence or examples.

## Patterns

Concrete practices that serve the ideals in `SKILL.md`. In a design or review, the "reached when"
column is the question to ask. (Notes in `sources/` written before 2026-10-14 call these "ideal N"
or "P N". "Principle N" below is the numbered list in `SKILL.md`; notes written before 2026-10-16 number
those ideals in the old order, mapped in `sources/INDEX.md`.)

| # | Pattern | Serves principle | Reached when |
|---|---|---|---|
| 1 | One core, varied at the edge | 2, 9, 12 | a new case needs no core edit |
| 2 | Swappable parts are called by name | 2, 4, 13 | swapping an implementation moves no caller |
| 3 | Defaults people can change, chosen by reversibility | 7, 12 | the person affected can override or pin it without code, and no default acts at scale on people who never chose it |
| 4 | Each setting lives in one place, inherited inward | 3, 9, 12 | a change is one edit |
| 5 | A shared container with personal content | 7, 12 | a new person needs only their own goal, metric and plan |
| 6 | Generic capability, with the specific connected from outside | 2, 8, 9 | the feature makes sense to a stranger's team |
| 7 | Behaviour comes from definitions a person can read | 2, 6, 13 | a wrong result is fixed in the definition, not by a special case |
| 8 | Experiment and production share one path; one function serves every entry point | 4, 5 | publishing a draft is a small step |
| 9 | Alternatives are comparable, and values are measured | 2, 4, 7 | you can show on real results which option wins, and by how much |
| 10 | People see only what is set | 12, 13 | the surface does not grow with the options |
| 11 | People own it by adapting it | 7, 8 | they can copy and change it and still hear when the original improves |
| 12 | One method, with categories emerging from each case | 7 | no fixed instrument is forced on a new case |
| 13 | A stable interface, with changes announced | 2, 3 | tests pin the contract and users hear about upgrades |
| 14 | Parts are separated by how fast they change | 5 | changing the fastest part touches none of the slower ones |
| 15 | Functional components: iterate inside, reuse across systems | 2, 4, 8, 9 | the measure picks between implementations with no caller changing, and a second system uses it unmodified with new parameters only |

From a principle to its patterns: 1 → `principles/purpose.md` (sizing the structure to the intent and its
timeframe); 2 → 1, 2, 6, 7, 9, 13, 15; 3 → 4, 13; 4 → 2, 8, 9, 15; 5 → 8, 14 and `principles/purpose.md`;
6 → "How to think and document" below; 7 → 3, 5, 9, 11, 12; 8 → 6, 11, 15; 9 → 1, 4, 6, 15, with
`principles/difficulties.md` (copies drift; generality the purpose does not call for) as its limit; 10 → 8, 9
and `principles/difficulties.md` (a general claim needs a real case; an extension point counts once built
and tested): verify in the real system and against the outcome metric, not only in unit tests; 11 → 4, 8 and
`principles/purpose.md` (one source of truth refined in place; lessons carried to the next round), the
same idea one project's goal folders apply with a source-of-truth file; 12 → 1, 3, 4, 5, 10; 13 → 2, 7, 10
and `INDEX.md`'s read-when routing.

## Difficulties

When generality is the wrong move, with evidence, in `principles/difficulties.md`:
- Structure is justified by a predicted change that matters to the purpose, not by speculation;
  scope wins most of Joshua's corrections, but a general goal he already named is the need.
- Being generic is no reason to keep a feature.
- A default that acts at scale needs a setting the person can change.
- A measured value must not be overridable by callers.
- The right level matters, and a general structure still gives a specific answer.
- A general claim needs a real second case, and flexibility is hard to check.
- Copies drift, and silent fallbacks hide that the structure broke.
- An extension point counts once it is built and tested.
- Some things stay outside the standard set, and people set the AI's direction.

## How to think and document

Follow Joshua's Project Documentation board (`sources/trello_project_documentation.md >
Documentation`, `> Solution Definitions`). State the **problem** (who, why it matters, why it is
hard) and the **ideals**, each with a practical metric. Keep the **definition** (what it does, its
interface, its measure of success) apart from its **implementations**, the alternatives. The best by
the measure is the default, chosen by the structure where it can be, so people need only review metrics, not
implementations (they can still add value to implementations); park the rest rather than delete them. Note the **difficulties** and what the
structure leaves out, then **keep improving**, and save each round's lessons where the next will
find them. Apply the same steps to principles and processes, not only artifacts, and look for
problems nobody has defined yet. Before building, look for an existing structure, library, method or
public source that already serves the definition. When AI writes code, start from the interface and
one example call (`coding.md`).

**A problem is not a restated solution; every type is written as itself.** Lesson from an AI-runner project, 2026-10-17.
Joshua: "Not a single problem is written as a problem", and "keep in mind my feedback is about all five
types of things". The registry had generated one "problem" per solution, worded as the job ("Decide per
message whether to answer..."), and similar restatements stood in for ideals and metrics. Each of Problem,
Solution, Implementation, Ideal and Metric is a first-class record that specifies every field of its
`Specify:` list in `SKILL.md`'s "The five specification templates within an intent", is not what that template's "What it's not" says,
and links as its "Connects to" says (so one problem can motivate several solutions and be opposed by several
ideals). Never derive one type from another's row, and do not write a standard of your own: read the template
from `SKILL.md` each time, since Joshua refines it, and fill any field it newly lists.

**Keep Joshua's qualifiers when restating SKILL.md.** Lesson from the evolvable-structure repo, 2026-10-17.
Principle 4 says "Humans need only review metrics, not implementations (but they can still add value to
implementations)". AI docs shortened it to "Humans review metrics, not implementations" and "never by reading
implementations". Joshua: "you lost the nuance here ... a very important nuance as people will be critical to
explicitly deny the possibility of humans reviewing implementations." A paraphrase that drops "need only", "if and
only if", "relatively", "pragmatically" or a parenthetical turns a sufficiency into a prohibition or a rule into an
absolute. Quote SKILL.md, or keep every qualifier, and check a restatement against the original sentence.

**Define the top intent first; per-repo tooling comes from the shared utilities.** Lesson from a research-engine
project, 2026-10-17. Asked to apply ESOI to it, AI started copying a sibling project's registry and checker into the
repository. Joshua: "Apply esoi to the overall structure which the practical structures in repo will implement, but keep
in mind the new evolvable-structure repository will provide guidance or utilities for doing that in general, but you
should define the overall solution of conceptai and have me review right away." So the first deliverable is the
top-level network (the product's own problems, ideals, solutions, implementations, metrics), validated with the ESOI
tools and sent for review before any per-module registry. A review pass then found the same draft had drifted into
framework plumbing (runtime, providers, stores promoted to top-level ideals) and missed evaluation and evidence
ingestion: at the top level, ideals come from the owner's stated requirements, the core capabilities are the ones users
and the evaluation depend on, and how the code is built is one level down. Comparison arms (baselines) go in a metric's
record, not in implementations; status, gaps and numbers go in the project's tracker or dated result files, not in the
records. The project's own notes are in the local ESOI index.

**Hierarchy is intents, not solutions (Joshua, 2026-10-18).** Joshua: "In ESOI have hierarchy be defined in terms of intents and sub-intents instead of solutions and sub-solutions." An intent is a clear, encapsulating container (in a repository, a folder with its own record). A sub-intent arises as an implementation of a solution in the parent intent, and is specified "if and only if that intent brings insights on opportunities that don't emerge directly from the parent intent or solution that the sub-intent is implementing". Risks and uncertainties alone do not justify one: risks are disadvantages of the implementation, and the metric of the solution handles uncertainty. Implementations are ideas that can start as sub-intents or evolve into them. The two-level "overall network plus detailed records" layout is legacy (it maps to the top intent plus sub-intents and `uses_solution_ids`). The 2026-10-17 answers below that say "sub-solution" are from before this change.

**A project's top intent is why that project exists, never "the structure" (Joshua, 2026-10-18).** Joshua: "The top intent is very importantly custom to the project, why the project exists." The folder that holds the specifications is not the intent. The evolvable structure a project applies is a solution inside the project's own top intent; its implementation may use the generic ESOI solutions (a "uses" link across projects), and anything project-specific about the structure lives inside that project's top intent. Only in the ESOI repository itself is the top intent ESOI, because that is why that project exists; do not generalize from it.

**Joshua's answers on the structure network, 2026-10-17.** On whether types link both ways: "Your question is
misleading, as what you list in parenthesis I *did* specify in "Connects to." I included the directions I felt important
to specify to ensure the intent is documented. In practice, this depends on what structure holds the ESOI structure, e.g.
if it's a graph data model then it only has to be specified once for both directions, as edges." So before asking
whether SKILL.md specifies something, check it, and quote it in the question. On keeping two close solutions separate
(a measurement harness and a leaderboard): important enough to separate, and it "helps for humans skimming and reading
only names, to get a clear picture." On a structure budget with no implementation: "Keep; it's essentially always needed
conceptually to avoid infinite hierarchy, but not every project merits a code solution for this." On ESOI applied to AI
behaviour: "The general application of ESOI to AI is a sub-solution of ESOI", so it belongs in the evolvable-structure
repository, though not in its structure network file.

## Upkeep of this skill

- **Project routing belongs in the local ESOI index, not in this skill's `INDEX.md`** (Joshua, 2026-10-18). `INDEX.md` routes by kind of task to instructions and examples, with no assumption about which projects the reader works on. Which projects ESOI is applied to, how they relate and where to look in each live in `$ESOI_HOME` or `~/.esoi/` (`projects.csv` and `INDEX.md`; see the ESOI repository's "The local ESOI index"). Example files from the author's own work stay, named as examples of a technique.
- Never edit `SKILL.md`. A new statement from Joshua goes, dated and in his words, into the matching
  `principles/` subfile, then into the tables above and the matching `INDEX.md` row in the same edit.
- Name a framework only in an example, a `coding/` file or a source pointer, unless the principle is
  for that framework.
- `sources/` notes are research records: add to them, but do not renumber or rewrite old ones.
