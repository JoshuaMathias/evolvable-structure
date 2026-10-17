"""The staleness check, one function: ``check(kind, args) -> {"exit": int, "problems": [...]}`` over the fixture repository
of check_the_structure (see its interface), restricted to cases about whether a recorded result still counts: no result, no
commit, other cases than the ones now on disk, and (with ``strict`` in the args) uncommitted code or measured code that has
changed since the recorded commit. A change outside the measured code is not staleness. Judged on mutation detection and on
staying silent when every result is current. ``build(meter)`` in ``impls/`` returns the function. No model is called.
"""
