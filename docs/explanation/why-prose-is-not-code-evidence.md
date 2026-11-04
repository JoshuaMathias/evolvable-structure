# Why prose is not evidence that code uses a solution

The coherence check holds the paragraph to the code: "the paragraph matches how solutions relate in the code". Evidence must
therefore come from what the code does. A docstring or comment that names another solution says what a person wrote, not what
runs, and writing one is the cheapest way to raise a precision score without changing anything. So the check reads the syntax
tree and counts a mention only in executable code (an identifier, attribute, import, annotation, or a string used as a value).
Prose strings, docstrings and comments are left out. A relation that is real shows up in the code when it is wired through an
import, a typed need or a resolve call; a relation that only appears in prose is either missing wiring or not a relation, and the
records should say which. See [Declare a solution's interface](../how-to/declare-a-solutions-interface.md).
