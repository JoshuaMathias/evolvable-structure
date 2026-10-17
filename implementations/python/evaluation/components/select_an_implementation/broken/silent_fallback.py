"""BASELINE: the naive selector. An unknown name quietly falls back to the default, names are case-sensitive,
overrides are ignored, and every entry is imported up front. Zero model calls."""
import importlib


def load(ref):
    module, _, attr = ref.partition(":")
    return getattr(importlib.import_module(module), attr)


def build(meter):
    def select(kind, args):
        entries = args["table"][args["solution"]]["implementations"]
        loaded = {n: load(r["target"] if isinstance(r, dict) else r) for n, r in entries.items()}
        name = args.get("name") if args.get("name") in loaded else args["table"][args["solution"]]["default"]
        return {"resolved": loaded[name].__name__, "chosen": name, "names": sorted(loaded)}
    return select
