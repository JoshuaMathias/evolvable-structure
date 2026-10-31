"""Shared by the arms: the live views of this repository's own records plus two items of another source, built once."""
from pathlib import Path

from esoi import config as config_module, spec_index, spec_search

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "esoi.toml").is_file())
INDEX = spec_index.build(config_module.load(ROOT))
ITEMS = {"runbook": {"name": "Invoice batch runbook", "summary": "Restart the nightly invoice batch and check queue depth.",
                     "keywords": ["invoice", "batch", "queue"]},
         "keys": {"name": "Backup key rotation", "summary": "Rotate the backup encryption keys every month.",
                  "keywords": ["backup", "encryption", "rotation"]}}
VIEWS = spec_search.views_from_items(ITEMS, kind="card", source="cards") + spec_search.views_from_index(INDEX)


def runner(search_fn):
    def run(kind, args):
        got = search_fn(args["query"], VIEWS, expand=args.get("expand", 0), max_ranked=args.get("k", 5))
        return {"ids": got.ids, "route": got.route}
    return run
