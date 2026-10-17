Joshua's public Trello board "Project Documentation" (https://trello.com/b/8P89TPlo/project-documentation), a reusable project-structuring template he made in 2020 and the origin of ESOI's intent template. Read from a board export (10 lists, 34 cards, 1 member) and checked against the live board on 2026-10-14. Board history: copied on 2020-06-22 from an earlier board, "Project Design 2"; last activity 2020-10-17.

## Project Documentation (https://trello.com/b/8P89TPlo/project-documentation)

Board-level insight: the board is a reusable project-structuring template rather than a worked project. Almost every checklist is an empty placeholder, and every checklist item in the export is "[incomplete]". The only worked-out content is in the Documentation list descriptions, the Steps checklist, and one example of a parameter interface (Software Definition Template). Evidence of adaptability is therefore mostly the design of the templates, not a populated example. Board labelNames are all blank, so labels are not yet defined.

### Documentation

#### Purpose of this Board
- Insight: the board's own organization is stated up front, with two stated focuses: collaboration between problem-understanders and solution-builders, and comparing alternative solutions for iterative improvement. A map of each list is kept here, so the board documents its own structure.
- Quote: "Each list in the board template is explained by a card in the Documentation list."
- Why adaptable: the structure is described as a template that any project can fill in, and the explanation of the structure lives inside the structure, so a new user can adapt the lists without a separate manual.
- Links: none.

#### Steps to project completion
- Insight: a 16-step procedure, each step pointing to a template card. It loops back ("keep improving, adjusting any problems, goals, and solutions as necessary") rather than ending.
- Quote: "Consider whether there may be better alternative Implementations to try, and test these."
- Why adaptable: the process is generic and re-runnable for any project; the step list references templates by card link, so the procedure is parameterized by which templates are used.
- Checklist "Project Steps" still has items such as "Decide what to use labels for" and "Review problems again using new information", all marked incomplete, so the board is a template in progress.
- Links: https://trello.com/c/liMWBDGN/7-ideal-template ; https://trello.com/c/r0jD5vps/16-problem-template ; https://trello.com/c/MPOpLLyq/6-definition-template ; https://trello.com/c/oongtekn/13-implementation-template ; https://trello.com/c/n9O3CUFF/1-purpose-of-this-board ; https://trello.com/c/AbGHJoqw/17-target-audience-template ; https://trello.com/c/PfCeb99j/19-brainstorm ; https://trello.com/c/umTUjN7y/15-labels

#### Labels
- Insight: labels are a second classification axis separate from lists. The card gives examples of label dimensions (problem, time estimate, target audience) and notes that labels may differ by list.
- Quote: "There might be different labels for different lists."
- Why adaptable: tags let the same items be cut by problem, audience, or effort without restructuring the lists. The export shows no label names defined yet (labelNames all blank), so this is an open decision.
- Links: none.

#### Problems to Solve
- Insight: problems are the root of the structure. Each problem gets its own card, and a colored label per problem is used to trace which goals and solutions address it.
- Quote: "To make sure all problems are solved and to track solutions by problem, you could have a colored label for each problem and apply these to the relevant goals and solutions."
- Why adaptable: traceability from problem to solution means a solution can be swapped out while the problem stays fixed, and the coverage check still works.
- Links: https://trello.com/c/vv9CJtY4 (problem card, referenced in description)

#### Ideals
- Insight: ideals are project-level requirements, and success is defined as all of them being met. Each ideal names the problems it solves and how its attainment is measured.
- Quote: "Ideals are requirements; if all goals are met, the project is a success."
- Why adaptable: the success criteria sit above any implementation, so implementations can change while the ideal list stays the acceptance test.
- Links: none.

#### Foundation (documentation card)
- Insight: this card holds what applies to the whole project (principles, target audience, dependencies). It also separates project-wide dependencies from solution-specific ones.
- Quote: "Dependencies for the whole project and a description of how they're used in the project. There may also be dependencies specific to each solution."
- Why adaptable: this is a defaults layer. Project-wide values are set once and solutions can add or override their own.
- Links: none.

#### Knowledge (documentation card)
- Insight: knowledge covers beliefs, prior knowledge, and desires relative to goals, and is linked to the parts of the project it affects.
- Quote: "Knowledge may also be desires in relation to the goals, without necessarily being requirements."
- Why adaptable: knowledge is stored as cards that can be linked into any definition or implementation, so one resource can serve many solutions.
- Links: none.

