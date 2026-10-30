"""The world of the metric-record evaluation and its tests: a throwaway repository written by ``esoi.scaffold.init`` (records, a
recorded run, an evaluation component), the edits a case makes to it, fake meters, and a spy on the processes an arm would start.

``run_case(kind, args, strategy)`` builds the world a case describes, calls ``strategy.<kind>(world, args)`` and returns its
dict. Nothing here belongs to an implementation: a live implementation and a naive baseline are given the same world. No model,
no network, no real data.
"""
from __future__ import annotations

import contextlib
import csv
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import esoi
from esoi import scaffold
from esoi.metric_meter import AFTER, BEFORE
from esoi.spec_slice import SpecSlice

HANG_SECONDS = 0.8   # a meter that hangs holds its thread this long; cases give the reading far less
SLICE = SpecSlice(root="none", solution_id="greet-a-person", metric_id="greeting-pass-rate",
                  metric_command="esoi run greet_a_person --impl live")
ONE_LINE = "greet_a_person / live: 1/2 passed (dev 1/2, held-out 0/0)\n"


@dataclass
class World:
    """What a strategy is handed: the repository, the folder the case looks from, and the processes an arm tried to start."""
    root: Path
    folder: Optional[str]
    spawned: List[Dict[str, Any]] = field(default_factory=list)
    ledger_dir: str = ""


class FakeMeter:
    """A meter built from a case: the values it gives (the last repeats), whether it takes time, hangs, raises, or serves one moment."""

    def __init__(self, spec: Dict[str, Any]):
        self.name = spec["name"]
        self.cheap = spec.get("cheap", True)
        if "serves" in spec:
            self.serves = tuple(spec["serves"])
        self.values = list(spec["values"]) if "values" in spec else [spec.get("value")]
        self.hang, self.raises, self.reads = spec.get("hang", False), spec.get("raises", False), 0

    def measure(self, spec_slice: SpecSlice, working_dir: Optional[str] = None) -> Optional[float]:
        self.reads += 1
        if self.raises:
            raise RuntimeError("broken")
        if self.hang:
            time.sleep(HANG_SECONDS)
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


def default_environ() -> Dict[str, str]:
    """The environment an arm is started from in a case: this process's, with this copy of ``esoi`` importable by the child."""
    return {**os.environ, "PYTHONPATH": str(Path(esoi.__file__).resolve().parents[1])}


def fake_meters(specs: List[Dict[str, Any]]) -> List[FakeMeter]:
    return [FakeMeter(spec) for spec in specs]


def edit_solutions(root: Path, column: str, text: str) -> None:
    path = root / "esoi" / "solutions.csv"
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row["solution_id"] == "greet-a-person":
            row[column] = text
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def edit_world(root: Path, setup: Dict[str, Any]) -> None:
    """Apply a case's edits: the milestones cell, the arm made paid (listed, declared, or by its last run), cases that changed,
    no recorded run, or an arm that takes a minute."""
    components = root / "evaluation" / "components"
    arm = components / "greet_a_person" / "impls" / "live.py"
    if "milestones" in setup:
        edit_solutions(root, "milestones", setup["milestones"])
    if setup.get("paid_listed"):
        with open(root / "esoi.toml", "a", encoding="utf-8") as handle:
            handle.write('paid_arms = ["greet_a_person/live"]\n')
    if setup.get("declared_paid"):
        arm.write_text("PAID = True\n" + arm.read_text(encoding="utf-8"), encoding="utf-8")
    if setup.get("model_called"):
        results = components / "results.csv"
        lines = results.read_text(encoding="utf-8").splitlines()
        fields = lines[1].split(",")
        fields[7], fields[14] = "5", "some-model"   # model_calls, model
        results.write_text("\n".join([lines[0], ",".join(fields), *lines[2:]]) + "\n", encoding="utf-8")
    if setup.get("other_cases"):
        cases = components / "greet_a_person" / "cases.json"
        cases.write_text(cases.read_text(encoding="utf-8").replace("Ada", "Grace"), encoding="utf-8")
    if setup.get("no_row"):
        header = (components / "results.csv").read_text(encoding="utf-8").splitlines()[0]
        (components / "results.csv").write_text(header + "\n", encoding="utf-8")
    if setup.get("slow_arm"):
        arm.write_text("import time\ntime.sleep(60)\n" + arm.read_text(encoding="utf-8"), encoding="utf-8")


class Proc:
    returncode = 0

    def communicate(self, timeout: Optional[float] = None):
        return ONE_LINE, None


@contextlib.contextmanager
def spying(spawned: List[Dict[str, Any]], on: bool):
    """While ``on``, ``subprocess.Popen`` records the argv, environment and folder of each start and runs nothing."""
    if not on:
        yield
        return
    real = subprocess.Popen

    def record(argv, **kwargs):
        spawned.append({"argv": list(argv), "env": dict(kwargs.get("env") or {}), "cwd": kwargs.get("cwd")})
        return Proc()

    subprocess.Popen = record
    try:
        yield
    finally:
        subprocess.Popen = real


def run_case(kind: str, args: Dict[str, Any], strategy: Any) -> Dict[str, Any]:
    """Build the world the case describes and ask ``strategy.<kind>``."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        scaffold.init(root, "demo_pkg", say=lambda *_: None)
        edit_world(root, args.get("setup", {}))
        bare = Path(tmp) / "bare"
        bare.mkdir()
        folder = {"repo": str(root), "bare": str(bare), "none": None}[args.get("folder", "repo")]
        world = World(root, folder, ledger_dir=str(Path(tmp) / "ledger"))
        with spying(world.spawned, args.get("spy", False)):
            return getattr(strategy, kind)(world, args)


__all__ = ["AFTER", "BEFORE", "SLICE", "FakeMeter", "World", "default_environ", "fake_meters", "run_case"]
