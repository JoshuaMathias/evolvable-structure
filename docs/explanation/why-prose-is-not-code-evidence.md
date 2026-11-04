# Why prose is not evidence that code uses a solution

The coherence check holds the paragraph to the code: "the paragraph matches how solutions relate in the code". Evidence must
therefore come from what the code does. A docstring or comment that names another solution says what a person wrote, not what
runs, and writing one is the cheapest way to raise a precision score without changing anything. So the check reads the syntax
tree and counts a mention only in executable code (an identifier, attribute, import, annotation, or a string used as a value).
Prose strings, docstrings and comments are left out. A relation that is real shows up in the code when it is wired through an
import, a typed need or a resolve call; a relation that only appears in prose is either missing wiring or not a relation, and the
records should say which. See [Declare a solution's interface](../how-to/declare-a-solutions-interface.md).

Lift is held to the same honesty. It compares how often the evidence fires on recorded edges with how often it fires on pairs
that are not edges, so it is only defined for an intent that records edges. A grouping of independent solutions has none; the
check reports "n/a (no recorded edges)" instead of inventing a number or failing a limit that has nothing to measure. An intent
that does record edges is never excused: a lift of 0.0 still fails `min_lift`. A limit that suits one intent is written in that
intent's own `[rules.S38.floors.<intent-id>]` table, so it is visible, reviewed by S39, and does not loosen every intent.
