"""The declaration function. Every implementation is ONE function with this signature:

    specify(kind: str, args: dict) -> dict

A solution and its alternatives are declared once, where the code is (``@solution``, ``@implementation``, ``register``),
and the records follow: the declarations are read without importing the code, what the records lack is reported, the missing
rows are written with only what the code knows (never over text a person wrote), and one command creates a whole new
solution. The cases drive the LIVE ``esoi.declarations`` and ``esoi.newsolution`` over throwaway projects. Deterministic
and offline.

Kinds and the dict an implementation returns:
  scan  args {files: {path: source}}
        -> {"solutions": [ids], "implementations": ["solution:name"], "ports": {id: class}, "parameters": {id: text},
            "outputs": {id: text}}
  sync  args {edits: [fixture edits], solution?, keep?: {path, key_col, key, col, value}}
        -> {"before_count": S30 findings before, "after_count": after one sync, "changes": rows written, "second": rows a
            second sync writes, "row": cells of the solution row (name, parameters, outputs, selected, metric_kind,
            implementations), "kept": bool (the cell a person wrote still holds its text)}
  new   args {id, twice?: bool, intent?}
        -> {"files": [...], "text_only": bool (every remaining finding is a field only a person can write, or the first recorded run),
            "valid": bool (the module compiles and cases.json parses), "refused": bool (a second create is refused)}
An implementation module in ``impls/`` exposes ``build(meter) -> specify``. No implementation here calls a model.
