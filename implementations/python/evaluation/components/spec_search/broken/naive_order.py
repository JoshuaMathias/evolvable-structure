"""BASELINE: what a first draft would write. It ignores the words of the request and returns the first views in the order
they are listed, so it never finds the record asked for and never returns nothing. Zero model calls."""
from .. import impls  # noqa: F401
from ..impls import live


def build(meter):
    def run(kind, args):
        return {"ids": [v.key for v in live.VIEWS][:args.get("k", 5)], "route": "unjudged"}
    return run
