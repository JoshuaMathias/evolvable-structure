"""BASELINE: a hand-made copy. Someone copies the source files once and never looks again, so the copy keeps private text, never
notices that it is out of date, finds no leak, and an install overwrites whatever is there."""


def build(meter):
    def act(kind, args):
        if kind == "sync":
            return {"files": sorted(args["source"]), "text": args["source"].get("SKILL.md", "")}
        if kind == "drift":
            return {"stale": False}
        if kind == "leak":
            return {"kinds": []}
        return {"exit": 0, "installed": True, "text": "copied"}
    return act
