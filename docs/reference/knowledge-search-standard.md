# Knowledge search standard

Every knowledge search is done as a small systematic review, sized to the decision it informs, and every other piece of research
(a trial, an observation, an interview) follows the same standard with its own method. This page is the one research standard:
research finds new evidence (primary) or gathers existing evidence (secondary, a review), and one record shape holds both. A knowledge
search is any look outside the repository for what is known: public evidence for a metric, alternatives for a solution, a registry
refresh, a licence or adoption check, a vendor documentation lookup that informs a decision, prior art before writing an
implementation. The standard says what a piece of research is, what its record holds and when each size applies. It extends and does
not replace [knowledge records](knowledge-records.md) (what a solution rests on) and [use public evidence](../how-to/use-public-evidence.md)
(the grading of benchmark numbers). How to do one: [search like a small review](../how-to/search-like-a-small-review.md). Where research
sits in the effort of an intent: [experiments in ESOI](experiments-in-esoi.md). Standard dated 2026-11-10.

## Why

A search with no question, no stopping rule and no record finds what is easy to find, keeps what agrees with the searcher and cannot
be checked or refreshed. Review practice in medicine and in software engineering solved this: fix the question and the method before
the work, say where and how you looked, count what you screened out and why, grade what you kept, and state what remains unknown. ESOI
adds one part those practices leave to the authors: what the research changed (the applied part).

## The role is loose on purpose

A piece of research minimally is: a **question**, a **method** fixed beforehand, what was **observed or found**, what it **means**, what
it **changed**, and **when to revisit** it. Everything else on this page is optional unless a kind asks for it, and the method may be
quantitative or qualitative. A metric and a pass or reject value are required only when the question compares alternatives on a
metric. A qualitative piece states instead what will be observed, how, by whom, and what would count as changing one's mind. Never
force a number onto a qualitative question, and do not read this page as a reason to exclude a legitimate way of inquiring.

## The concepts

