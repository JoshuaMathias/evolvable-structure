"""Synthetic inputs for the measurement cases: results tables and a mini component in a throwaway git repository.
Nothing here touches this repository's results log or any real component."""
from __future__ import annotations

import contextlib
import csv
import itertools
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from esoi.config import Config
from esoi.registry import Registry

RESULT_COLUMNS = ["date", "component", "impl", "cases", "passed", "dev", "heldout", "model_calls",
                  "tokens_in", "tokens_out", "cost_usd", "seconds", "git_sha", "cases_sha", "model"]
MINI_CASES = [{"id": f"M{i}", "kind": "echo", "args": {"n": i}, "expect": {"eq": {"n": i}}, "heldout": i == 3}
              for i in (1, 2, 3)]
counter = itertools.count(1)
GOOD = 'def build(meter):\n    def echo(kind, args):\n        return {"n": args["n"]}\n    return echo\n'
BAD = 'def build(meter):\n    def echo(kind, args):\n        return {"n": -1}\n    return echo\n'
SPENDER = 'def build(meter):\n    def echo(kind, args):\n        meter.record()\n        return {"n": args["n"]}\n    return echo\n'
SCORE = 'from esoi import expect\n\n\ndef score_case(fn, case):\n    return expect.score_kind_case(fn, case)\n'


def full_row(partial: dict, component: str = "mini") -> dict:
    row = dict(date="2026-10-16", component=component, cases=10, passed=5, dev="", heldout="", model_calls=0,
               tokens_in=0, tokens_out=0, cost_usd=0.0, seconds=0.1, git_sha="abc1234", cases_sha="aaaa1111", model="none")
    row.update(partial)
    return row


def write_results(path: Path, rows: list, component: str = "mini") -> None:
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESULT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow(full_row(r, component))


def registry_selecting(selected: str, component: str = "mini") -> Registry:
    return Registry(solutions=[{"solution_id": "mini-solution", "selected": selected, "metric_kind": "eval",
                                "metric_command": f"esoi run {component} --impl {selected}", "selected_by": "the fixture"}])


@contextlib.contextmanager
def mini_component(cases_file: str = "json", markers: dict | None = None):
    """A mini component with three cases and impls ``good``, ``bad`` and ``spender`` (one model call per case), inside
    a temporary git repository whose ``mini_pkg`` folder stands for the code under test. ``markers`` adds impl files
    whose docstring opens with a marker word (``{"name": "ABLATION"}``). Yields (config, component name)."""
    with tempfile.TemporaryDirectory(prefix="esoi_measure_") as tmp:
        root = Path(tmp)
        name = f"minicomp{next(counter)}"
        comp = root / "evaluation" / "components" / name
        (comp / "impls").mkdir(parents=True)
        (root / "mini_pkg").mkdir()
        (root / "mini_pkg" / "live.py").write_text("X = 1\n")
        (comp / "__init__.py").write_text("")
        (comp / "impls" / "__init__.py").write_text("")
        (comp / "score.py").write_text(SCORE)
        for impl, text in (("good", GOOD), ("bad", BAD), ("spender", SPENDER)):
            (comp / "impls" / f"{impl}.py").write_text(text)
        for impl, marker in (markers or {}).items():
            (comp / "impls" / f"{impl}.py").write_text(f'"""{marker}: a reference arm."""\n')
        if cases_file == "json":
            (comp / "cases.json").write_text(json.dumps(MINI_CASES))
        else:
            with open(comp / "cases.csv", "w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=["id", "kind", "heldout"], lineterminator="\n")
                writer.writeheader()
                writer.writerows({"id": c["id"], "kind": "echo", "heldout": "yes" if c["heldout"] else ""} for c in MINI_CASES)

        def git(*a):
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a],
                                  cwd=root, capture_output=True, text=True, check=True)
        git("init", "-q")
        git("add", "-A")
        git("commit", "-q", "-m", "init")
        config = Config(root=root, package="mini_pkg")
        sys.path[:0] = [str(comp.parent), str(root)]
        try:
            yield config, name
        finally:
            for entry in (str(comp.parent), str(root)):
                if entry in sys.path:
                    sys.path.remove(entry)
            for mod in [m for m in sys.modules if m == name or m.startswith(name + ".")]:
                del sys.modules[mod]
