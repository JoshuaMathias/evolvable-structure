# Where the template came from: the Project Documentation board

ESOI's intent template began in 2020 as a public Trello board Joshua Mathias made for structuring any project:
[Project Documentation](https://trello.com/b/8P89TPlo/project-documentation). The board is a reusable template rather
than a worked project, and it still works as a no-code way to apply ESOI. A fuller record of the board is in the skill's
[sources](../../skill/evolvable-structure/sources/trello_project_documentation.md).

## What the board set out to do

The board names its two focuses on its first card: collaboration between the people who understand a problem and the
people who build solutions, and "Comparing alternative solutions for iterative improvement." Each list is explained by a
card in a Documentation list, so the structure documents itself.

## From board lists to the five types

| Board list | Its rule on the board | ESOI today |
|---|---|---|
| Problems to Solve | A card per problem: why it matters, why it is hard, what workarounds exist | [Problem](../templates/problem.md), which kept those questions and added what it is and who has it |
| Ideals | "Ideals are requirements"; each says "How to know this ideal is reached", preferably with a threshold | [Ideal](../templates/ideal.md), whose Hints of Measurement carry the same question |
| Solution Definitions | What a part must do, its goals, knowledge and measures of success; a software version adds parameters, inputs, outputs and effects | [Solution](../templates/solution.md), with the same fields and interface |
| Possible Implementations | "Every implementation has only one definition, while a definition could have many implementations which are mutually exclusive alternatives" | [Implementation](../templates/implementation.md): description, advantages, disadvantages |
| Metric Definitions and Metric Implementations | "A metric can itself be a definition with a specific goal that could be implemented in different ways" | [Metric](../templates/metric.md), and the note that metrics can also be solutions |
| Foundation (principles, dependencies, target audience) | What applies to the whole project, with solutions adding their own | The overall solution network, and settings inherited inward |
| Knowledge | Sources and tools, each linked to the parts of the project it affects | The Solution's Knowledge field |
| Difficulties | What may make the project hard, including missing knowledge or needed approval | Difficulties noted on solutions and in the overall network |

## What carried over

- **Definitions apart from implementations.** "The advantage of separating definitions from implementations is that the
  defined solution can be carried out in different ways which continue to improve, and it should be clear what
  "improving" means."
- **The best is the default, by metric.** "The best Implementation is used by default, where "best" is defined by the
  specified metrics for the Definition." This became principle 4.
- **Measures of success compare alternatives.** A definition's measure is "a way to know whether one implementation is
  better than another in achieving the Definition's goals."
- **Recursion.** Sub-components of an implementation are themselves definitions with alternatives, which is how
  [sub-solutions](when-to-split.md) nest.
- **The loop does not end.** The board's last step reads "You're done! Or, keep improving, adjusting any problems, goals,
  and solutions as necessary."
- **Reversible status, not deletion.** Lanes such as "To Consider", "Probably not" and "Not now" keep options visible and
  movable, the same habit as parking retired records rather than deleting them.

## What changed since

The board gave each type its questions. ESOI added what the board left implicit: a definition of intent and the
principles that order the work; "What it's not" and "Connects to" for each type, so problems are not written as tasks
and the records form a network; Ideal names and State Descriptions; a Metric template with a Record of what is compared;
a single solution at the top that everything implemented falls under; and checks, results logs and automatic selection,
so the default changes when a better implementation is measured rather than when someone moves a card.

## Using the board today

Copy the board in Trello and fill it with the current [templates](../templates/): one card per record, a list per type,
and links between cards for the network. Put each metric run in a checklist or a linked sheet with the date, the
implementation and the version measured, and move the winning implementation to "Chosen". It suits work with no code
and a small team. When records multiply, the [review sheet](../templates/review-sheet.md) or the
[tools](../guides/apply-with-tools.md) take over.

The board itself is mostly empty placeholders: only the Documentation cards, the steps checklist and the software
definition template are written out, and it has no versioning. Treat it as the origin and a starting layout, and the
templates here as the current wording.
