"""Synthetic fixture repositories for the structure evaluations (no real data, public-repo safe).

``baseline_repo(dest)`` writes a small repository that follows every rule: ``esoi init``'s example, plus a port with
a selection table, an adapters layer, an overall network and generated docs. ``apply_edits(root, edits)`` injects one
known violation as a few declarative edits. ``fresh_repo(edits)`` copies the clean baseline (built once per process)
and applies the edits, so cases never see each other's damage. ``report(root)`` runs the live checker over a
fixture and returns the exit code and the problem lines.
"""
from __future__ import annotations

import atexit
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
    set_cell(root, "esoi/intent.csv", "intent_id", "demo", "name", "Consistent greetings")
    set_cell(root, "esoi/intent.csv", "intent_id", "demo", "vision_statement", "Every person is greeted by their own name.")
    # the scaffold also leaves its top solution to the project: write the stand-in project's own
    for column, value in dict(name="Greetings sent", scoped_purpose="Everything that greets a person for this project.",
                              goals="Every greeting is consistent.", knowledge="The house style for greetings.",
                              measures_of_success="The greeting cases pass.", problem_ids="greeting-by-hand",
                              ideal_ids="consistent-greeting", metric_ids="greeting-pass-rate").items():
        set_cell(root, "esoi/solutions.csv", "solution_id", "project-purpose", column, value)
    for column, value in dict(name="The project", description="The greeting function and the structure that records it.",
                              advantages="One place to start.", disadvantages="Nothing rival has been compared.").items():
        set_cell(root, "esoi/implementations.csv", "implementation_id", "project-purpose:the-project", column, value)
    set_cell(root, "esoi/problems.csv", "problem_id", "greeting-by-hand", "solution_ids", "greet-a-person;project-purpose")
    set_cell(root, "esoi/metrics.csv", "metric_id", "greeting-pass-rate", "solution_ids", "greet-a-person;project-purpose")
    toml = (root / "esoi.toml").read_text().replace('layers = ["core"]', 'layers = ["core", "adapters"]')
    write(root, "esoi.toml", toml + TOML_EXTRA)
    write(root, "demo/ports.py", PORTS)
    write(root, "demo/selection.py", SELECTION)
    write(root, "demo/adapters/__init__.py", ADAPTERS)
    set_cell(root, "esoi/components.csv", "component_id", "package", "path", "demo/*.py")
    path = root / "esoi/components.csv"
    rows, cols = read_rows(path), read_header(path)
    rows.append(dict(component_id="adapters", layer="adapters", path="demo/adapters/*.py", role="Fixture adapters.",
                     solutions="greet-a-person"))
    path.write_text(csv_text(cols, rows))
    set_cell(root, "esoi/solutions.csv", "solution_id", "greet-a-person", "port", "Greeter")
    set_cell(root, "esoi/solutions.csv", "solution_id", "greet-a-person", "selected", "plain")
    check.write_docs(config.load(root), say=lambda text: None)
    return root


def apply_edits(root: Path, edits: List[dict]) -> None:
    """Apply declarative edits. ``write``/``append``/``replace``/``delete`` act on files; ``csv_cell``, ``csv_drop``,
    ``csv_dup``, ``csv_clone`` (a copy with the cells of ``row`` replaced) and ``csv_append`` act on a CSV row found by
    ``key_col`` == ``key``; ``csv_drop_col`` removes the column ``col``; a ``csv_cell`` value of ``{HEAD}`` is the
    current short commit; ``git_commit`` commits what changed without restamping the results; ``regen`` re-runs the live
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
        elif op == "git_commit":
            git_commit(root)
        elif op == "csv_drop_col":
            rows, cols = read_rows(path), read_header(path)
            path.write_text(csv_text([c for c in cols if c != e["col"]], [{k: v for k, v in r.items() if k != e["col"]} for r in rows]))
        elif op == "regen":
            check.write_docs(config.load(root), say=lambda text: None)
        elif op.startswith("csv_"):
            rows, cols = read_rows(path), read_header(path)
            hit = next(r for r in rows if r[e["key_col"]] == e["key"]) if op != "csv_append" else None
            if op == "csv_cell":
                hit[e["col"]] = e["value"].replace("{HEAD}", head_sha(root)) if "{HEAD}" in e["value"] else e["value"]
            elif op == "csv_clone":
                rows.append({**hit, **e["row"]})
            elif op == "csv_drop":
                rows.remove(hit)
            elif op == "csv_dup":
                rows.append(dict(hit))
            elif op == "csv_append":
                rows.append({c: e["row"].get(c, "") for c in cols})
            path.write_text(csv_text(cols, rows))
        else:
            raise ValueError(op)


def run_git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=root,
                          capture_output=True, text=True, check=True).stdout.strip()


def head_sha(root: Path) -> str:
    return run_git(root, "rev-parse", "--short", "HEAD")


def git_commit(root: Path) -> None:
    """Commit every change so far (the fixture must already be a git repository, see ``git_record``)."""
    run_git(root, "add", "-A")
    run_git(root, "commit", "-q", "-m", "change")


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


CREATED: List[Path] = []   # every temporary folder this process made, removed when it exits


def remove_created() -> None:
    for folder in CREATED:
        shutil.rmtree(folder, ignore_errors=True)


atexit.register(remove_created)


def fresh_repo(edits: List[dict], kind: str = "repo") -> Path:
    """A private copy of the clean fixture with ``edits`` applied. The copy is removed when the process exits, so a long
    run does not fill the temporary folder."""
    if kind not in TEMPLATES:
        template = Path(tempfile.mkdtemp(prefix="esoi_fixture_"))
        CREATED.append(template)
        baseline_repo(template / "r")
        TEMPLATES[kind] = template / "r"
    folder = Path(tempfile.mkdtemp(prefix="esoi_case_"))
    CREATED.append(folder)
    root = folder / "r"
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
