# A problem says what is true; an ideal says the state you want

Joshua's lesson, after reading a problem that said "Parts that are best alone can fail when assembled, and nobody tests the whole":
"this isn't correct, it's that the parts need to be justified as part of the whole but just independently optimized, and it's not
correct that the whole is never tested, what developer would say that." Problems must not say false things to make an easy statement.
They should use nuanced yet clear and simple language.

And on ideals: "absolutes are more expected in ideals than in problems, that's kind of what ideals are", and "ideals should avoid being
solutions, that's the easiest trap; solutions are strategic approaches or roles in a system, ideals are the state we want."

## A problem describes today, so it must be accurate

A problem is a description of how things are now: what is missing, who it is missing for, and why that matters. A reader who knows the
field checks it against what they have seen. When it says "nobody tests the whole" or "it is never measured", they know of a team that
does, so they stop trusting the record and everything built on it. The overstatement usually exists to make the solution look necessary.
That is a strawman. It also hides the real gap, which is the thing a solution has to close.

The true version is usually more useful, because it names what is actually missing:

| Overstated | True, and still simple |
|---|---|
| Parts that are best alone can fail when assembled, and nobody tests the whole. | Each part is usually tuned on its own, so a part can be kept for how well it does alone even when the whole gains little from it or pays more for it. Wholes are tested, but people assembling open-source parts have no shared, measured way to judge what each part adds to the whole. |
| The best tool is never used. | Teams often keep the tool they started with, because comparing a new one on their own cases takes days they rarely have. |
| Nothing checks the records against the code. | Records are checked by hand, if at all, so they drift from the code within weeks of a busy change. |

A problem that holds up says, in plain words:

- **What is missing**, exactly (not "no testing" but "no shared way to judge one part's contribution to the whole").
- **For whom** (people assembling open-source parts, not "everyone").
- **How often or how much**, when known (usually, within weeks, on most changes), and nothing invented when it is not known.
- **At what cost** (time lost, money spent, a wrong default shipped).

Absolutes are allowed when they are literally true: "the simulated arm spends nothing" is a fact. The question is never "does it
contain the word never" but "would a domain expert call this sentence accurate".

## An ideal describes the state you want, so absolutes are the point

An ideal is the limit state a solution aims at: what is true for the people or the system when things are right. "Every part earns its
place in the whole" is a good ideal precisely because it is absolute. Nobody expects it to be true today. The absolute gives the
direction and the measure of distance.

The trap for an ideal is a different one. It is written as a solution: a mechanism, a tool, a component or a role. A solution is a
strategic approach or a role in a system; an ideal is the state you want, from the point of view of whoever is affected.

| Written as a solution | Written as the state |
|---|---|
| Use one router for every model call. | Every request reaches a model that is up and within its budget. |
| Build a dashboard of every metric. | Anyone deciding can see, at a glance, which option is best and by how much. |
| Have a review step before publishing. | What goes out says only what the evidence supports. |

Ask of each ideal: could two different solutions both reach it? If only one mechanism could, it is a solution in disguise. Move the
mechanism into a solution and write the state it is for.

## Why both rules serve the structure

Problems and ideals are what solutions are judged against. A false problem sends effort to a gap that does not exist and leaves the real
one open. A solution-shaped ideal fixes the means before any alternative is measured, so the metric can only confirm the first idea.
Both make the structure less evolvable, which is the opposite of what the records are for.

## What the tools do

Two advisory rules inform and never fail the check:

- **S51** reads a problem's text (name, problem, who has it, why it matters, why it is hard, existing attempts) and points at sweeping
  absolutes (never, nobody, no one, always, everyone, none, nothing, impossible, the only way, every time), asking whether each is
  literally true. Ideals are not read. A true absolute is waived as `problem_id:field` with the reason.
- **S52** reads an ideal's name, principle and state description and points at text that opens with an instruction to build or use
  something, or that names the means: a method ("by comparing", "is chosen"), one component ("one intake", "one engine") or a
  mechanism ("configuration", "adapters"), asking what state it wants instead. Its phrases were written from 30 solution-shaped ideals
  found by reading three repositories' records; on those same 135 ideals it finds 24 of the 30 and points at 6 others, so it finds
  candidates and a person decides.

How to write and rewrite them: [Write problems and ideals that hold up](../how-to/write-problems-and-ideals-that-hold-up.md).
