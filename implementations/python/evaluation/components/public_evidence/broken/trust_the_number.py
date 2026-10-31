"""BASELINE: what a first draft would write. It trusts every number: every candidate is grade A with no flag and nothing needs a
run, and a ranking is the raw numbers, whoever reported them. Zero model calls."""
from .. import impls  # noqa: F401
from ..impls import live


def build(meter):
    def run(kind, args):
        rows = live.read(args["rows"])
        if kind == "grade":
            keys = {f"{e.candidate}/{e.dimension}" for e in rows}
            return {"grades": {k: "A" for k in keys}, "flags": {k: [] for k in keys}, "needs_own_run": {k: False for k in keys}}
        out = {}
        for dim in args["dims"]:
            mine = [e for e in rows if e.dimension == dim]
            out[dim] = [e.candidate for e in sorted(mine, key=lambda e: e.value, reverse=mine[0].better == "higher")]
        return {"order": out}
    return run
