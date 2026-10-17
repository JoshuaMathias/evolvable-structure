"""BASELINE: the naive tracker. A rebuild overwrites the tabs wholesale, so reviewers' notes are lost, and nothing is
ever called stale. Zero model calls."""
import csv

import repo_fixture
from esoi import config, registry, tracker


def build(meter):
    def track(kind, args):
        root = repo_fixture.fresh_repo(args.get("edits", []))
        cfg = config.load(root)
        for tab_file in cfg.tracker_dir.glob("*.csv"):
            tab_file.unlink()
        tracker.write(cfg, registry.load(cfg), say=lambda text: None)
        tab = args.get("tab", "solutions")
        rows = list(csv.DictReader((cfg.tracker_dir / f"{tab}.csv").open()))
        header = list(rows[0].keys()) if rows else []
        hit = next((r for r in rows if r[header[0]] == args.get("key")), {}) if rows else {}
        return {"stale": [], "value": hit.get(args.get("column", ""), ""), "header": header, "rows": len(rows)}
    return track
