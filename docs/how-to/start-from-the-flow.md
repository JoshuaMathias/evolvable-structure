# Start from the flow, then implement what it reaches

Write the **flow** first, then what the flow reaches. This is Joshua's general guidance, and it is not only for code: it applies to
anything ESOI structures (specifications, processes, documents, business offerings, how an AI behaves). Code is one case. In his
words: "always start implementation from top to bottom and code for the conceptual flow which the intent solution coherence paragraph
describes, using the entry points for each solution, unless told otherwise; after the flow is implemented, implement the code for
what the flow calls; in other words function definitions and calls of solution functions first (interfaces), then implementations,
at all points of the hierarchy for everything within scope of the current task (which can be the whole repository); interfaces and
flow can be updated as needed based on learnings from implementation."

## The order

1. **Read the paragraph.** The intent's solution coherence paragraph says, in names, how its solutions fit together ("The Mind asks
   Science for evidence ..."). That is the flow.
2. **Write the flow, in the medium the implementation will be.** In code, entry-point calls from each solution to the ones it uses.
   In a process, the steps and handoffs. In a document, sections that refer to each other. In an organisation, roles and
   delegations. Define each solution's **interface** (what it takes and returns, and who is responsible) even where no
   implementation exists yet. The flow runs end to end, with stubs, placeholders or a named owner behind each part if need be.
3. **Then implement what the flow reaches, one level down at a time**, at every point of the hierarchy in scope for the task (a
   sub-intent's flow is the implementation of its parent's solution). An implementation may be code, a document, a registry, a
   process or a person. The scope may be one solution or the whole repository.
4. **Revise as you learn.** Implementing a level shows what an interface should take or return and whether the flow was right, so
   change the interfaces and the flow to match, and keep the paragraph and the records true to them.

Unless the person asking says otherwise, this is the order. It keeps the intent, not the available parts, in charge of the shape.

## What esoi checks

Rule S50 (opt-in, `[rules.S50] enabled = true`, advisory) informs where the flow is not written yet in **code**, from the evidence of
[`esoi.coherence`](../explanation/why-prose-is-not-code-evidence.md) (E1 to E5): a solution that has an implementation but no caller in
the flow (nothing in the code of any solution the records say uses it imports, types or names it), and stated edges that no call in
the code shows while the used solution has another caller. Each finding names the next step: write the flow, then what it reaches.
Only code is read; for documents, processes and organisations the same order is yours to keep, and the paragraph and the records are
where a reviewer checks it. It never fails a check; waive it as the solution id (or `intent:solution` for one edge).

See also [declare a solution's interface](declare-a-solutions-interface.md), [assemble the parts by name](assemble-by-name.md),
[scope the role of a solution](scope-the-role-of-a-solution.md) and [names and ids](../reference/names-and-ids.md) (the paragraph is
written in display names).