| Part | What it is | Drawn from |
|---|---|---|
| Question and decision | The question and the decision its answer informs. For a choice between options, the question has four slots (below) | PICO (Richardson et al., 1995) adapted |
| Home and links | The question belongs to an intent (or sub-intent). It links, optionally and many to many, to what it bears on: solutions, problems, ideals, metrics, implementations, or none yet when it is about how to think about the intent itself | ESOI |
| Method (protocol) | How it will be done, by whom, written and dated before the work; a change after is recorded with its date | PRISMA-P (Moher et al., 2015), Kitchenham and Charters (2007) |
| Criteria (review) | What is included and excluded, fixed before searching: kind of source, date range, licence, maintenance, fit to constraints | PRISMA 2020 items on eligibility |
| Sources and queries (review) | Each source searched and each exact query with its date and hit count | PRISMA-S (Rethlefsen et al., 2021) |
| Screening (review) | Hits found, screened out with a reason and a count each, kept. The counts add up | PRISMA 2020 flow |
| Observation (trial, observation, interview) | What will be observed and how; what would change one's mind; for a comparison, the metric, stage, expected value and rejecting value, fixed before it runs | ESOI |
| Extraction | Per kept item: the claim or observation, its source, date, independence, how it was verified, licence where code is concerned | Kitchenham and Charters (2007) |
| Grade | A to D per item by the rule [esoi evidence](../how-to/use-public-evidence.md#the-grade-in-short) applies: one source is B at most, no independent source is C at most, a vendor or maintainer alone is D, A needs two independent sources that agree. Required for a review, optional for primary research | GRADE (Guyatt et al., 2008), kept to the repository's own scale |
| Synthesis | What is known, what is contested, what is unknown: what it means | PRISMA 2020 |
| Limitations | What was not opened, not verified, not searched, not observed | PRISMA 2020 |
| Decision per candidate (review) | `adopt`, `adapt`, `build-on`, `reject`, `defer` or `no-candidate`, each with a reason. A candidate found and neither adopted nor given a reason is a gap, not research done ("adopt before writing") | ESOI principle 8 |
| Applied | For each item: what it changed, as `kind:record id` (a knowledge row, an implementation, a metric stage or prior, a selection, a waiver, a decision, a milestone, a document, a problem, an ideal), or `not-applied` with the reason. A decision about an alternative is one application, not the definition. Every record created or changed because of research points back to it | ESOI |
| Revisit | The date it is redone or retired | Cochrane living and rapid review practice |

### The question for a choice, in four slots

PICO asks about a patient, an intervention, a comparison and an outcome. For an engineering choice the slots are: the **need** (what
the solution must do, under which constraints), the **candidates** (the options, including the repository's own and the strongest
existing one), the **comparator** (the incumbent or baseline each candidate must beat) and the **outcome** (the criteria the
decision rests on: fit, cost, licence, maintenance, measured quality). Write it as one sentence, then name the decision: "adopt,
adapt or build". Questions that are not choices (how to see the intent, what a person does) need no slots.

## Kinds

The kind names the activity. All share one record shape.

| Kind | Finds | Needs beyond the minimum |
|---|---|---|
| `review` | existing evidence | decision, criteria, sources, queries, counts, decision per candidate |
| `trial` | new evidence by trying something | what will be observed, what would change one's mind (a comparison names metric, stage, expected and rejecting value) |
| `observation` | new evidence by noticing | what will be observed |
| `interview` | new evidence from a person | nothing more |
| `other` | anything else | nothing more |

An activity names the [experiment](experiments-in-esoi.md) it happens inside (`experiment_id`, a row of `experiments.csv`) when it has one; a review done for a one-off decision needs none.

## Three sizes

The size follows the weight of the decision: how reversible it is, how many solutions it reaches, what it costs or promises
outward. When two sizes fit, take the larger. Research may move up when it finds a contradiction or a blocker, never down for convenience.

| Size | Use when | Time | Minimum |
|---|---|---|---|
| Quick check | The decision is reversible within a day, touches one implementation or one file, and has no outward, money or licence consequence | minutes | One source kind, up to three queries (or one observation), no synthesis beyond a sentence |
| Standard | The decision selects or changes a solution's implementation, a metric, a public-stage prior or a registry area, or other solutions depend on it | up to an hour of AI work | Two source kinds (or two observations), at least five queries for a review, every part above, synthesis in three parts |
| Full | The decision is hard to reverse, adds a dependency others rely on, carries licence, privacy or safety risk, makes a public claim, or creates a solution | hours | Standard, plus the method reviewed by a second reader before the work, three source kinds, a second screening pass over a sample of the excluded, and a note on what would change the decision |

Nothing here is a reason to do more. Before searching, look in `research.csv` for a current review of the same question and reuse it; a
review not past its revisit date is the answer.

### The minimum record, smallest size

A quick check is one `research.csv` row and one `research_items.csv` row per kept item. The row holds: the kind, the intent, the question,
the size, the date the method was fixed, the method in one line, the date done, the limitations (one phrase) and the revisit date; a
review adds its decision, criteria, sources, queries, counts (found, screened out with reasons, kept) and the decision per candidate with
its reason. Each kept item holds its claim, source, source date, and what it changed. The synthesis fields may be empty.

## The record format

Two CSV files in the records folder beside `knowledge.csv`, one record type kept as two tables (as a problem and its links are):

`research.csv`, one row per piece of research: `research_id`, `kind`, `intent_id`, `experiment_id`, `links` (`kind:id` entries,
`;` separated, kind one of solution, problem, ideal, metric, implementation, intent, knowledge; empty when the question is about
the intent itself), `question`, `decision`, `size`, `protocol_date`, `method`, `criteria`, `sources`, `queries` (`source | query | date | hits`),
`found`, `screened_out` (`count reason`), `kept`, `observe`, `change_my_mind`, `stop`, `done_on`, `synthesis_known`, `synthesis_contested`,
`synthesis_unknown`, `limitations`, `decisions` (`candidate: verb: reason`), `refresh_on`, `status` (`open` or `superseded`). Lists are `;` separated.

`research_items.csv`, one row per kept item: `research_id`, `item_id`, `claim`, `source`, `source_date`, `independent` (`yes`, `no`, `unknown`),
`verified` (`opened`, `cross-checked`, `snippet`, `not-opened`, `observed`), `licence` (`n/a` when not code), `grade` (A to D), `knowledge_id`, `applied`.

Knowledge it produces is a `knowledge.csv` row whose new optional column `research_id` names it. Numeric benchmark results go in
`evidence.csv` as before. No template field changes: the files and the column hold ids, dates, counts, links and the record's own text,
and a solution's `knowledge` cell is untouched. Whether research records stay beside knowledge as these files, or become a record
kind of the template, or live inside the Knowledge field of an intent or solution, remains the owner's to choose; experiments, which
frame research, are records of their own ([experiments in ESOI](experiments-in-esoi.md)). Python: `esoi.understanding.solution_consideration.research`.

### What `esoi check` says about it

Advice only; nothing here fails a check. It lists a record missing a part its kind and size require, counts that do not add up, a method
dated after the work, a link of an unknown kind, an item without a grade where a review needs one, a decision without a verb or a reason,
research past its revisit date, an item neither applied nor marked `not-applied` after its size's grace period (quick 7 days, standard 14,
full 30), an activity naming an experiment that has no row in `experiments.csv`, and a knowledge row recorded on or after the standard's date that cites
an address but names no research. A generated page lists, under an intent's records, each piece of research linked to a solution
and what each item changed.

