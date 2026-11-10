# Evolvable structure: each solution gets its own consideration

Part of `../principles.md`. Pattern 16: every relevant solution, and each level of the hierarchy, is judged on its own against its own records, and depth (sub-prompts, sub-agents) is how a solution reaches its completion quality. Quotes are verbatim.

## Pattern 16

**Pattern 16, in Joshua's words (2026-11-08):** "An ESOI solution represents an area that deserves its own depth of focus and
domain expertise. Even where there is hierarchy, each level of the hierarchy is a different scope of depth with its own value,
such as the structure of the combination of its children. The key then is to ensure that each relevant solution receives its own
consideration. In the case of AI intelligence, a separate intelligence and prompt for each. The structure helps provide memory and
expertise that is durable and not skipped over."
How to apply it: when work touches several solutions (triaging candidates, reviewing a change, choosing arms), split it into one
pass per relevant solution. Give each pass that solution's records first (its definition, metric, recorded results in
`results.csv`, findings and history), plus one pass for the parent level judging how the children combine. The prompt for each
pass is formed automatically from the solution's network of connected records, its Knowledge field included, never hand-written
per solution ("the network of what solution connects to should automatically form the prompt including knowledge", Joshua,
2026-11-08). Do not use one broad
pass that rates everything from general knowledge. Why: on 2026-11-08 a single agent triaging 23 outside repos across the whole hub
rated Graphify 0.85 and called it the strongest candidate. Its own solution's records already held a measured result: on
2026-11-04, Graphify's arm placed 3 of 63 cases in the top three (balanced 0.32), against 40 of 63 (0.74) for the arm that won. A
pass scoped to Cards From Files, reading its own results first, could not have missed that.
In the ESOI library this is `esoi consider "<text>"` (one generated prompt per relevant solution and per parent level, as JSON) and
`esoi spec prompt SOLUTION` (one solution's prompt); knowledge items are rows of `knowledge.csv`, offered beside the prompt for the
situation to choose from (docs/how-to/give-each-solution-its-own-consideration.md in the ESOI repository).
Depth is also how completion quality is reached. When a piece of work falls short of its own solution's metric (a deliverable that
is a thin stub), the answer is more depth, not a bigger model first: the work is split into the sub-solutions it needs (research,
outline, each section, review against the rubric), each handled by its own sub-prompt or sub-agent with its own consideration, and
recombined and checked against the parent metric, repeating within the request's budget. A stronger tier is a measured option inside
that structure, not a replacement for it. (Joshua, 2026-11-08, on a milestone script that came back as a four-line stub: "the type of
thing solution depth is supposed to handle, esoi ensures task completion quality, and subprompts/agents are used as needed to build
out depth".)
Work quality rests on three parts, each with its own metric: (1) classifying the work to its solution, creating the solution where
none fits; (2) an agent applying ESOI on that solution (its records, metric, milestones and depth); (3) the harness that carries out
the work, chosen by its own metric. When work comes back poor, find which of the three failed and fix that part generically, rather
than patching the output of one flow. (Joshua, 2026-11-08: "for ensuring work is high quality, it comes down to 3 things IMO:
solution classification and creation where needed, 2. agent carrying out ESOI skill on the solution, 3. the AI harness used for
carrying out work. if those three things are handled well it should be fine".)
