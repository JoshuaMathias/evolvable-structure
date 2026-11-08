"""The solution-relevance function. Every implementation is ONE function with this signature:

    classify(text: str) -> [{"solution_id": str, "role": "solution" | "parent", ...}, ...]

Given the text of a change, a candidate or a request, return the solutions that need their own consideration for it, best first,
then the parent level of each. The cases drive the LIVE classifier over this repository's own records (``esoi consider`` returns the
same list): mined from this repository's git history (a commit subject in, the solutions whose code it changed out) and written by
hand for what history cannot give (requests, outside candidates, bug reports). A case passes when every gold solution is returned
and at least a quarter of the solutions chosen are gold (``esoi.understanding.solution_relevance.relevance_cases``).
An implementation module in ``impls/`` exposes ``build(meter) -> classify``. No implementation here calls a model.
"""
