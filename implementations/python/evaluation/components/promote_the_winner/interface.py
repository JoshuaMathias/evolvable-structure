"""The promotion function. Every implementation is ONE function with this signature:

    promote(kind: str, args: dict) -> dict

The best implementation of a solution should run without anyone editing three files by hand, but only on evidence that
counts and only where the solution's policy allows it. The cases drive the LIVE ``esoi.promote`` over synthetic results
tables and records in a temporary folder. Deterministic and offline.

Kinds and the dict an implementation returns:
  decide  args {rows: [results rows], selected, promotion?: "automatic", records?: [{implementation_id, filepath}],
                stale?: [impl names whose row no longer counts], table_default?: bool}
          -> {"count": proposals, "status": "promote" | "propose" | "blocked" | "none", "winner", "selected", "command",
              "reason", "text" (the reason, for checks that quote it)}   (none when no rival clearly beats the selected implementation)
  apply   args as decide
          -> {"applied": bool, "selected": the `selected` cell afterwards, "command": the metric command afterwards,
              "evidence": bool (selected_by names the date, the commit and the cases hash)}
An implementation module in ``impls/`` exposes ``build(meter) -> promote``. No implementation here calls a model.
