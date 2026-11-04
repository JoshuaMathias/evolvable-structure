"""The staleness decision, one function: ``decide(kind, args) -> {"stale": bool, "why": str}``.

Given a step of the fixture repository (a commit, an uncommitted edit, a rename, a doc or case change) and a component whose
result was recorded at the first commit, say whether that recorded result still counts. The cases name the step and the
component and say, written by hand from what each component's code reads, whether the result is stale. Judged on false-stale
(a result re-run although nothing it measures changed) and false-fresh (a result kept although what it measures changed: a hard
fail that disqualifies the arm). ``build(meter)`` in ``impls/`` returns the function. No model is called.
"""
