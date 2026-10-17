# Video: "Evolutionary Architecture: How do you build systems that can evolve?" (Nikhil Barthwal, Devoxx, 42:47)

Link: https://www.youtube.com/watch?v=jdf80v9vKmc , uploaded 2025-11-11. English captions pulled 2026-10-16
with yt-dlp and saved as a transcript (about 7,300 words; not shipped, as it is a third party's talk). Quotes are
verbatim from those captions, so caption errors remain ("conan" and "conens" for connascence, "conveys law"
for Conway's law, "evolity" for evolvability). Joshua gave it as the technology example of evolvable
structure (2026-10-16). The talk follows Ford, Parsons and Kua's *Building Evolutionary Architectures*
(fitness functions, guided incremental change) without naming the book. It is not Joshua's own work.

## Source: the talk

### Architecture assumes a future it cannot know, so design it to keep changing
- **Insight:** an architecture is built on predictions, the predictions go wrong, and a fixed architecture
  then decays. Evolutionary architecture treats the architecture as having no end state.
- **Evidence:** "when we build an architecture we assume something about the future but in reality future is
  far more uncertain". And: "treat architecture as an evolvable and uh entity. It doesn't really have an end
  state but it's just designed to keep changing." And: "optimize your architecture for change."
- **Relation:** the same premise as principle 7 (humility) and the SKILL.md definition (predict what will be useful
  to change). It is the "over time" half of ESOI.

### Fitness functions: a score for each dimension, guiding each change
- **Insight:** first define the desired characteristics across several dimensions, then a fitness function
  that scores the architecture, then make small changes guided by the score.
- **Evidence:** "you first need a mechanism to evolve mechanism to evaluate how good an architecture is."
  And: "ideally you should be able to assign a score between say 0 to 10 ... because if you don't really have
  a measure of defining how good your architecture is. You really don't know what you're doing." And:
  "you're guided by the fitness function which is essentially guiding you on the direction to take and you
  evaluate across all dimensions."
- **Relation:** principle 2 (ideals and a metric for every solution) applied to architecture. It stops short
  of principle 4's automatic selection: the score guides a person.
- **Limit he names:** "evaluating an architecture is more of an art than a science. It's not always that you can
  have a proper analytical function." Dimensions mix hard and soft constraints, so compromise is normal.

### Small deltas, measured, learned from, carried into the next cycle
- **Evidence:** "guided incremental changes in form of small deltas ... and then you measure you understand like
  how good my architecture is you learn from it and you take it in the next cycle." And: it is "a mindset", not
  a process.
- **Relation:** principle 5 and the Purpose (progress over time); `principles/purpose.md` on carrying learning forward.

### Boundaries: cohesion inside, loose coupling between, bounded contexts as the cut lines
- **Evidence:** "all related things should be in one module." And bounded contexts are "basically going to
  give you boundaries for partitioning". And: "there is no unique way of separating a software into different
  components ... You start with your initial guess and as your system evolves ... you might combine
  microservices, you might split microservices".
- **Relation:** principle 2 (a component per use case where "best" differs) and principle 9. The point that the cut
  itself evolves supports treating the problem-solution network as revisable, not fixed at design time.

### Start simple: a modular monolith before microservices
- **Evidence:** "for most of the organizations who are building services or scratch it's often a good idea to
  start with monolith and then move to microservices." And: "The more number of parts there is, the more
  things can break."
- **Relation:** principle 12 (minimalism) and principle 9's cost test; `principles/difficulties.md` on over-abstraction.

### Loose contracts and tolerant readers
- **Evidence:** "rather than having a strict schema you should have basically a loose schema ... Loose schema is
  a one that can evolve." And: "Be conservative in sending. Send as little as possible." Plus versioning, minor
  for compatible additions and major for breaking changes.
- **Relation:** principle 2's interfaces (what, not how) and principle 3 (interfaces interact despite changing implementations) and `coding/components.md` on changing a shared interface.

### Event sourcing keeps the history, so unanticipated uses stay possible
- **Insight:** store the sequence of changes, not only the current state. The history lets you roll back,
  audit, and build views or workflows nobody planned.
- **Evidence:** "it enables you to create future workflows that you have not anticipated." Examples: a bank
  ledger, version control ("your current source code is nothing but a sums of all the deltas"), one event shown
  differently in several views.
- **Relation:** the SKILL.md definition of evolvable, "retaining benefits from the past", made concrete; principle 11.

### Data outlives the application
- **Evidence:** "data is often more important than the architecture itself because data usually outlives the
  application." And: "Applications they'll be rewritten in couple of years." Do not share schemas across
  services; he ties a Google outage to shared schemas during a gradual rollout.
- **Relation:** pattern 14 (decide what stays stable): the data model is the slower layer, the code the faster one.

### Organization shapes architecture (Conway's law)
- **Evidence:** "if you have four teams working on a compiler you'll have a fourpass compiler. The inverse is
  structure your team such a way that it looks like target architecture."
- **Relation:** a process is a structure too (`principles/purpose.md`); see `definitions_and_advice.md` on Conway.

### Practices for evolvability
- **Evidence (his list):** "take reversible decisions as much as possible"; solve a real problem (startups fail
  when "They basically solve problems that is nobody's problem"); "prefer evolvable over predictable"; "Don't do
  excessive customizations. Basically when you try to please everybody you will end up pleasing nobody";
  "Culture of experimentation"; "don't overarchitect"; "prototyping as a way to know unknown unknowns"; "defer
  decisions till you can"; "avoid leaky abstractions"; "prefer libraries over frameworks"; be careful with
  low-code tools that fail on "the last 30%"; "You can't really have one governance model for everything";
  "architect for testability".
- **Relation:** all fit the principles (problem-first is principle 2; experimentation is principles 4 and 7; several
  governance models is principle 2's "different definition of best"). Three can look like tensions; Joshua
  resolved them (see How Joshua reads the apparent tensions).

## Principles evidenced
- Principles 2, 4 and 5: fitness functions are per-dimension metrics that guide incremental change, the clearest
  outside precedent for metric-guided improvement of a structure.
- Principle 7: "prefer evolvable over predictable" because the future cannot be predicted.
- Principles 2 and 9: cohesion, loose coupling and bounded contexts, with the cut lines themselves revisable.
- Pattern 14: data is the slow layer; contracts are versioned and tolerant.
- The definition of evolvable (keep the benefits of the past): event sourcing and versioning keep history usable.

## How Joshua reads the apparent tensions

Three of the talk's practices look at first like they pull against the principles. Joshua, 2026-10-16,
said none is a contradiction; record them this way, not as counter-evidence:

- **"Don't do excessive customizations."** "handled with the right balance if ESOI's principles are
  effectively applied": principle 2 makes a separate component only where a different definition of best
  could change the outcome, so customization stops where it stops paying.
- **"Don't overarchitect" and "defer decisions."** These "speak to why the structure has to be evolvable so
  architecting can continue to happen over time", and deferring a decision "also speaks to how the intent can
  change". Principle 1's note says the same: the first design is not final, and it evolves.
- **Copying one or two functions instead of importing a library.** "These are not contradictions for me."
  Principle 9 applies structure only where its disadvantages do not outweigh its advantages; a heavy
  dependency can cost more than a few duplicated lines.

## Limits / counter-evidence
- **No automatic selection.** Fitness functions inform people; nothing in the talk selects implementations by
  the metric (principle 4). He also warns the score is often empirical and judgment-laden, which matches
  principle 7's caveat on metrics.
- Software only, one practitioner's talk, examples from large web services. It does not cover adapting to
  people, research or teaching.
