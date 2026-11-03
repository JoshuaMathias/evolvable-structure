"""The navigable-records function. Every implementation is ONE function with this signature:

    layout(kind: str, args: dict) -> dict

``kind`` is ``layout`` and ``args`` are ``{repo, solution, fresh}``: the label of a repository (``this`` or ``adopter-N``, see
``glance_fixture``), the solution a case is about, and whether to lay the records out again. The implementation lays the
repository's records out the way it keeps them (``esoi_folder``: all of the top intent's records in the structure folder;
``beside_code``: each record in the folder that holds its code, with the READMEs the library generates) and returns
``{"root": the folder of the laid-out tree, "digest": a hash of every README written}``. The score is computed from that tree by the
checks in ``score.py``, the same for every arm. Deterministic and offline; no implementation here calls a model.
An implementation module in ``impls/`` exposes ``build(meter) -> layout``.
"""
