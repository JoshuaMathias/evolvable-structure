"""The public-evidence function. Every implementation is ONE function with this signature:

    run(kind: str, args: dict) -> dict

The cases give evidence rows (the columns of ``esoi.evidence.COLUMNS``, with the sensible ones defaulted by the runner) and a
fixed ``today``, so a result never depends on the clock. Deterministic and offline: no model is called.

Kinds and the dict an implementation returns:
  grade  args {rows, today}        -> {"grades": {"candidate/dimension": letter}, "flags": {"candidate/dimension": [flag]},
                                       "needs_own_run": {"candidate/dimension": bool}}
  rank   args {rows, today, dims}  -> {"order": {dimension: [candidate best first]}}
An implementation module in ``impls/`` exposes ``build(meter) -> run``.
"""
