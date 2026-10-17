"""BASELINE: a consumer check that only verifies the registry has its required columns and unique ids. The naive
version a first draft would write. Zero model calls."""
import csv

import consumer_fixture


def build(meter):
    def check(kind, args):
        root = consumer_fixture.fresh_consumer(args.get("edits", []))
        with (root / "registry.csv").open(newline="") as fh:
            reader = csv.DictReader(fh)
            have = reader.fieldnames or []
            ids = [r.get("integration_id") for r in reader]
        problems = [f"C1 registry: missing {c}" for c in consumer_fixture.OPTIONS.required_columns if c not in have]
        problems += [f"C1 {i}: duplicate integration_id" for i in set(ids) if ids.count(i) > 1]
        return {"exit": 1 if problems else 0, "problems": problems}
    return check
