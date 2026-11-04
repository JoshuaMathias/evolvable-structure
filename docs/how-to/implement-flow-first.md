# Implement the flow first, then what it calls

Start from the top and code the conceptual flow the intent's **solution coherence paragraph** describes, then the code that flow
calls. This is Joshua's general guidance for any piece of work, in his words: "always start implementation from top to bottom and
code for the conceptual flow which the intent solution coherence paragraph describes, using the entry points for each solution,
unless told otherwise; after the flow is implemented, implement the code for what the flow calls; in other words function
definitions and calls of solution functions first (interfaces), then implementations, at all points of the hierarchy for everything
within scope of the current task (which can be the whole repository); interfaces and flow can be updated as needed based on
learnings from implementation."

## The order

1. **Read the paragraph.** It says, in names, how the intent's solutions fit together ("The Mind asks Science for evidence ...").
   That is the flow to code.
2. **Write the flow.** For each solution the flow uses, the function definition of its entry point (the interface, declared with
   `@solution(<id>, entry=...)`) and the calls that carry the flow from one solution to the next. Let a solution that uses another
   take it as a typed need (`def __init__(self, science: Science)`) or call its entry point. The flow runs end to end, with stubs
   behind it if need be.
3. **Then the implementations.** Write what each call reaches, one level down, then the level below that, at every point of the
   hierarchy that is in scope for the task (a sub-intent's flow is the implementation of its parent's solution). The scope may be
   one solution or the whole repository.
4. **Revise as you learn.** The interfaces and the flow are not frozen: implementing the lower level shows what a call should take or
   return, so change the interface and the flow to match, and keep the paragraph and the records true to them.

Unless the person asking says otherwise, this is the order. It keeps the intent, not the available parts, in charge of the shape.

## What esoi checks

Rule S47 (opt-in, `[rules.S47] enabled = true`, advisory) informs where the flow is not coded yet, from the evidence of
[`esoi.coherence`](../explanation/why-prose-is-not-code-evidence.md) (E1 to E5): a solution that has an implementation but no caller
in the flow (nothing in the code of any solution the records say uses it imports, types or names it), and stated edges that no call
in the code shows while the used solution has another caller. Each finding names the next step: write the flow, then what it calls.
It never fails a check; waive it as the solution id (or `intent:solution` for one edge).

See also [declare a solution's interface](declare-a-solutions-interface.md), [assemble the parts by name](assemble-by-name.md) and
[names and ids](../reference/names-and-ids.md) (the paragraph is written in display names).
