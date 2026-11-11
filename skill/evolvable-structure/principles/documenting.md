# Evolvable structure: how to think and document

Part of `../principles.md`. The documentation method, and the dated lessons from Joshua about writing problems, ideals, vision statements, intents and restructurings. Quotes are verbatim, and Joshua's typed inputs keep their typos.

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

**A problem says what is true; an ideal says the state you want (Joshua, 2026-11-04).** On a hub problem that read
"Parts that are best alone can fail when assembled, and nobody tests the whole", Joshua: "this isn't correct, it's that
the parts need to be justified as part of the whole but just independently optimized, and it's not correct that the
whole is never tested, what developer would say that ... ensure that problems don't say false things just to make easy
statements; it should have nuanced yet clear and simple language." A problem describes today, so a domain expert must
recognise it as accurate: replace a sweeping absolute or a strawman with the real gap (what is missing, for whom, how often,
at what cost). Then: "absolutes are more expected in ideals than in problems, that's kind of what ideals are", and "ideals
should avoid being solutions, that's the easiest trap; solutions are strategic approaches or roles in a system, ideals are
the state we want." So an ideal states the limit state from the point of view of whoever is affected ("Every request
reaches a model that is up and within its budget"), never the means ("Use one router for every model call"). Test: could
two different solutions both reach it? The ESOI repository's explanation `a-problem-says-what-is-true.md` and how-to
`write-problems-and-ideals-that-hold-up.md` hold the checklist; its advisory rules S51 (absolutes in problems) and S52
(solution-shaped ideals) point at candidates.

**A vision statement is one short sentence naming the overall concept in its optimal, ongoing state (Joshua, 2026-11-04).** AI drafts were "too long and detailed, like going into the metrics or subsolutions instead of an overall concept", and "every week" is "too specific for a vision statement, that's a metric or implementation". His rewrites show the pattern: start from who the concept serves and what they get ("AI builders have consistent interfaces for whatever the current best AI solutions are, to adapt only what is unique to their project"); name the central concept itself, not its steps or parts; state the optimal ongoing state with words like "optimally", "in the best way possible", "continuously" ("The AI system optimally learns and interacts with the world outside of it", "AI requests are handled in the best way possible, given all relevant information"); write "The AI system", not "An AI system"; qualify with what the result depends on, not with an outcome clause; leave out frequencies, counts, flow steps and sub-solutions. An ideal takes the comprehensive absolute form ("The implementations selected for solutions always reflect the best alternative available across all known resources and methods"). AI may write vision wording but shows it to him first.

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

**Hierarchy is intents, not solutions (Joshua, 2026-10-18).** Joshua: "In ESOI have hierarchy be defined in terms of intents and sub-intents instead of solutions and sub-solutions." An intent is a clear, encapsulating container (in a repository, a folder with its own record). A sub-intent arises as an implementation of a solution in the parent intent, and is specified "if and only if that intent brings insights on opportunities that don't emerge directly from the parent intent or solution that the sub-intent is implementing". Risks and uncertainties alone do not justify one. SKILL.md: "Risks are addressed by considering disadvantages of Implementations and Metrics, uncertainties are addressed by Metrics, and opportunities are addressed by Solutions." Implementations are ideas that can start as sub-intents or evolve into them. The two-level "overall network plus detailed records" layout is legacy (it maps to the top intent plus sub-intents and `uses_solution_ids`). The 2026-10-17 answers below that say "sub-solution" are from before this change.

**A restructuring is an alternative structure, measured before and after (Joshua, 2026-11-05).** Each merge, split, adoption, interface change or moved module is compared like any other alternative: run `esoi structure-quality` before, `esoi structure-quality --compare <before> <after>` after, and keep the change only if the balanced number holds or rises, stating the reason in the commit when it does not. Joshua had to ask for this; the library's order of building, standard and CLAUDE.md now say it so nobody has to be told.

**A project's top intent is why that project exists, never "the structure" (Joshua, 2026-10-18).** Joshua: "The top intent is very importantly custom to the project, why the project exists." The folder that holds the specifications is not the intent. The evolvable structure a project applies is a solution inside the project's own top intent; its implementation may use the generic ESOI solutions (a "uses" link across projects), and anything project-specific about the structure lives inside that project's top intent. Only in the ESOI repository itself is the top intent ESOI, because that is why that project exists; do not generalize from it.

