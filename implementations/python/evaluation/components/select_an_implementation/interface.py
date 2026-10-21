"""The selection function. Every implementation is ONE function with this signature:

    select(kind: str, args: dict) -> dict

The cases give a selection table whose targets are standard-library classes, and ask what resolves. The rules:
an explicit name beats an override, which beats the table default; names are case-insensitive; an unknown solution
or name fails loudly and lists the choices (never a silent fallback); targets are imported lazily, so a broken
entry that is not chosen costs nothing; a registered implementation is selectable and may become the default.

Kinds and the dict an implementation returns:
  resolve   args {table, solution, name?, overrides?, register?: [{name, target, default?}], config?: bool}
            -> {"resolved": class name, "chosen": name, "names": [...]}  or  {"error": exception name, "text": message}
  declared  args {solution, registered?: {name: "module:Attr"}, decorated?: {name: "module:Attr"}, interface?: bool,
            records_default?, deployment?, env?, context?, using?, lazy_module?: {name, source}}
            -> {"resolved": class name, "chosen": name, "layer": "call" | "context" | "environment" | "deployment" |
            "project", "names": [...], "layers": [layers that name one, innermost first]}  or  {"error", "text"}
            The graceful layer (``esoi.runtime``): an implementation declared in code (the decorator, or a registration
            of another package's class) runs when the interface is called; which one is decided by the cascade, the
            innermost layer winning: per call (``using``), context (``override``), environment (``ESOI_SELECT_<ID>``),
            deployment (``[selection]`` in ``esoi.toml``), then the project default, the solution's ``selected`` in the
            records (no second copy in code). An unknown name fails loudly with the choices and the layer that named it.
            ``lazy_module`` is an implementation in a module not imported yet, found through its record's ``filepath`` and
            imported only when chosen.
An implementation module in ``impls/`` exposes ``build(meter) -> select``. No implementation here calls a model.
"""
