"""The repositories the README-at-a-glance evaluation reads: this repository and the adopters named in ``ESOI_GLANCE_ADOPTERS``
(paths separated by the platform's path separator, in the order ``adopter-1``, ``adopter-2``). Nothing here writes to them and
nothing calls a model. ``load`` and ``intent_of`` are what every arm of ``readme_at_a_glance`` reads through."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Tuple

from esoi import config, intents, readme, registry

ADOPTERS = "ESOI_GLANCE_ADOPTERS"
CACHE: Dict[str, Tuple] = {}


def root_of(label: str) -> Path:
    if label == "this":
        return Path(__file__).resolve().parents[4]
    chosen = [p for p in os.environ.get(ADOPTERS, "").split(os.pathsep) if p]
    number = int(label.rsplit("-", 1)[1]) if label.startswith("adopter-") and label.rsplit("-", 1)[1].isdigit() else 0
    if not 1 <= number <= len(chosen):
        raise LookupError(f"{label}: set {ADOPTERS} to the paths of the adopting repositories to measure")
    return Path(chosen[number - 1])


def load(label: str, fresh: bool = False) -> Tuple:
    """``(config, registry, view)`` of one repository; ``fresh`` reads it again instead of reusing the last load."""
    if fresh or label not in CACHE:
        cfg = config.load(root_of(label))
        loaded = registry.load(cfg)
        CACHE[label] = (cfg, loaded, readme.view_of(cfg, loaded))
    return CACHE[label]


def intent_of(view, name: str):
    found = [i for i in view.intents if (i.is_top if name == "top" else i.intent_id == name)]
    if not found:
        raise LookupError(f"no intent {name} here")
    return found[0]
