"""BASELINE: what a first draft would write. It believes what it is told: a milestone list split on any number followed by a
full stop, the first lexical hit taken as the solution, the first meter believed at any moment with no budget, an arm run
whatever it may cost, a number coerced from whatever was typed, and the last row for a metric taken as the answer. Zero model calls."""
import re
import subprocess
import sys
from pathlib import Path

import metric_record_fixture as fixture
from esoi import config, spec_index
from esoi.metric_meter import AFTER, BEFORE


class Naive:
    def milestone(self, world, args):
        parts = [p.strip() for p in re.split(r"\d+\.\s+", args["cell"]) if p.strip()]
        number = re.search(r"\d+(?:\.\d+)?(%?)", parts[0]) if parts else None
        return {"number": 1 if parts else 0, "text": parts[0] if parts else "",
                "target": (float(number.group(0).rstrip("%")) / (100 if number.group(1) else 1)) if number else None}

    def slice(self, world, args):
        if not world.folder:
            return {"solution_id": "", "metric_id": "", "milestone_number": 0}
        index = spec_index.build(config.load(Path(world.folder)))
        hits = spec_index.find_specs(index, args["request"], k=1)
        return {"solution_id": hits[0]["id"] if hits else "", "metric_id": "", "milestone_number": 1 if hits else 0}

    def reading(self, world, args):
        meters = fixture.fake_meters(args["meters"])
        value = meters[0].measure(fixture.SLICE) if meters else None
        return {"value": value, "meter": meters[0].name if value is not None else "", "note": "", "announced": 0}

    def arm(self, world, args):
        argv = [sys.executable, "-m", "esoi", "run", "greet_a_person", "--impl", "live"]
        environ = dict(args.get("environ", fixture.default_environ()))
        proc = subprocess.Popen(argv, cwd=str(world.root), env=environ, stdout=subprocess.PIPE, text=True)
        out, _ = proc.communicate()
        found = re.search(r":\s*(\d+)/(\d+) passed", out)
        return {"value": int(found.group(1)) / int(found.group(2)) if found else None, "spawned": len(world.spawned),
                "argv": argv[-2:], "leaked": sorted(k for k in environ if "KEY" in k or "TOKEN" in k), "seconds": 0.0}

    def result(self, world, args):
        float(args.get("before") or args.get("after") or 0)
        return {"error": ""}

    def reconcile(self, world, args):
        last = {}
        for row in args["rows"]:
            last[row.get("metric_id", "m")] = row
        rows = list(last.values())
        return {"sources": [r["source"] for r in rows], "disagrees": [False for r in rows],
                "values": [[r.get("before"), r.get("after")] for r in rows], "line": ""}

    def iteration(self, world, args):
        rows = [[r["source"], r.get("before"), r.get("after")] for r in args.get("worker", [])]
        return {"rows": rows, "block": False, "reads": [0 for _ in args.get("meters", [])]}


def build(meter):
    strategy = Naive()
    return lambda kind, args: fixture.run_case(kind, args, strategy)
