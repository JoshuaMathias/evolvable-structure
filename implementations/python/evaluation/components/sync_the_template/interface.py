"""The template-reading function. Every implementation is ONE function with this signature:

    read(kind: str, args: dict) -> dict

The intent template is written by its author as markdown prose and refined over time, so the reader must follow the
author's words: a field keeps its key when its wording is refined, a new labelled field becomes a new key, an empty
bullet (an unfinished section) is skipped and counted, a missing section is reported rather than fatal, and a copy
that no longer matches its source is called stale.

Kinds and the dict an implementation returns:
  parse   args {text} -> {"keys": {entity: {"required": [...], "interface": [...]}}, "text": the notes joined}
  stale   args {text, committed: "same" | "edited"}
            -> {"stale": bool}   whether the committed parsed copy differs from what ``text`` parses to
An implementation module in ``impls/`` exposes ``build(meter) -> read``. No implementation here calls a model.
"""
