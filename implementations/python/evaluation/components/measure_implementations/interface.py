"""The measurement function. Every implementation is ONE function with this signature:

    measure(kind: str, args: dict) -> dict

The harness that records numbers has to be right: a record carries the commit (suffixed ``-dirty`` when the
measured code has uncommitted changes) and the case file's hash, a changed case file changes the hash, a run budget
is enforced, and ``--only`` runs only the named cases. The cases drive the LIVE ``esoi.harness`` over a synthetic
mini component built in a temporary folder with its own throwaway git repository. Deterministic and offline.

Kinds and the dict an implementation returns:
  record    args {cases_file: "json" | "csv", dirty: bool, edit_cases: bool}
            -> {"git_sha": bool, "dirty": bool, "cases_sha_matches": bool, "cases_sha_changes": bool, "rows": n}
  run       args {impl, argv: [extra flags]} -> {"cases": n, "passed": n, "error": exception name | None}
            the shared ``run_component`` driver on the mini component (``--only``, ``--max-calls``)
  validity  args {} -> {"cases": n, "good_passed": n, "bad_passed": n}
            a component is valid offline when a reference good implementation passes every case and a reference bad
            one fails every case
An implementation module in ``impls/`` exposes ``build(meter) -> measure``. No implementation here calls a model.
"""
