"""The selection function. Every implementation is ONE function with this signature:

    select(kind: str, args: dict) -> dict

The cases give a selection table whose targets are standard-library classes, and ask what resolves. The rules:
an explicit name beats an override, which beats the table default; names are case-insensitive; an unknown solution
or name fails loudly and lists the choices (never a silent fallback); targets are imported lazily, so a broken
entry that is not chosen costs nothing; a registered implementation is selectable and may become the default.

Kinds and the dict an implementation returns:
  resolve   args {table, solution, name?, overrides?, register?: [{name, target, default?}], config?: bool}
            -> {"resolved": class name, "chosen": name, "names": [...]}  or  {"error": exception name, "text": message}
An implementation module in ``impls/`` exposes ``build(meter) -> select``. No implementation here calls a model.
"""
