"""The local-index lookup. Every implementation is ONE function with this signature:

    lookup(kind: str, args: dict) -> dict

The cases describe a small world of projects on disk (folders with ESOI specifications) and a person's index of them,
then ask where to look. Kinds and the dict an implementation returns:
  where    args {projects, path}      -> {"project_id": id or None, "start_here": file, "specifications": entry}
  related  args {projects, project, relation} -> {"ids": [project ids related that way, sorted]}
  listed   args {projects}            -> {"ids": [every project it knows, sorted]}
A project is {id, dir, name, vision, files?, start_here?, specifications?, relations?, kind?, location?}: ``dir`` is a
folder under the world's root, ``location`` a URL for a project that is not on this machine. An implementation module in
``impls/`` exposes ``build(meter) -> lookup``. No implementation here calls a model or the network.
"""
