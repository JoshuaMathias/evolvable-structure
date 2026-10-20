"""Shared by the arms: the live index of this repository's own records, built once, and the two kinds of case."""
from pathlib import Path

from esoi import config as config_module, registry, spec_index

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "esoi.toml").is_file())
CONFIG = config_module.load(ROOT)
INDEX = spec_index.build(CONFIG)


def full_size():
    loaded = registry.load(CONFIG)
    rows = [r for group in (loaded.problems, loaded.ideals, loaded.implementations, loaded.metrics, loaded.every_solution())
            for r in group]
    return sum(len(v) for r in rows for v in r.values())


def runner(find_fn):
    def find(kind, args):
        if kind == "scan":
            scan = "\n".join(spec_index.line(e) for e in INDEX["entries"])
            return {"chars": len(scan), "ratio": round(len(scan) / full_size(), 3)}
        hits = find_fn(INDEX, args["query"], args.get("k", 5), args.get("expand", 0))
        return {"ids": [h["id"] for h in hits], "text": spec_index.render_scan(INDEX, hits)}
    return find
