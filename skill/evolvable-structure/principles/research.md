# Evolvable structure: outside research and thin evidence

Part of `../principles.md`. What public research supports, qualifies or challenges, and where the evidence is thin. Source pointers read `file > heading`, with files in `../sources/`. Quotes are verbatim, and Joshua's typed inputs keep their typos.

## What public and scientific research adds

Notes: `sources/public_research.md` (26 sources, each marked by how it was verified). It supports the
purpose and patterns 2, 8, 9 and 13 with theory and case evidence (Parnas 1972, Baldwin and Clark 2002,
Simon 1962, Ford et al. 2017); only MacCormack et al. 2006 is empirical, and it measures structure, not
outcomes. Say "supported by theory and case evidence", not "proven". It also qualifies several patterns:

- **Cost clause for patterns 1, 4, 6 and 7 (principle 9's limit).** Configuration is expensive (Sayagh et al. 2020; Xu et al.
  2015 found up to 54 percent of parameters seldom set), a core pays back only with enough reuse (Krüger
  and Berger 2020), and a wrong abstraction costs more than duplication (Metz 2016, Fowler on YAGNI).
  Suggested test on pattern 1: the core did not get harder to understand.
- **Defaults must be good and bounded (patterns 3, 10, 11).** People rarely customize (Mackay 1991), so a
  default carries most of the weight, which matches the 2026-10-12 calendar-sync lesson. User-controlled
  adaptation was preferred in one lab test (Findlater and McGrenere 2004, small evidence).
- **Personalization needs a measured benefit (pattern 5).** Learning-styles matching has no supporting
  evidence (Pashler et al. 2008); intelligent tutoring does (Kulik and Fletcher 2016); universal design
  for learning outcomes are thinly evidenced (Capp 2017).
- **Flexible case methods can fail (pattern 12).** Lucas and Szatrowski 2014 report simulations where
  qualitative comparative analysis fails with known answers, so check a flexible method against a case
  whose answer is known.
- **Change is concentrated** (Qiu et al. 2013, Fenton and Ohlsson 2000): most parts never change, so
  spend flexibility where change happens and measure before assuming.
- **Size is not the evidence.** Studies disagree on size and defects (Koru et al. 2009: smaller classes
  proportionally worse; Hatton 1997: middle sizes best; Fenton and Ohlsson: no link), and structure
  metrics often track size (El Emam et al. 2001). The support is for named stable interfaces and hidden
  change (Parnas, Simon), not small files. Two 2026 preprints (Hu et al.; Zhu et al.) report monolithic
  agent output, which backs Joshua's observation, while a third (Mao et al.) found small differences
  between AI and human code in real repositories.
- **A check on variety (Ashby 1956):** the variety at the edge should match the variety of the cases,
  which guards against both over-generalizing and under-fitting.
- Undo a failed generalization by inlining it back (Metz), and guard what must stay true with checks that
  run (Ford et al.'s fitness functions).

No study found tests "one core, parameters at the edge" as a whole against alternatives under control.
That comparison is Joshua's own to run, which suits pattern 9.

From definitions and general advice (`definitions_and_advice.md > B. General advice`, labelled by
evidence strength there):

- **Pattern 3 by reversibility** (Bezos 2015, one-way and two-way doors): heavy approval on a reversible
  default costs experimentation, and an irreversible one deserves the pause.
- **The last responsible moment** (Poppendieck 2003) and **making everything easy to change has a
  complexity price** (Fowler): both argue for holding the general version until a second case, with the
  limit that waiting must not lose an alternative. `SKILL.md` goes further toward building up front
  when the change is predictable from the purpose, so treat waiting as the choice when the prediction
  is weak.
- **Start from a simple system that works** (Gall 1975): a general design built whole tends not to work.
- **Structure copies communication, and premature modularization hurts** (Conway 1968; Colfer and
  Baldwin 2016): for teams and courses, the right amount of fixed structure follows the rate of change
  (Burns and Stalker 1961), and fixed rhythm with cheap probes helps (Brown and Eisenhardt 1997).

## Where the evidence is thin

- Joshua's design boards record ideas and open questions, not decisions, and the Project Documentation
  board is a template with little filled in (its value is the method, which `../principles.md` "How to think and document" follows). Treat them as design intent; his built code
  and notebooks are the built evidence, and the notebooks hold unfinished cells and bugs.
- The manual and AI code comparison is a tendency to learn from, not a controlled study: its median
  file sizes (8 to 40 lines manual, 138 to 258 AI) come from a script over codebases of very different
  scale and purpose, and a recount of two of them agreed in direction with small differences.
- QAR was built by AI to Joshua's design, so its failures are implementation gaps against the
  principles, not his choices.

**Related AI and agentic frameworks (2026-10-17).** `sources/agentic_frameworks.md` compares ESOI with layered agent
models, spec-driven development, DSPy-style optimizers, eval harnesses, evolutionary agent systems, routing and oversight
frameworks. None found covers all five record types with an evolving structure; the most borrowable ideas are an archive
of losing alternatives, Pareto selection when ideals conflict, a named metric lifecycle (capability to regression,
retire when saturated), recording what a metric cannot measure, and routing as a selection mode.
