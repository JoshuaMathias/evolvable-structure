"""The skill-copy function. Every implementation is ONE function with this signature:

    act(kind: str, args: dict) -> dict

The author's skill lives in a folder that also holds material that is not public, and a public copy is generated from it. The
copy must follow the source after every edit, must not carry anything private, and must be installable without the source.

Kinds and the dict an implementation returns:
  sync     args {source: {path: text}, include: [globs], substitute: [{file, pattern, replacement, reason}]}
             -> {"files": [shipped paths], "text": the shipped SKILL.md, or the error message when the sync refuses}
  drift    args {source, include, change: "none" | "source-edited" | "copy-edited" | "copy-extra-file" | "copy-missing-file"}
             -> {"stale": bool}   whether a check of the committed copy against the source finds it out of date
  leak     args {files: {path: text}, denylist: [terms], private_dirs: [folders]}
             -> {"kinds": sorted kinds of leak found in the copy}
  install  args {existing: "none" | "same" | "other", force: bool, where: "user" | "project"}
             -> {"exit": int, "installed": bool, "text": what it said}
An implementation module in ``impls/`` exposes ``build(meter) -> act``. No implementation here calls a model.
"""
