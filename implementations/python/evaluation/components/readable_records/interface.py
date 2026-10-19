"""The readable-records function. Every implementation is ONE function with this signature:

    readable(kind: str, args: dict) -> dict

An intent's folder holds five CSV files; a reader should learn what the intent is from a page generated from them, and that
page must never disagree with them. The cases drive the LIVE ``esoi.readme`` and the check over throwaway projects.
Deterministic and offline.

Kinds and the dict an implementation returns:
  readme  args {edits: [fixture edits]}  -> {"text": the top intent's README.md}
  sub     args {edits: [fixture edits]}  -> {"text": the README.md of the sub-intent "voices" ("" when none)}
  check   args {edits: [fixture edits]}
          -> {"stale": how many README.md files the check reports out of date, "text": the findings}
An implementation module in ``impls/`` exposes ``build(meter) -> readable``. No implementation here calls a model.
