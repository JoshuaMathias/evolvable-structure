"""The ownership check, one function: ``check(kind, args) -> {"exit": int, "problems": [...]}`` over the fixture
repository of check_the_structure (see its interface), restricted to cases about placement and layering: every file
in exactly one component (S1), component rows (S2), no Python at the root (S3), the size ceiling (S4), module
docstrings (S5), imports pointing inward (S6) and environment-free layers (S13). Judged on mutation detection and
on staying silent on the clean fixture. ``build(meter)`` in ``impls/`` returns the function. No model is called.
"""
