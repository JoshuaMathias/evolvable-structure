"""The intent-records check, one function: ``check(kind, args) -> {"exit": int, "problems": [...]}`` over the fixture
repository of check_the_structure (see its interface), restricted to cases about the records: every template field
filled, a problem that is not a task, links that resolve and agree on both sides, a record for every implementation,
and parent links that resolve in the overall network (all reported as S26). Judged on mutation detection and on
staying silent on the clean fixture. ``build(meter)`` in ``impls/`` returns the function. No model is called.
"""
