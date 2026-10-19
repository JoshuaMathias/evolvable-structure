"""FLOOR: nothing beyond each project's own records. From a path it climbs to the nearest ``esoi.toml`` and reports that
folder as the project, with the specifications entry the configuration implies; it knows no other project, no file to
start with and no relation. Zero model calls."""
from pathlib import Path

import index_world as world


def build(meter):
    def lookup(kind, args):
        root = world.make_world(args["projects"])
        if kind in ("listed", "related"):
            return {"ids": []}
        here = (root / args["path"]).resolve()
        for folder in [here, *here.parents]:
            if folder == root.resolve().parent:
                break
            if (folder / "esoi.toml").is_file():
                return {"project_id": Path(folder).name, "start_here": "", "specifications": "esoi.toml"}
        return {"project_id": None, "start_here": "", "specifications": ""}
    return lookup