**Cutting cost is not the same as finding the balance (Joshua, 2026-10-19).** A review found user specs were written but never read, and recommended "Stop AI-written specs for quests" outright. Joshua: "Some of this sounds a little too extreme ... Of course a one single time AI call to specify a quest more as a spec would he worth it once quest is fully specified and being discussed with the user with AI, but yes certain fields like vision statement/outcome are directly translatable ... Find the right balances and nuances not just easy fixes. And yes don't have token spend for things that aren't needed or used and things can happen in the moment first needed by AI." So when a structure costs more than it returns, sort each part instead of deleting it. A part that maps directly from data that already exists is built by code. A part that adds judgment is generated once, lazily, at the moment it is first needed, and refreshed on real events. A part nobody reads is removed. Retrieval follows the context-card approach: each intent is a card, and records are found by relevance rather than pinned. Also tie the spec to the features that already compare alternatives (in Quest, experiments), and remember that some intents endure, such as a repository or an artifact built over time, while the quests under them end.

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

**Extend before adding a solution (Joshua, 2026-11-06).** "We don't add a solution for every task that comes up, but if it's genuinely missing and a long term thing then we do." A new behaviour is first a case, a metric stage, an arm or a flow step of an existing solution. A new solution needs a distinct purpose no sibling holds, several alternatives that could compete on one metric, and a reason to exist if the task that raised it were forgotten; its role record then justifies it against each sibling (`purpose`, `out_of_scope`, `delegates_to`), and a new top-level solution needs the owner's approval. The ESOI repository's explanation `extend-before-adding-a-solution.md` has the test and two examples.

## Who decides what, and where a lesson is kept

**The owner's design suggestion is an alternative, judged like any other (Joshua, 2026-10-22).** "I want tyou to use ESOI to decie whether to act on my product suggestions or not, not just repeat back what I say", and "I'm not a UX expert I want what's best". Check a suggested design against the intent's ideals and the solution's metric, say in a sentence what the records support, then act; where the records support something better, say so and let the owner answer ("unles you can persuad me otherwies", 2026-10-30). This is about design and product suggestions. A plain instruction to carry something out is carried out.

**AI creates structure without waiting; placement is where the owner's input counts most (Joshua, 2026-11-10).** "Don't have blocking on my feedback as a standing rule, AI shouldn't be blocked for creating structure normally it does it all on its own, it's just the most important thing to get my input on when possible". So decide which intent and solution a thing belongs under, and whether it is its own solution, on the strongest model available, build on that decision, and show the owner the placement choices with their siblings so each can be answered in a word ("Not sure would need to see what other siblings are"). The rest of the split:

| Part of the structure | Who decides |
|---|---|
| Ids and links between records | AI, no approval ("ids fields dont need my aporoval", 2026-10-26) |
| The content of AI-written records | AI, improved in place; the owner reviews metrics and may add to anything |
| Placement and hierarchy | AI decides and proceeds; the owner sees the choices when available |
| Which implementation is selected | the authoritative metric ("Selection shouldn't be my call, it should be metrics call", 2026-11-10) |
| Text the owner wrote, and any new, renamed or classifying field | the owner (`INDEX.md`, "Never add a specification field") |

**When the output is poor, improve the specification, not only the output (Joshua, 2026-10-27).** "somethign must be wrong with the esoi specification for this please improve it so that the metric ... gets thr tright kind of qualit". A defect the metric let through is first a gap in an ideal, a solution's definition or the metric; fix that, then the output, so the next session cannot repeat it ("ESOI was suppoesd to ensure the quality woudl be maintained by future AI sessoins").

**Standing rules live in the specifications of the thing they govern (Joshua, 2026-11-09).** "stwnding rules go in ESOI now especiallt for design", in the repository the rule is about. An assistant's private memory keeps only a pointer to them. The reason is his remedy whenever an instruction did not stick: put it where every session reads it, so that "any AI sohuld know to use the same stuff this should'nty be possible for another AI to do it wrong" (2026-10-27). Read a repository's records before working in it, and write a new standing rule there in the same pass as the work.

**A value two records share exists in one place (Joshua, 2026-11-10).** "ESOI spec fields that are exactly the same value as quest fields I think should exist only one place in the data model. If I had designed it from scratch that's how I would have done it." The same holds for behavior: of two code paths meant to act alike, "it should notnjudt be the ssme it should be impossible for it to be different!" (2026-11-02). Two copies kept equal by care or by a check are pattern 4 not yet reached.

**Everything is measurable, so AI always has progress to make (Joshua, 2026-11-08).** "proper esoinapplicstion mesns everything is measursble so Asi should never ysve ezcuse duento wsiting on human, ir can alwsys improce the qyslity of its rec9mmendations and research". A run that only records that a person is awaited has skipped the solution's metric: iterate on one solution and report its metric before and after.

**A warning most people see means fix it or drop it (Joshua, 2026-11-10).** "any warning that happens to most or all users is an indicator that soimething needs fixing or isn't worth warning". The same test applies to an advisory check: it is worth its cost, or it changes.
