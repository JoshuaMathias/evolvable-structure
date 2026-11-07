"""The repositories the navigable-records evaluation reads (this repository, and the adopters named in ``ESOI_GLANCE_ADOPTERS``, in
the order ``adopter-1``, ``adopter-2``) and the layout each arm gives their records. ``layout`` copies only the records, the
configuration, the root README and an empty stand-in for each file an implementation names into a temporary tree, moves the records
as the arm says, writes the READMEs the library generates, and returns where it is. Nothing is written to the repository measured and no
model is called."""
from __future__ import annotations

import dataclasses
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Tuple

import glance_fixture
from esoi.structure.intent_registry import besidecode, config, intents, registry
from esoi.understanding.readable_records.interface import readme

CACHE: Dict[Tuple[str, str], Tuple[Path, str]] = {}
RECORDS: Dict[Tuple[str, str], dict] = {}   # the [records] table each laid-out tree is read with
KEPT = ("intent.csv", *intents.RECORD_FILES)
KEEPERS: list = []   # the temporary folders of the laid-out trees, cleaned at exit by their finalizers


def copy_records(cfg, target: Path) -> None:
    """The records of every folder of the tree, the configuration and the root README, at the same relative paths."""
    for name in ("esoi.toml", "pyproject.toml", "README.md"):
        if (cfg.root / name).is_file():
            shutil.copy(cfg.root / name, target / name)
    for _, folder in intents.folders(cfg):
        for name in KEPT:
            if (folder / name).is_file():
                path = target / (folder / name).relative_to(cfg.root)
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(folder / name, path)


def stand_in_code(cfg, target: Path) -> None:
    """An empty file where each implementation record says its code is (the evaluation reads where code is, never what it says)."""
    for _, folder in intents.folders(cfg):
        for row in intents.read_csv(folder / "implementations.csv"):
            here = besidecode.code_folder(cfg, row.get("filepath", ""))
            entry = (row.get("filepath") or "").split("::")[0].strip()
            if here is not None and entry:
                path = target / entry
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()


def layout(label: str, arm: str, fresh: bool = False) -> Tuple[Path, str]:
    """``(root of the laid-out tree, digest of its READMEs)`` for one repository under one arm: ``beside_code`` or ``esoi_folder``."""
    if fresh or (label, arm) not in CACHE:
        cfg = config.load(glance_fixture.root_of(label))
        if (label, arm) in CACHE:
            shutil.rmtree(CACHE[(label, arm)][0], ignore_errors=True)
        scratch = tempfile.TemporaryDirectory(prefix="navigable-")
        KEEPERS.append(scratch)   # removed when the process exits, so no laid-out tree is left in the temporary folder
        target = Path(scratch.name)
        final, digest = lay_out(cfg, arm, target)
        CACHE[(label, arm)] = (target, digest)
        RECORDS[(label, arm)] = final.records
    return CACHE[(label, arm)]


def lay_out(cfg, arm: str, target: Path):
    """Copy the records into ``target`` under one arm, move them to where the arm puts them, write the READMEs; (the final config, their digest)."""
    copy_records(cfg, target)
    stand_in_code(cfg, target)
    records = dict(cfg.records) if isinstance(cfg.records, dict) else {}
    if arm == "beside_code" and not records.get("beside_code"):
        records["beside_code"] = besidecode.code_hosts(cfg)
    moved = dataclasses.replace(cfg, root=target, records=records)
    besidecode.apply(moved, besidecode.plan(moved, "beside" if arm == "beside_code" else "gather"))
    final = moved if arm == "beside_code" else dataclasses.replace(moved, records={**records, "beside_code": []})
    pages = readme.pages(final, registry.load(final))
    for path, text in pages:
        path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256("".join(f"{p.relative_to(target)}\n{t}" for p, t in sorted(pages)).encode()).hexdigest()[:16]
    return final, digest


def load(label: str, arm: str, fresh: bool = False):
    """``(config, registry)`` of the laid-out tree, read with the same ``[records]`` table it was laid out with."""
    target, _ = layout(label, arm, fresh)
    cfg = dataclasses.replace(config.load(target), records=RECORDS[(label, arm)])
    return cfg, registry.load(cfg)
