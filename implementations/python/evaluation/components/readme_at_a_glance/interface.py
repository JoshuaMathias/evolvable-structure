"""The readme-at-a-glance function. Every implementation is ONE function with this signature:

    page(kind: str, args: dict) -> dict

``kind`` is ``page`` and ``args`` are ``{repo, intent, fresh}``: the label of a repository (``this`` or ``adopter-N``, see
``glance_fixture``), the intent folder in it (an intent id, or ``top``), and whether to read the repository again. The
implementation returns ``{"text": the README.md that layout writes for that intent folder}``. The score is computed from the text
by the checks in ``score.py``, the same for every arm. Deterministic and offline; no implementation here calls a model.
An implementation module in ``impls/`` exposes ``build(meter) -> page``.
"""