#### Solution Definitions (documentation card)
- Insight: the core separation of the framework. A definition states what a part of the solution must do; implementations are alternatives. The default is the best implementation, judged by the definition's metrics.
- Quote: "The best Implementation is used by default, where 'best' is defined by the specified metrics for the Definition."
- Why adaptable: a default is chosen by a stated measure, not hard-coded, so the default changes when a better implementation is measured.
- Links: none.

#### Implementations (documentation card)
- Insight: an implementation is any form of solution (steps, commitments, data, code). It must link back to exactly one definition, and sub-components should themselves be definitions with alternatives.
- Quote: "Every implementation has only one definition, while a definition could have many implementations which are mutually exclusive alternatives."
- Why adaptable: this is the swappable-component rule, and the recursion (sub-components as definitions) lets the same pattern nest to any depth.
- Links: none.

#### Metrics (documentation card)
- Insight: metrics reuse the definition and implementation templates, so a measurement is itself a swappable component.
- Quote: "A metric can itself be a definition with a specific goal that could be implemented in different ways."
- Why adaptable: one framework covers both the solution and its measurement, so the same mechanism swaps either.
- Links: none.

#### Difficulties (documentation card)
- Insight: this card is the list of things that may make the project hard, such as missing knowledge or required approval. It is the equivalent of the Difficulties list (see the empty Difficulties list below).
- Quote: "The Difficulties list describes that may make the project hard to implement, including lack of knowledge or needed approval."
- Why adaptable: blockers are captured in the same structure as everything else, so they can be reviewed the same way.
- Links: none.

### Foundation

#### Brainstorm
- Insight: all major parts are brainstormed in one card before splitting into separate cards. The checklists include "Probably won't be done" as an explicit scope-out bucket, alongside ideals, problems, solutions to define, and possible implementations.
- Quote: "Brainstorm all major parts of the project in one card, before making cards for each part."
- Why adaptable: scope is a named parameter ("Probably won't be done"), so out-of-scope items are kept visible and can be moved back in.
- Links: none.

#### Principles
- Insight: guiding principles are a project-level default. The description suggests a reusable organization-wide principles template.
- Quote: "You could create a principles template for the organization."
- Why adaptable: principles are defined once and reused across projects, so the same defaults apply to every board that copies this template. Checklist is empty in the export.
- Links: none.

#### Dependencies
- Insight: dependencies are a project-level list, with per-solution dependencies added elsewhere. Checklist empty in the export.
- Quote: "What does this project depend on in order to be successful?"
- Why adaptable: same layered default model as Foundation (project-wide, then per solution).
- Links: none.

#### Target Audience Template
- Insight: the audience is a parameter that changes how the project is built, not only who it is for. One question asks how the audience affects the way the project should be done.
- Quote: "How do they affect how the project should be done?"
- Why adaptable: audience is a reusable profile (benefit, uniqueness, difficulty, impact on build). New audiences are new cards of the same shape.
- Links: https://trello.com/c/AbGHJoqw/17-target-audience-template (the Foundation copy is the template itself)

### Knowledge

#### Knowledge Overview
- Insight: a hub of sources and tools, with a "Related links" checklist that is empty in the export.
- Quote: "Sources of information or tools that relate to this project."
- Why adaptable: a hub with per-resource cards means resources can be added or swapped without touching the definitions that point to them.
- Links: none.

#### Resource Template
- Insight: each resource has a standard shape: link, parts of the project it relates to, how it can be used, other notes.
- Quote (checklist): "Parts of the project this resource relates to"
- Why adaptable: the "parts this resource relates to" field makes a resource reusable across solutions, and the template keeps every resource in the same schema.
- Links: none.

#### Favorites
- Insight: a staging area for resources currently in use, with an "Archived Cards" checklist.
- Quote: "Place under this card resources that are currently useful or you want to look at soon."
- Why adaptable: status buckets are cards, not fixed structure, so the working set can change without moving items.
- Links: none.

#### To Consider
- Insight: a parking card for options under evaluation, with the same archived-cards checklist pattern.
- Quote: "Put under this card options to consider."
- Why adaptable: same status-bucket pattern as Favorites, so candidate options can be promoted or dropped.
- Links: none.

