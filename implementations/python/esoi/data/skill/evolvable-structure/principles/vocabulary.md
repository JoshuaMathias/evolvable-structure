# Evolvable structure: definition and vocabulary

Part of `../principles.md`. The definition, the component definition, and which neighbouring words to use. Source pointers read `file > heading`, with files in `../sources/`. Quotes are verbatim, and Joshua's typed inputs keep their typos.

## Definition and vocabulary

Joshua's definitions in `SKILL.md` are the authority: **evolvable** is changeable towards a
different purpose while keeping the benefits of the past; **structure** is relatively stable and
enables other purposes that lean on it; **evolvable structure** balances longevity and changeability
by predicting what will be useful to change and choosing a niche of changeability from the
structure's purpose; **adaptable** is changeable to handle different situations or contexts in the
moment; **intent** is a conceptualization within consciousness that motivates a future state, specified
as problems, solutions, implementations, ideals and metrics. The practice is named **Evolvable
Structure that Optimizes Intent (ESOI)**. Until 2026-10-16 the skill was called adaptable structure,
and "adaptable" carried the meaning "evolvable" has now; older notes in `../sources/` use the old word.

A working version for design and review, in terms of mechanism: a stable core that a person can fit
to a new case, such as another person, domain, dataset or experiment, by changing a parameter, a name
or content at the edge, without editing the core. It is built so each change can be tried, compared
with the alternatives and kept or reversed, so the work improves over iterations. (Proposed from
`definitions_and_advice.md > Proposed definition`, before `SKILL.md` was rewritten.)

Words that overlap, and when to use which (sources and verification labels in
`definitions_and_advice.md`):

- **Evolvable and adaptable.** Joshua, 2026-10-16: "I think this is actually more evolvable structure than
  adaptable structure even thogu hit also enables the system to adapt to individual cases." Evolvable is
  change across iterations and design cycles that keeps the benefits of the past; adaptable is fitting a
  situation or case now. They are not rivals: "the evolving structure enables adaptation" (Joshua,
  2026-10-16, on why the SKILL.md opening says the design "is adaptable to changing intentions,
  contexts, priorities, and problems"). ESOI is evolvable at its center (principles 3, 4, 5 and 11 and the
  Purpose, progress over time) and adaptable at its edge (principles 2 and 12, a component per use case,
  only what differs specified per case). Outside support: in biology, evolvability is the capacity to
  generate useful heritable variation (Kirschner and Gerhart 1998); in software, evolutionary architecture
  "supports guided, incremental change across multiple dimensions" (Ford, Parsons and Kua 2017; a talk on
  it: `../sources/evolutionary_architecture_talk.md`). "Evolving" was considered for the name and
  declined (2026-10-16): evolvable names the designed capacity, and change alone can also be decay.
- **Adaptable and adaptive.** In human-computer interaction, adaptable means a person changes the
  system and adaptive means it changes itself (`> McGrenere, Baecker, Booth 2007`). Systems engineering
  splits the words the other way round, by whether the change agent is inside the system
  (`> Ross, Rhodes, Hastings 2008`). Joshua's use is defined by intent, not agent (his clarification,
  2026-10-16): a structure is adaptable when it is built to be adapted intentionally, use case by use
  case, even when an AI or automation does the adapting (as in metric-driven selection, principle 4). It is
  both adaptable and adaptive in the HCI sense, but intentional adaptation by use case is the point.
- **Flexible.** Used for both ease of change and outside-driven change. Too loose; avoid unless defined.
- **Changeability.** The umbrella term, which Ross et al. count as the number of change paths available.
  Evolvable structure is one kind. A usable test for pattern 1: count the change paths that need no
  core edit.
- **Modifiability, modularity, reusability** (ISO/IEC 25010): the enabling properties, not the goal.
  Modifiability is the cost of editing; evolvable structure aims for no edit of the core.
- **Variability** (`> Svahnberg, van Gurp, Bosch 2005`): the closest software neighbor, one core and many
  products. It usually assumes the set of variants is known in advance, while Joshua's cases can be new.
- **Extensibility and configurability.** Extensibility adds capability through plug points;
  configurability is the settings layer only. A structure can also be adaptable through definitions and
  content. (No authoritative definition of either was fetched.)
- **Robust, resilient, antifragile.** Robust resists change; evolvable and adaptable structures accommodate it. Avoid the others.

The closest analogue outside software is building design: supports and infill (Habraken) and layers by
rate of change (Duffy, Brand). It fits patterns 1, 5 and 14, and the point that most parts rarely change. It
does not cover the purpose (comparing alternatives and carrying learning forward), many cases at once, or
measurement, so use it as an illustration, not as support (`definitions_and_advice.md > How close is the
building analogue? An honest assessment`).

**Functional component:** one piece of a larger system with an explicit interface and explicit
dependencies, defined by what it does and its measure of success. Other systems use it by changing
only parameters, composed without modification; its inside stays free to improve behind the same
interface. (From `components_research.md > Proposed wording`, which draws on Szyperski and on
Heineman and Councill, plus Joshua's measure-of-success point under pattern 15.)
