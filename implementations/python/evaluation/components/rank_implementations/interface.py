"""The ranking function. Every implementation is ONE function with this signature:

    rank(kind: str, args: dict) -> dict

A repository decides which implementation to run by recorded numbers, so the ranking has to be right: the winner is
the higher pass rate (equal rate: lower spend), scores on different case files are never compared, a row with no
provenance is flagged, a tie is not a win, and an ablation or validity arm is no rival. The cases drive the LIVE
``esoi.leaderboard`` over synthetic results tables. Deterministic and offline.

Kinds and the dict an implementation returns:
  rank      args {rows: [{impl, passed, cases, cost_usd, cases_sha}], selected}
            -> {"ranked": [impl, best first], "beats": [challenger impls], "unverified": [impls]}
  verdict   args {rows: [{impl, passed, cases, cost_usd, cases_sha}], selected, markers?: {impl: ABLATION | ...}}
            -> {"verdict": "WIN" | "TIE" | "LOSS" | "UNMEASURED", "text": why, "arms": {impl: "" | ablation | baseline | ...}}
  board     args {rows: [full results rows], selected, strict}
            -> {"exit": int, "text": leaderboard output, "beats": [...], "incomparable": [...]}
An implementation module in ``impls/`` exposes ``build(meter) -> rank``. No implementation here calls a model.
"""
