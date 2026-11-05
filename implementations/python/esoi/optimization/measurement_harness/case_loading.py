"""Load a component's cases and pick the sample of them a run scores."""
from __future__ import annotations

import argparse
import csv
import importlib
import json
from typing import Dict, List, Optional

from esoi.optimization.leaderboard.case_identity import cases_digest
from esoi.optimization.measurement_harness.component_folder import prepare_path
from esoi.structure.intent_registry.config import Config


def stratified_sample(cases: List[dict], n: int, seed: int = 0) -> List[dict]:
    """``n`` cases spread over the strata (``stratum``, else ``dataset``, else ``area``), the same cases every
    time for one seed. A smaller ``n`` is a prefix of a larger one."""
    import random
    rng = random.Random(seed)
    groups: Dict[str, List[dict]] = {}
    for case in sorted(cases, key=lambda c: str(c["id"])):
        groups.setdefault(case.get("stratum") or case.get("dataset") or case.get("area") or "", []).append(case)
    for group in groups.values():
        rng.shuffle(group)
    picked: List[dict] = []
    while len(picked) < n and any(groups.values()):
        for name in sorted(groups):
            if groups[name] and len(picked) < n:
                picked.append(groups[name].pop(0))
    return sorted(picked, key=lambda c: str(c["id"]))


def sample_label(args: argparse.Namespace, cases: List[dict], whole: int) -> str:
    """The ``sample`` cell of a run: blank for the full set, ``only:ids`` for ``--only``, else ``sample:N``."""
    if len(cases) == whole:
        return ""
    if args.only:
        return "only:" + ",".join(str(c["id"]) for c in cases)
    return f"sample:{args.sample}"


def sample_label_args(row: Optional[Dict[str, str]]) -> List[str]:
    """The ``esoi run`` flags a row's ``sample`` label names (``only:`` or ``sample:``), read from the label alone, else ``[]``.
    It imports nothing from the repository's evaluation, so a reader that must not run its code can use it."""
    label = ((row or {}).get("sample") or "").strip()
    if label.startswith("only:"):
        return ["--only", label[len("only:"):]]
    if label.startswith("sample:"):
        return ["--sample", label[len("sample:"):]]
    return []


def sample_args(config: Config, component: str, row: Optional[Dict[str, str]]) -> List[str]:
    """The ``esoi run`` flags that reproduce the sample a recorded row was scored on (``[]`` for the full set). A row
    recorded before the ``sample`` column that scored fewer cases than the set has is read as ``--sample`` of that size,
    which is what ``--sample`` recorded (stratified_sample is deterministic and a smaller N is a prefix of a larger). That
    reading holds only while the case file is unchanged; on other cases the old count says nothing, so the full set runs."""
    if not row:
        return []
    if labelled := sample_label_args(row):
        return labelled
    if (row.get("cases_sha") or "") != cases_digest(component, config.evaluation):
        return []   # a legacy count on other cases says nothing about a sample: the full set
    try:
        count = int(float(row.get("cases") or 0))
    except ValueError:
        return []
    return ["--sample", str(count)] if 0 < count < len(load_cases(component, config)) else []


def load_cases(component: str, config: Config) -> List[dict]:
    """The component's cases: the ``load_cases()`` of its score module when it has one (a dataset folder another
    harness also reads), else ``cases.json``, or ``cases.csv`` when the dataset is reviewed as a sheet (a
    ``heldout`` cell of ``yes`` marks a held-out case)."""
    prepare_path(config)
    score = importlib.import_module(f"{component}.score")
    if hasattr(score, "load_cases"):
        return score.load_cases()
    folder = config.evaluation / component
    if (folder / "cases.json").exists():
        return json.loads((folder / "cases.json").read_text(encoding="utf-8"))
    with (folder / "cases.csv").open(newline="", encoding="utf-8") as fh:
        cases = list(csv.DictReader(fh))
    for case in cases:
        case["heldout"] = (case.get("heldout") or "").strip().lower() == "yes"
    return cases
