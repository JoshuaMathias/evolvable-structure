# Intents and the five specification types

An **intent** is the container: a meaningful set of specifications with a name and a vision statement (what it is
manifesting, in present tense). See [intents-and-sub-intents.md](intents-and-sub-intents.md) and the
[intent template](../templates/intent.md). Inside it, ESOI writes the intent as five kinds of record: **problems**,
**ideals**, **solutions**, **implementations** and **metrics**. Each is defined, with the questions a record must answer,
in the author's own words. Those words are not repeated here: open the template for the type you need.

An intent brings insights on risks, uncertainties and opportunities. The author's definition maps them to the types:

> Risks are addressed by considering disadvantages of Implementations and Metrics, uncertainties are addressed by
> Metrics, and opportunities are addressed by Solutions.

That mapping is also why a part becomes a sub-intent only for an opportunity (see
[when-to-create-a-sub-intent.md](when-to-create-a-sub-intent.md)).

| Type | Template | Answers |
|---|---|---|
| Problem | [problem.md](../templates/problem.md) | What motivated the intent |
| Ideal | [ideal.md](../templates/ideal.md) | The future state, in one dimension |
| Solution | [solution.md](../templates/solution.md) | How one or more problems are addressed, and its interface |
| Implementation | [implementation.md](../templates/implementation.md) | A built alternative that carries out a solution |
| Metric | [metric.md](../templates/metric.md) | How to measure the distance from an implementation to an ideal |

Each template starts with the definition, lists the questions to answer, and ends with what the type is not and what it
connects to. The definitions of intent, evolvable, structure and the rest are in
[from-the-skill.md](from-the-skill.md). The template grew out of a 2020 project board; see
[project-documentation-board.md](project-documentation-board.md).

## Habits that make records useful

- **Give a part its own solution only when best differs and it matters, and its own sub-intent only for an opportunity.** See
  [when-to-create-a-sub-intent.md](when-to-create-a-sub-intent.md).
- **Give every record a short, stable id.** Other records link to it, so renaming it is a change to many files.
- **Fill every field.** A field you cannot answer is a gap worth knowing about. A solution's `milestones` may stay empty
  (no milestone is chosen yet); for any other field, say what you know and name what the metric cannot see in the
  metric's `scoped_purpose`, or a weakness in an implementation's `disadvantages`.
- **Keep numbers out of prose.** Scores belong to the results log, where they carry the commit and the cases. A
  sentence that says "passes most cases" is out of date the day a case is added.
- **Say when each Metric is run.** Timing is not a field of the Metric template, so it belongs to a solution that governs the
  metrics: see [when-metrics-are-run.md](when-metrics-are-run.md).
- **A problem is a challenge, a difficulty, or how an ideal is not reached; it is not a decision, task,
  recommendation or component**, though each of those can *have* problems. "Add a cache" is a task. "Reports take a
  minute to load and people stop opening them" is a problem.
