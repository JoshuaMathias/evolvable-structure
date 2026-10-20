"""The spec-index function. Every implementation is ONE function with this signature:

    find(kind: str, args: dict) -> dict

Given the records of a repository, a person or system narrows them to the few a new use case or input concerns. The cases
drive the LIVE ``esoi.spec_index`` over this repository's own records (the real thing, not a stand-in), so a case names
real record ids. Deterministic and offline; no implementation calls a model.

Kinds and the dict an implementation returns:
  find  args {query, k, expand}  -> {"ids": the ids returned best first, "text": the tier-0 scan of them}
  scan  args {}                  -> {"ratio": characters of the tier-0 line of every record over characters of the full
                                     records, "chars": the tier-0 characters}
An implementation module in ``impls/`` exposes ``build(meter) -> find``.
"""