## Worked example: this standard's own search

The review that produced this page is recorded in `research.csv` and `research_items.csv` beside `knowledge.csv` in the Solution
Consideration records (id `r-research-standard`), inside the experiment `x-research-standard` in `experiments.csv` (focus: how every
knowledge search and every experiment's research is done and recorded; period 2026-11-10 to 2026-12-10).

- **Question.** Which established review practices (reporting, protocol, question framing, evidence grading, rapid and software
  engineering adaptations) can ESOI adopt for every knowledge search, and where does it need its own part? Decision: adopt, adapt or
  build the standard. Size: standard.
- **Method (fixed 2026-11-10, before searching).** Include: the current canonical statement or guideline of a review practice, with a
  citable identifier. Exclude: teaching handouts and glossaries as the source of a claim (they may locate the canonical one).
- **Queries (2026-11-10).** Eight web searches: PRISMA 2020; Cochrane Handbook and rapid reviews; Kitchenham and Charters protocol; GRADE and
  PRISMA-S; PRISMA-S; PICO; PRISMA-P and PROSPERO; grey literature and multivocal reviews in software engineering.
- **Screening.** About 80 hits (links returned). Screened out 72: 62 mirrors or repository copies of a kept source, 6 teaching
  handouts, 4 translated or unrelated pages. Kept 8.
- **Kept, with grades.** PRISMA 2020 (Page et al., BMJ 2021, B); PRISMA-S (Rethlefsen et al., Systematic Reviews 2021, B); PRISMA-P
  (Moher et al., Systematic Reviews 2015, B); Cochrane Handbook v6.5 (2024) and the Cochrane rapid review guidance (updated in BMJ,
  2024) (B); Kitchenham and Charters, EBSE-2007-01 (2007, B); Garousi, Felderer and Mantyla on grey literature (Information and
  Software Technology, 2019, B); GRADE (Guyatt et al., BMJ 2008, B); PICO (Richardson et al., ACP Journal Club 1995, C: reached only
  through secondary descriptions).
- **Synthesis.** Known: a protocol before searching, counted screening, a reporting checklist for the search and a certainty grade per
  finding are settled practice in medicine, carried into software engineering by Kitchenham and Charters and by Garousi and
  colleagues. Contested: how little a rapid review may omit before it misleads (Cochrane's rapid guidance gives 24 recommendations
  and no single threshold), and whether PICO fits exploratory questions. Unknown: how well an AI-run review matches a human one;
  no source found measures it.
- **Limitations.** Every item was read through search-result summaries, not opened in full (verified `snippet`); author lists
  were not checked; no paper index was searched, only the web.
- **Decisions.** Adopt Kitchenham and Charters' protocol-first plan; adapt PRISMA 2020 (screening counts, limitations), PRISMA-S
  (queries with dates), PRISMA-P (method fixed before the work), PICO (four engineering slots), the Cochrane rapid guidance (three
  sizes) and Garousi's grey-literature quality assessment (vendor documentation as a source of the lowest grade); build on GRADE
  with the repository's own A to D rule rather than its four certainty levels.
- **Applied.** The sizes, the record format and the grade rule in this page (a document).
- **Revisit.** 2027-11-10.

## Proposal: every session holds research questions

A proposal for the owner's review. Nothing in it is enforced and nothing in the checks reads it.

The owner's idea: "What if every user input is actually a research question", corrected to: "more like each session, than each input, different
inputs in a session could be clarifying the same research question, and also one input could have more than one research question" (2026-11-10).
So the unit is the **research question**, held at the level of a **session** (a conversation, a task thread, a working session), not the single input.

**Placing each input.** A session carries one or more research questions. They are not one to one with inputs: several inputs may clarify,
narrow, correct or extend the same question, and one input may raise more than one. The first job of an AI for each input, in these terms, is to place it:
does it refine a question the session already holds (then that question's statement is updated and the earlier work is kept and built on, not restarted),
raise a new question, ask for something to be applied, or several of these at once. Small talk (a greeting, thanks, an acknowledgement) holds no
question and is exempt.

**The record is kept per question, not per input.** The smallest size applied to a question holds: the question as currently understood, with how it
changed over the session (each refinement tied to the input that caused it); the method actually carried out (the plan, as done); the sources (what was
retrieved, searched or read); the findings, each with its confidence (how it was verified) and its limits; and the applied part (what was done and what it
changed, or nothing and why). A request to do something is the applied part of a question, or a question of its own when what to do is unknown. A reply to one
input may advance several question records. It costs nothing extra and stays out of sight unless opened: it is the trace the system already keeps, read as a
record, and nothing is shown to the person for it.

**The check it gives.** A question is answered when its current statement is answered by a method actually carried out, not when the latest input got a reply.
An answer whose stated method was not carried out is not an answer: the completion judge can test exactly this, by comparing the method the answer claims with
the steps the trace shows.

**The link to experiments.** A session's questions that fall inside a running [experiment](experiments-in-esoi.md)'s scope attach to it (`experiment_id`), and
their findings and applied parts count for its reevaluation. A question outside every running experiment is outside current focus: it is still answered, and it
neither reopens what an experiment holds fixed nor counts as exploration.

### Worked example: where an assembling repository's flow already holds it

The example is a repository that assembles AI components by metric, whose top-level flow answers a request by asking for the person's authority and
preferences, where the data lives, passing the request to an intelligence part that draws tools, models and outside knowledge from a world part, stating what that
part is for, keeping the run record and auditing it against what was done. Mapped on the record:

| Part of the record | What the flow has today | Missing |
|---|---|---|
| Place the input | A request classifier reads what the plan asks of the system (to tell something, to change something, to write a text, or not yet understood) and passes nothing on when it needs clarifying; a reference resolver ties a phrase to the one candidate it names or abstains | It places one request at a time; there is no step that compares an input with the questions the session already holds (refine, new, apply) |
| The question as currently understood | The request text, and each plan piece's sub-goal as a target with a budget | No statement of the question that is revised and kept; the next input starts from the next request |
| How it changed | None; each request is its own run | A revision history tying each change to the input that caused it |
| The method | A planner breaks the request into pieces, each with a sub-goal; a delegation step hands each piece to the worker its category names | The plan is not stored as a method the answer can be tested against |
| The sources | Workers return items with addresses and titles; the run record lists the sources | Not tied to the question each served |
| Findings, confidence, limits | Results with their items; a done-standard per piece; a response-quality judgment against a profile | No confidence or limits per finding as a field |
| Applied | The run record holds the answer, the attempts and why it stopped; a request to change something is delegated to a worker | What it changed is not recorded as such |
| The completion check | A goal-completion step holds the result to its target and decides when to stop; an integrity audit compares what the system says it did against the run record | It tests the latest request's target, not a question's current statement over the session |
| Where a session's questions would be held today | The conversation (the front end's input history is a list of typed lines, not questions); the run record kept for each request in the data part; the working memory of one delegated agent session, which lasts one run; the long-term memory and objectives of the long-view part | None holds a session-level list of questions |

What is already there is most of the record per request: the plan, the sources, the results, the done-standard, the answer and the trace. What is missing is the unit
above it: a session's question list, the placement of each input against it, the revision history, and a completion check run on a question rather than on a request.
No code is changed for this in the example in this pass.

## Sources

Looked up 2026-11-10 through web search summaries (see the limitations above): Page et al., "The PRISMA 2020 statement", BMJ 2021;372:n71;
Rethlefsen et al., "PRISMA-S", Systematic Reviews 2021;10:39; Moher et al., "PRISMA-P", Systematic Reviews 2015;4:1; Cochrane Handbook
for Systematic Reviews of Interventions, version 6.5 (2024), and the Cochrane Rapid Reviews Methods Group guidance (BMJ, 2024 update);
Kitchenham and Charters, "Guidelines for performing systematic literature reviews in software engineering", EBSE-2007-01, 2007;
Garousi, Felderer and Mantyla, Information and Software Technology 106 (2019) 101-121; Guyatt et al., BMJ 2008;336:995-8;
Richardson et al., ACP Journal Club 1995;123:A12-3.
