"""CURRENT: the live tracker, ``esoi.tracker`` (``stale``, ``write``), over the clean fixture repository.
Zero model calls."""
import csv

import repo_fixture
from esoi import config, registry, tracker


def build(meter):
    def track(kind, args):
        root = repo_fixture.fresh_repo(args.get("edits", []))
        cfg = config.load(root)
        stale = tracker.stale(cfg, registry.load(cfg))
        tab = args.get("tab", "solutions")
        tracker.write(cfg, registry.load(cfg), say=lambda text: None)
        rows = list(csv.DictReader((cfg.tracker_dir / f"{tab}.csv").open()))
        header = list(rows[0].keys()) if rows else []
        hit = next((r for r in rows if r[header[0]] == args.get("key")), {}) if rows else {}
        return {"stale": stale, "value": hit.get(args.get("column", ""), ""), "header": header, "rows": len(rows)}
    return track
