"""The structure-quality function. Every implementation is ONE function with this signature:

    assess(kind: str, args: dict) -> dict

``kind`` is ``assess`` and ``args`` are ``{shape, stage}``: the name of a small project in ``structure_fixture`` (generic shapes of structural incidents
and clean exemplars, each case tagged with its source) and the stage (1 static code and records, 2 also co-change from git history). The implementation
returns ``{"score": the one number or None, "verdict": "at_reference"|"below_reference"|"unmeasured", "flagged": [the dimensions that have offenders]}``. The cases
score it by what it says (a clean exemplar is at the reference and flags nothing; an incident flags the dimension it damages) and by comparison (the balanced
real structure must score above the same project cut into tiny files, the bound a size-only scorer fails). Deterministic and offline; the arm that
asks an expert model declares ``PAID = True`` and is never run without approval. ``build(meter)`` in ``impls/`` returns the function.
"""
