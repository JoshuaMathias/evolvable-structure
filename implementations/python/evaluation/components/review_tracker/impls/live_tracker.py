"""CURRENT: the live tracker, ``esoi.understanding.review_tracker.tracker`` (``stale``, ``write``), over the clean fixture repository.
Zero model calls."""
import repo_fixture
import tracker_fixture
from esoi.structure.intent_registry import config, registry
from esoi.understanding.review_tracker.interface import tracker


def build(meter):
    def track(kind, args):
        root = repo_fixture.fresh_repo(args.get("edits", []))
        cfg = config.load(root)
        stale = tracker.stale(cfg, registry.load(cfg))
        tracker.write(cfg, registry.load(cfg), say=lambda text: None)
        return {"stale": stale, **tracker_fixture.tab_summary(cfg, args)}
    return track
