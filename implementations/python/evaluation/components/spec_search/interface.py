"""The spec-search function. Every implementation is ONE function with this signature:

    run(kind: str, args: dict) -> dict

Given a request, the search ranks views of this repository's own records (the live specification index, plus two plain
items standing for a product's own notes) and returns the keys it chose. The cases drive the LIVE ``esoi.spec_search``
over the live records, so a case names real record ids. Deterministic and offline: no vector search and no judge are
injected, because a stand-in for either would measure the stand-in. What the vector search and the judge add is measured
by the adopter that supplies them, on its own records.

Kinds and the dict an implementation returns:
  find  args {query, k}  -> {"ids": ranked keys best first (linked ones after), "route": how it was decided}
An implementation module in ``impls/`` exposes ``build(meter) -> run``.
"""
