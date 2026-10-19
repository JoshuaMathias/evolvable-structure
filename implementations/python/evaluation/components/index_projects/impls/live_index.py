"""CURRENT: the live local index, ``esoi.projects``, kept in a folder of its own (the stand-in for ``~/.esoi``). Zero
model calls and no network."""
import index_world as world
from esoi import projects


def build(meter):
    def lookup(kind, args):
        root = world.make_world(args["projects"])
        home = world.repo_fixture.make_temp("esoi_home_")
        projects.init(home)
        for p in args["projects"]:
            location = p.get("location") or str(root / p["dir"])
            projects.add(home, location, project_id=p["id"], name=p["name"], vision=p["vision"],
                         kind=p.get("kind", ""), specifications=p.get("specifications", ""),
                         start_here=p.get("start_here", ""), relations=p.get("relations", ""))
        rows = projects.read_projects(home)
        if kind == "listed":
            return {"ids": sorted(r["project_id"] for r in rows)}
        if kind == "related":
            mine = next(r for r in rows if r["project_id"] == args["project"])
            wanted = args["relation"] + ":"
            return {"ids": sorted(e[len(wanted):] for e in mine["relations"].split(";") if e.startswith(wanted))}
        found = projects.where(home, root / args["path"])
        if found is None:
            return {"project_id": None, "start_here": "", "specifications": ""}
        return {"project_id": found["project_id"], "start_here": found["start_here"],
                "specifications": found["specifications"]}
    return lookup
