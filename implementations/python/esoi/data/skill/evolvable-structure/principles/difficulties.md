# Evolvable structure: difficulties

Part of `../principles.md`. When generality is the wrong move, from Joshua's pushback and from where his structures failed. Source pointers read `file > heading`, with files in `../sources/`. Quotes are verbatim, and Joshua's typed inputs keep their typos.

## Difficulties: when generality is the wrong move

These come from Joshua's own pushback and from where his structures failed. They are weighed
alongside the patterns.

- **Generality earns its place through the purpose, and scope wins most corrections.** `SKILL.md`
  asks to predict what will be useful to change and says improving the structure up front is worth
  the time, so the test is not "has a second case arrived" but "can you name the likely change and
  the purpose it serves". What fails is generality no purpose calls for (principle 9's own limit: a structure only where its advantages outweigh its costs for this purpose and niche): an abstraction nobody asked
  for on a scoped task, or a second mechanism that duplicates an existing one (principle 8 says use what
  exists). The 2026-06-07 corrections analysis counts 157 "scope limitation" corrections (56.1% of his
  feedback) with the fix "minimum viable NOW, iterate later". That pulls against his standing instruction to
  "build the complete and correct solution". They meet here: exactly what was asked, complete and
  correct, and nothing speculative beyond it.
- **But a general goal he has named is the need.** When Joshua (or the task) already stated the
  structural goal ("auto support everything Y supports with no code per integration"), narrowing it
  back to one case and asking him to justify it again goes backwards.
- **Generic is not a reason to keep a feature.** A feature was made generic and was then removed,
  because only one org would use it: removing a feature can be better than making it ever more
  generic. Ask who the second user is. Against this, promising users that the features they request
  will be built is bespoke service.
- **A shared default works best with a user-settable parameter.** On 2026-10-12 a sync that was on
  by default flooded his calendar with an event for every recurring item, including past dates. The
  fix was a parameter, not a removal: the behaviour became opt-in the same day, and its bounded time
  window stayed the default but became changeable. A default that acts at scale should start off or bounded until the person chooses.
- **A measured value stops being measured once callers can override it.** Letting a caller set a
  parameter whose value comes from measurement breaks the evaluation.
- **The right level matters.** A category defined per case was too specific and broke the
  measurement, so such categories now span cases. Too high is as wrong as too low. Placing something in a hierarchy needs
  a written reason.
- **A general structure still gives a specific answer.** Generic output is rejected. The
  structure is general so the result can be exact for this person and this input.
- **Generality is a claim until a real case shows it.** His dissertation proposal says the method
  could be applied to any theory, but no second-domain run is reported. A pooled estimate built to be general lost to its own floor and to plain
  prompting, and features have been documented as working before any live run.
- **Flexibility has a cost.** The same openness that lets a method fit any case makes it hard to
  check. Naming the weakness when choosing the flexible option helps the next person. Joshua marked Lucas (1974) as key:
  "The greatest strengths and the fundamental weaknesses of the case survey method are the same: the
  almost infinite flexibility of the theories and concepts that can be studied."
- **Copies drift.** Every time the core lived in two places, the copies diverged: a course's syllabus,
  course page and handoff gave three different answers on when it runs and where the work lives; one
  set of docs described an integration three ways; a case reimplemented the core's formula with
  keyword matching; a playbook and its code disagreed on a default; three consumers of one library
  each hand-rolled the same driver. One source with pointers, or a test that copies match, keeps them together. This is principle 9 applied to information and instructions as much as to code.
- **Silent defaults and silent failures hide that the structure broke.** A deployment pinned to one
  model ran every task on another for weeks with nothing in the log; a client call returned an empty
  list on any failure and never raised; a dead optimizer silently broke a stability guarantee. A
  parameter that falls back is best said aloud in the log.
- **An extension point is real once it is built and tested.** A README that promises a
  parameter or a selection rule the code does not have is not an extension point yet.
- **Some things stay outside the standard set.** Healing is not in the standard tests because it
  cannot be verified well yet, and his grounded theory study leaves out manifestation, "as the
  expected outcomes may be open-ended and vary widely across participants." State what the structure
  does not cover.
- **People set the AI's direction.** An adaptable system lets a person widen what the AI may do
  (for example from only working to also planning); the AI suggests rather than widening it for
  itself. Autonomy is off by default, and nothing opts itself in.

## Examples from his frameworks (evidence, not principles)

A principle above must not depend on any of these, and each stays true if the framework is retired.

**Difficulties**
- Quest: Team Reports was made generic and was then removed, because only one org would use it:
  "the answer can be to remove the feature from Quest rather than keep genericizing it". Against
  this, the Quest course promises students that the founder builds the features they request.
- Quest: on 2026-10-12 calendar sync was on by default and flooded his calendar with events for
  every habit, including past dates ("because sync was on by default now I ahve tons and tons of
  calendar event"); sync became opt-in the same day, and he asked for the 7-day window to stay the
  default but be changeable.
- Concept AI: a per-domain paradigm was too specific and broke the measurement, so paradigms are
  cross-domain.
- Concept AI: the pooled estimate lost to its floor and to plain prompting (direction 0.562 vs floor
  0.604 vs llm_baseline 0.872).
- QAR: the playbook says "no LIVE turn has run on either feature".
- Super Psychic Academy: SPA 101's syllabus, course page and handoff give three different answers on
  when it runs and where the work lives.
- Concept AI: the docs describe the integration three ways, and a domain reimplemented the core's
  formula with keyword matching.
- QAR: the playbook and code disagree on the default model ladder, and three QAR consumers each
  hand-rolled the same driver.
- QAR: a lane "pinned Fable ran every deep task on its balanced model for weeks with nothing in the
  log saying so", and a client `list_tasks` "returns `[]` on ANY failure and never raises".
- Concept AI: a dead vector-store optimizer was "silently breaking identity stability".
- A name-keyed registry library of his: the README promises a `version` parameter and metric-based selection that the code
  does not have.
- Quest: autopilot lets a person widen what the AI may do (`plan_and_work`), and is "Off by default; a
  quest never opts itself in."

**Difficulties (collaborative innovation)**
- Cantr governance: the proposals carry many thresholds (1.5 votes, 10 vetoes, monthly membership,
  five-times contribution for councilors) and admit "this may seem like a slow process"; their
  adoption and results are not recorded. Source: `cantr_governance_proposals.md > Limits / counter-evidence`.

