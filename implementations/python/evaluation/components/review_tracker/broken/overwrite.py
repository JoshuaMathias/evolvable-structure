"""BASELINE: the naive tracker. A rebuild overwrites the tabs wholesale, so reviewers' notes are lost, and nothing is
ever called stale. Zero model calls."""
import repo_fixture
import tracker_fixture
from esoi.structure.intent_registry import config, registry
from esoi.understanding.review_tracker import tracker


def build(meter):
    def track(kind, args):
        root = repo_fixture.fresh_repo(args.get("edits", []))
        cfg = config.load(root)
        for tab_file in cfg.tracker_dir.glob("*.csv"):
            tab_file.unlink()
        tracker.write(cfg, registry.load(cfg), say=lambda text: None)
        return {"stale": [], **tracker_fixture.tab_summary(cfg, args)}
    return track
