"""The consumer-check function. Every implementation is ONE function with this signature:

    check(kind: str, args: dict) -> dict

``kind`` is ``consumer``. ``args["edits"]`` is a list of declarative edits (see ``repo_fixture.apply_edits``) that
inject ONE known violation into a small synthetic consumer repository, built beside a synthetic library; an empty
list is the clean consumer. The function runs its checker and returns

    {"exit": 0 clean or 1 violations, "problems": ["C3 id: message", ...]}

An implementation is judged on mutation detection: the right rule for each injected violation, and silence on the
clean consumer. An implementation module in ``impls/`` exposes ``build(meter) -> check``. No model is called.
"""
