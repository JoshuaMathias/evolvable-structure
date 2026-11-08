"""The solution-consideration function. Every implementation is ONE function with this signature:

    prompt(kind: str, args: dict) -> {"text": str, "chars": int}

Given a solution id, return the text a pass of AI reads to give that solution its own consideration. The free stage asks whether
the deciding records reach the pass: a recorded result that lost, a finding queued against the solution, its parent, its children's
coherence and its dependencies, within a size budget, closest records first. The cases drive the LIVE assembly over two
repositories: a synthetic one shaped like the case that motivated it (an outside tool rated strongest by reputation whose arm had
already lost 3 of 63 against 43 of 63, a fact held only in the results log and a finding), and this repository's own records.

Kinds: ``prompt`` with args ``{solution, repo ("fixture" or "live"), budget, task}``. An implementation module in ``impls/`` exposes
``build(meter) -> prompt``. No implementation here calls a model: whether a pass given the prompt reaches the right verdict, where a
pass without it does not, is the paid stage (``real=yes``), run only with an approved budget.
"""
