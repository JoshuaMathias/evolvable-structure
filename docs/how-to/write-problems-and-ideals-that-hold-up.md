# Write problems and ideals that hold up

A problem must be true today. An ideal must be the state you want, not a way of getting there. Why:
[A problem says what is true; an ideal says the state you want](../explanation/a-problem-says-what-is-true.md).

## Write or review a problem

1. **Say what is missing, exactly.** Name the gap, not a category. "No shared way to judge what one part adds to the whole", not
   "no testing".
2. **Say who has it.** A kind of person or system, as narrow as is true: "people assembling open-source parts", not "everyone".
3. **Say how often or how much, if you know.** Usually, on most changes, within weeks, about a fifth of requests. If you do not know,
   leave the frequency out rather than invent one.
4. **Say what it costs.** Time, money, a wrong default shipped, a person's trust.
5. **Read every absolute aloud.** Never, nobody, no one, always, everyone, none, nothing, impossible, the only way. For each ask: is
   this literally true? Would someone who works in this field agree? If not, replace it with what is true (rarely, few teams, by hand,
   not in one shared place).
6. **Check the existing attempts honestly.** Name what people already do and where it falls short. If it works well for some people,
   say so: the problem is then narrower than you thought.
7. **Keep it plain.** Short sentences, everyday words, no jargon a reader has to unpack. Nuance comes from precise words, not from
   longer sentences.

## Write or review an ideal

1. **Describe the state, from the point of view of whoever is affected.** What is true for the person or the system when things are
   right? "Anyone deciding sees which option is best and by how much."
2. **Absolutes are welcome.** An ideal is the limit case. "Every part earns its place in the whole" gives the direction; the metric
   measures the distance.
3. **Remove the means.** If the ideal names a tool, a component, a mechanism, a method or a role ("use", "build", "one intake",
   "by configuration", "is chosen by"), it is a solution. Move that into a solution record and write the state it is for.
4. **Test it with two solutions.** Could two quite different solutions both reach this ideal? If only one could, it is still a
   solution in disguise.

## Before and after

| Record | Before | After |
|---|---|---|
| Problem | Parts that are best alone can fail when assembled, and nobody tests the whole. | Each part is usually tuned on its own, so a part can be kept for how well it does alone even when the whole gains little from it. Wholes are tested, but people assembling open-source parts have no shared, measured way to judge what each part adds to the whole. |
| Ideal | Use one router for every model call. | Every request reaches a model that is up and within its budget. |
| Ideal (fine as is) | Every claim in a reply is backed by a source. | (no change: absolute, clear, and a state) |

## Let the check point at them

`esoi check --findings` lists two advisory rules, which inform and never fail:

- `S51 <problem_id>`: an absolute in a problem. Rewrite it, or if it is literally true, add a row to `waivers.csv`: rule `S51`, path
  `<problem_id>:<field>`, and the reason it is true.
- `S52 <ideal_id>`: an ideal that reads like a solution. Rewrite it as the state, or waive it as `<ideal_id>:<field>` with a reason.

Both are prompts for a person or an AI to read the sentence, not verdicts: a word list cannot tell a true absolute from a false one.
