"""BASELINE: routing rows written into the skill's own index, the way an index that names the author's projects would
route. The rows are frozen when written, so a project added or moved later is not in them. Zero model calls."""
import index_world as world

ROWS = {
    "alpha": {"start_here": "CLAUDE.md", "specifications": "esoi.toml", "uses": ["beta"], "used-by": []},
    "beta": {"start_here": "docs/structure/network.md", "specifications": "esoi.toml", "uses": [], "used-by": ["alpha"]},
}


def build(meter):
    def lookup(kind, args):
        world.make_world(args["projects"])
        if kind == "listed":
            return {"ids": sorted(ROWS)}
        if kind == "related":
            return {"ids": sorted(ROWS.get(args["project"], {}).get(args["relation"], []))}
        for part in args["path"].split("/"):
            if part in ROWS:
                return {"project_id": part, "start_here": ROWS[part]["start_here"],
                        "specifications": ROWS[part]["specifications"]}
        return {"project_id": None, "start_here": "", "specifications": ""}
    return lookup
