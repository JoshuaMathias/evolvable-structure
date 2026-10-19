"""BROKEN: the naive lookup a first draft would write. It names the first folder of the path as the project and knows
nothing else, so it cannot start, relate or list. Zero model calls."""


def build(meter):
    def lookup(kind, args):
        if kind in ("listed", "related"):
            return {"ids": []}
        first = args["path"].split("/")[0]
        return {"project_id": first, "start_here": "", "specifications": ""}
    return lookup
