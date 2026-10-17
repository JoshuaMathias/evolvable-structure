"""The structure-check function. Every implementation is ONE function with this signature:

    check(kind: str, args: dict) -> dict

``kind`` is ``repo``. ``args["edits"]`` is a list of declarative edits (see ``repo_fixture.apply_edits``) that inject
ONE known violation into a small synthetic fixture repository; an empty list is the clean fixture. The function
runs its checker over that fixture and returns

    {"exit": process exit code (0 clean, 1 violations), "problems": ["S4 path: message", ...]}

An implementation is judged on MUTATION DETECTION: for each injected violation it must report the right rule on
the right path, and it must stay silent on the clean fixture (no false positive). No model, no network.
An implementation module in ``impls/`` exposes ``build(meter) -> check``.
"""
