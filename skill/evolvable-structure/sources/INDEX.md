# evolvable-structure: sources index

The evidence behind the skill: research notes on outside research and a public talk. Come
here only when you need the original wording, a quote, or the evidence for a claim; the patterns in
`../principles.md` and the examples in `../coding.md` and `../other-categories.md` already summarize
it. A pointer reads `<file> > <heading>`: run `grep -n '<heading>' <file>` and read that section, not
the whole file. Notes written before 2026-10-14 say "ideal N" or "P N" for what is now pattern N in
`../principles.md`.

On 2026-10-16 Joshua renamed the skill from adaptable structure to Evolvable Structure that Optimizes
Intent (ESOI) and reordered its ideals into 13 prioritized principles. Notes are research records and
keep their original wording, so a note written between 2026-10-14 and 2026-10-16 that cites "ideal N"
means the old order. Old ideal → new principle: 1 → 2, 2 → 2, 3 → 4, 4 → 6, 5 → 3, 6 → 5, 7 → 12, 8 → 8,
9 → 7, 10 → 13, 11 → 9, 12 → 11, 13 → 10 (new principle 1, practical evolvable structure first, has no
old equivalent). In those notes "adaptable" usually means what SKILL.md now calls evolvable.

## Evidence by topic

| Topic | Source sections |
|---|---|
| Functional components: iterate inside, reuse across systems | definitions, versioning, behaviour tests and reuse evidence: `components_research.md > Proposed wording`, `> What this changes in the skill` |
| Definition and vocabulary (adaptable, adaptive, evolvable, flexible, changeable, variability) | `definitions_and_advice.md > A. Vocabulary`, `> Proposed definition`; evolvable vs adaptable: `evolutionary_architecture_talk.md > Architecture assumes a future it cannot know, so design it to keep changing` |
| Parts that change at different rates (layers, versioning, who decides) | `definitions_and_advice.md > Brand 1994 and the Long Now talk: separate by rate of change`, `> How close is the building analogue? An honest assessment` |
| When NOT to generalize | costs and counter-evidence from outside research: `public_research.md > What this changes in the skill` |
| Evolvable architecture: fitness functions, incremental change, loose contracts, event sourcing | `evolutionary_architecture_talk.md > Fitness functions: a score for each dimension, guiding each change`, `> Event sourcing keeps the history, so unanticipated uses stay possible`, `> Limits / counter-evidence` |

## What each source file holds, and when to open it


| File | Covers | Joshua's named source |
|---|---|---|
| `public_research.md` | outside research: modularity, configuration cost, adaptable vs adaptive, personalization in education, requisite variety, QCA critique, over-abstraction, size and defects, AI-generated code structure; what supports, qualifies or challenges the ideals | not Joshua's own work (added to ground and test the skill) |
| `definitions_and_advice.md` | how established sources define adaptable, adaptive, flexible, changeability, variability and neighbors; the building analogue; general advice (one-way doors, last responsible moment, Gall, Conway); proposed definition | not Joshua's own work (added to ground the vocabulary and advice) |
| `components_research.md` | outside research on software components and reuse: definitions (McIlroy, Szyperski), reuse evidence, iterating a component versus staying compatible (breaking changes, Hyrum's law), non-software component examples, reuse failures | not Joshua's own work (added to ground pattern 15) |
| `evolutionary_architecture_talk.md` | Nikhil Barthwal's Devoxx talk on evolutionary architecture: fitness functions, guided incremental change, cohesion and bounded contexts, loose contracts, event sourcing, data outliving code, practices, and three apparent tensions (customization, up-front structure, copying code) and how Joshua resolves them | not Joshua's own work; his technology example of evolvable structure (2026-10-16) |
