"""Synthetic fixture repositories for the structure evaluations (no real data, public-repo safe).

``baseline_repo(dest)`` writes a small repository that follows every rule: ``esoi init``'s example, plus a port with
a selection table, an adapters layer, an overall network and generated docs. ``apply_edits(root, edits)`` injects one
known violation as a few declarative edits. ``fresh_repo(edits)`` copies the clean baseline (built once per process)
and applies the edits, so cases never see each other's damage. ``report(root)`` runs the live checker over a
fixture and returns the exit code and the problem lines.
"""
from __future__ import annotations

import csv
import io
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

from esoi import check, config, scaffold

PORTS = ('"""The fixture port."""\nfrom typing import Protocol\n\n\nclass Greeter(Protocol):\n'
         '    """Says hello."""\n\n    def greet(self, name: str) -> str: ...\n')
SELECTION = ('"""Selection as data."""\nSELECTION = {"greet-a-person": {"default": "plain", "implementations": '
             '{"plain": "demo.greet:greet"}}}\n')
ADAPTERS = '"""Fixture adapters layer."""\n'
TOML_EXTRA = '''
selection = "demo/selection.py:SELECTION"

[rules.S13]
layers = ["core"]
'''
TEMPLATES: Dict[str, Path] = {}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with Path(path).open(newline="") as fh:
        return list(csv.DictReader(fh))


def read_header(path: Path) -> List[str]:
    with Path(path).open(newline="") as fh:
        return next(csv.reader(fh))


def csv_text(cols: List[str], rows: List[Dict[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def write(root: Path, rel: str, text: str) -> None:
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def set_cell(root: Path, rel: str, key_col: str, key: str, col: str, value: str) -> None:
    path = Path(root) / rel
    rows, cols = read_rows(path), read_header(path)
    next(r for r in rows if r[key_col] == key)[col] = value
    path.write_text(csv_text(cols, rows))


def baseline_repo(dest: Path) -> Path:
    """The clean fixture: ``esoi init`` plus a port, a selection table, an adapters layer, then generated docs."""
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    scaffold.init(root, "demo", say=lambda text: None)
    toml = (root / "esoi.toml").read_text().replace('layers = ["core"]', 'layers = ["core", "adapters"]')
    write(root, "esoi.toml", toml + TOML_EXTRA)
    write(root, "demo/ports.py", PORTS)
    write(root, "demo/selection.py", SELECTION)
    write(root, "demo/adapters/__init__.py", ADAPTERS)
    set_cell(root, "docs/structure/components.csv", "component_id", "package", "path", "demo/*.py")
    path = root / "docs/structure/components.csv"
    rows, cols = read_rows(path), read_header(path)
    rows.append(dict(component_id="adapters", layer="adapters", path="demo/adapters/*.py", role="Fixture adapters.",
                     solutions="greet-a-person"))
    path.write_text(csv_text(cols, rows))
    set_cell(root, "docs/structure/solutions.csv", "solution_id", "greet-a-person", "port", "Greeter")
    set_cell(root, "docs/structure/solutions.csv", "solution_id", "greet-a-person", "selected", "plain")
    check.write_docs(config.load(root), say=lambda text: None)
    return root


def apply_edits(root: Path, edits: List[dict]) -> None:
    """Apply declarative edits. ``write``/``append``/``replace``/``delete`` act on files; ``csv_cell``, ``csv_drop``,
    ``csv_dup`` and ``csv_append`` act on a CSV row found by ``key_col`` == ``key``; ``regen`` re-runs the live
    ``--write-docs`` so a case can isolate one rule from stale generated docs."""
    root = Path(root)
    for e in edits:
        op, rel = e["op"], e.get("path", "")
        path = root / rel
        if op == "write":
            write(root, rel, e["content"])
        elif op == "append":
            path.write_text(path.read_text() + e["content"])
        elif op == "replace":
            text = path.read_text()
            assert e["old"] in text, f"fixture edit does not apply: {e['old']!r} not in {rel}"
            path.write_text(text.replace(e["old"], e["new"], 1))
        elif op == "delete":
            path.unlink()
        elif op == "git_record":
            git_record(root)
        elif op == "regen":
            check.write_docs(config.load(root), say=lambda text: None)
        elif op.startswith("csv_"):
            rows, cols = read_rows(path), read_header(path)
            hit = next(r for r in rows if r[e["key_col"]] == e["key"]) if op != "csv_append" else None
            if op == "csv_cell":
                hit[e["col"]] = e["value"]
            elif op == "csv_drop":
                rows.remove(hit)
            elif op == "csv_dup":
                rows.append(dict(hit))
            elif op == "csv_append":
                rows.append({c: e["row"].get(c, "") for c in cols})
            path.write_text(csv_text(cols, rows))
        else:
            raise ValueError(op)


def git_record(root: Path) -> None:
    """Commit the fixture and stamp every recorded result with that commit, as `esoi run --record` does on committed code."""
    def git(*args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=root,
                              capture_output=True, text=True, check=True).stdout.strip()
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "fixture")
    sha = git("rev-parse", "--short", "HEAD")
    path = Path(root) / "evaluation/components/results.csv"
    rows, cols = read_rows(path), read_header(path)
    for row in rows:
        row["git_sha"] = sha
    path.write_text(csv_text(cols, rows))


def fresh_repo(edits: List[dict], kind: str = "repo") -> Path:
    """A private copy of the clean fixture with ``edits`` applied."""
    if kind not in TEMPLATES:
        template = Path(tempfile.mkdtemp(prefix="esoi_fixture_"))
        baseline_repo(template / "r")
        TEMPLATES[kind] = template / "r"
    root = Path(tempfile.mkdtemp(prefix="esoi_case_")) / "r"
    shutil.copytree(TEMPLATES[kind], root)
    apply_edits(root, edits)
    return root


def report(root: Path, strict: bool = False) -> Dict[str, object]:
    """Run the live checker over a fixture and return its verdict: exit code and the problem lines."""
    try:
        problems = check.check(config.load(root), strict)
    except Exception as exc:
        problems = [f"CRASH {type(exc).__name__}: {exc}"]
    return {"exit": 1 if problems else 0, "problems": problems}