#### Not now
- Insight: items that are not useful now but not deleted go into this bucket.
- Quote: "For cards that you're not ready to actually archive or delete, but that aren't useful right now."
- Why adaptable: a reversible deferral lane, so the board can be re-scoped without losing work.
- Links: none.

### Problems to Solve

#### Problem Template
- Insight: each problem is a card with three standard questions: why it matters, why it is hard, and what workarounds exist.
- Quote: "Users have a need." / checklist: "What solutions already exist? (Workarounds)"
- Why adaptable: the three questions are a fixed schema applied to every problem, so problems can be compared and new problems slot in without changing the template.
- Links: https://trello.com/c/r0jD5vps/16-problem-template ; https://trello.com/c/vv9CJtY4 (problem card, from Documentation description)

### Ideals

#### Ideal Template
- Insight: each ideal carries its own measure ("How to know this ideal is reached") and the problems it addresses.
- Quote: "Details about what the ideal looks like." / checklist: "How to know this ideal is reached"
- Why adaptable: every ideal has an explicit, testable measure, so acceptance is parameterized per ideal rather than being a single global check.
- Links: https://trello.com/c/liMWBDGN/7-ideal-template

### Solution Definitions

#### Definition Template
- Insight: the generic definition shape: possible implementations, goals, measures of success, knowledge. The measure of success is explicitly not the goal but the comparison criterion between implementations.
- Quote: "Measures of Success: ... a way to know whether one implementation is better than another in achieving the Definition's goals."
- Why adaptable: the comparison criterion is a parameter of the definition, so the choice of implementation can change when the measure changes. The metric can itself be a definition.
- Links: https://trello.com/c/MPOpLLyq/6-definition-template

#### Software Definition Template
- Insight: the richest parameter interface on the board. It adds Parameters, Inputs, Outputs, Effects, and an Interface Details line in the form "var_name (type)=default: Description". It is the only place a default value is written explicitly.
- Quote (checklist): "var_name (type)=default: Description"
- Why adaptable: this is the closest evidence for "parameters in one place with defaults users can override". Each parameter declares name, type, default, and purpose, so every implementation of this definition shares one interface contract. Observation: the template lists "Possible Implementations" twice, which looks like a duplicate to clean up.
- Links: none.

#### Verified
- Insight: a status lane for definitions already confirmed, with the archived-cards pattern.
- Quote (checklist): "Archived Cards"
- Why adaptable: status is a container card, so the lane can change without restructuring definitions.
- Links: none.

#### In Progress
- Insight: a status lane for definitions being worked on.
- Quote (checklist): "Archived Cards"
- Why adaptable: same status-container pattern.
- Links: none.

#### To Consider
- Insight: candidate definitions parked for review.
- Quote (checklist): "Archived Cards"
- Why adaptable: same status-container pattern.
- Links: none.

#### Probably not
- Insight: definitions rejected for now but kept on the board.
- Quote (checklist): "Archived Cards"
- Why adaptable: a reversible rejection lane.
- Links: none.

### Possible Implementations

#### Implementation Template
- Insight: each implementation states how it achieves its definition's goals and lists advantages, sub-components, and disadvantages. The description requires a link back to the definition.
- Quote: "Describe how this implementation achieves the goals of its solution definition."
- Why adaptable: a fixed link from implementation to definition lets alternatives be compared and swapped while the definition stays the same.
- Links: https://trello.com/c/oongtekn/13-implementation-template

#### Software Implementation Template
- Insight: implementations expose their own Parameters and Interface Details, with Dependencies, Effects, and Considerations, so the interface is per implementation but expected to match its definition.
- Quote (checklist): "Interface Details" / "Parameters" / "Sub-components"
- Why adaptable: a shared interface contract between definition and implementation lets implementations be replaced behind a stable interface. Observation: there is no explicit version field on any card, so versioning is implied by the Chosen lanes and the "keep improving" step, not recorded.
- Links: none.

#### Chosen - Done
- Insight: the lane for the implementation currently selected and completed for a definition. This matches "the best Implementation is used by default".
- Quote (checklist): "Archived Cards"
- Why adaptable: the default implementation is a status, so changing the default is moving a card between lanes.
- Links: none.

#### Chosen - To Do
- Insight: the lane for a selected implementation not yet built.
- Quote (checklist): "Archived Cards"
- Why adaptable: a selection can be made before work starts, and the lane shows what is queued.
- Links: none.

#### To Consider
- Insight: candidate implementations under evaluation.
- Quote (checklist): "Archived Cards"
- Why adaptable: same pattern as the other status lanes.
- Links: none.

#### Probably not
- Insight: rejected implementations kept for reference.
- Quote (checklist): "Archived Cards"
- Why adaptable: reversible rejection lane.
- Links: none.

### Metric Definitions
- Insight: this list is empty in the export (no cards). The Metrics card (Documentation list) says metrics use the same definition and implementation templates, so this list is planned to hold metric definitions.
- Links: none.

### Metric Implementations
- Insight: empty in the export. Planned for metric implementations, per the Metrics card.
- Links: none.

### Difficulties
- Insight: this list is empty in the export. The Difficulties card that describes it is in the Documentation list (see above).
- Links: none.

## Linked repos, docs and boards found
- Board: https://trello.com/b/8P89TPlo/project-documentation (short link 8P89TPlo, board name in export "Project Documentation"; copied from an earlier board on 2020-06-22)
- Template cards: https://trello.com/c/liMWBDGN/7-ideal-template ; https://trello.com/c/r0jD5vps/16-problem-template ; https://trello.com/c/MPOpLLyq/6-definition-template ; https://trello.com/c/oongtekn/13-implementation-template ; https://trello.com/c/AbGHJoqw/17-target-audience-template
- Other referenced cards: https://trello.com/c/n9O3CUFF/1-purpose-of-this-board ; https://trello.com/c/PfCeb99j/19-brainstorm ; https://trello.com/c/umTUjN7y/15-labels ; https://trello.com/c/vv9CJtY4
- No repos, attachments, or external document links appear anywhere in the export.

## Principles evidenced
1. One core framework, many projects: "Documentation > Purpose of this Board" (lists explained by a card, so the structure documents itself), "Documentation > Steps to project completion" (generic, re-runnable procedure).
2. Parameters in one place: "Solution Definitions > Software Definition Template" (Parameters, Interface Details with "var_name (type)=default: Description"), "Foundation > Target Audience Template" (audience shapes the build).
3. Reusable, swappable components: "Documentation > Solution Definitions" (definition vs implementation, mutually exclusive alternatives), "Possible Implementations > Implementation Template" (one definition link per implementation), "Documentation > Metrics" (metrics reuse the same templates, recursive composition).
4. Defaults users can override: "Documentation > Solution Definitions" (best implementation by metric is the default), "Foundation > Dependencies" (project-wide, then per-solution), "Possible Implementations > Chosen - Done / Chosen - To Do" (default is a movable status), "Documentation > Ideals" (layered goals at project, definition and implementation levels).
5. Documentation that adapts: "Documentation > Labels" (labels as a second axis), "Documentation > Problems to Solve" (traceability from problem to swappable solution), "Knowledge > Resource Template" (resources linked to the parts they affect), "Knowledge > Not now / Favorites / To Consider" (reversible status buckets).
6. Caveat for the reader: the evidence is mostly template design. Only the Documentation descriptions, the Steps checklist, and the Software Definition Template example contain real content; the rest is empty placeholders, and no explicit versioning or worked example exists on the board.

## Verified against the board (Opus pass)

Read directly from the board on 2026-10-14 (card descriptions via the Trello connector; the "Project Steps" checklist from the board export).

- Documentation > Purpose of this Board: "2. Comparing alternative solutions for iterative improvement."
- Documentation > Solution Definitions: "The advantage of separating definitions from implementations is that the defined solution can be carried out in different ways which continue to improve, and it should be clear what "improving" means."
- Documentation > Solution Definitions: "The best Implementation is used by default, where "best" is defined by the specified metrics for the Definition."
- Documentation > Ideals: "**How to know this ideal is reached**: A metric or way to measure this ideal, preferably including when exactly the ideal has been sufficiently met (threshold)."
- Documentation > Steps to project completion, checklist "Project Steps": "Consider whether there may be better alternative Implementations to try, and test these."
- Documentation > Steps to project completion, checklist "Project Steps": "You're done! Or, keep improving, adjusting any problems, goals, and solutions as necessary."
