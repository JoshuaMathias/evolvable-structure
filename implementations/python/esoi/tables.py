"""Small helpers every module shares: CSV reading and writing, ``;``-separated cells, path globs, repo files.

Standard library only. ``glob_re`` keeps ``*`` inside one path segment and lets ``**`` cross segments, so a
component's ``path`` cell means the same thing to every rule.
"""
from __future__ import annotations

import csv
import io
import re
import subprocess
from pathlib import Path
from typing import Dict, List

SEP = ";"
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", "build", "dist", ".esoi_cache"}
CACHE_PREFIX = ".esoi_cache/"


def read_csv(path: Path) -> List[Dict[str, str]]:
    """The rows of a CSV as dicts, or an empty list when the file does not exist."""
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:   # a sheet export may start with a byte-order mark
        return [{k: (v or "") for k, v in row.items() if k} for row in csv.DictReader(handle)]


def read_header(path: Path) -> List[str]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle), [])


def render_csv(columns: List[str], rows: List[Dict[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buf.getvalue()


def write_csv(path: Path, columns: List[str], rows: List[Dict[str, str]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(render_csv(columns, rows), encoding="utf-8")


def ids(cell: str) -> List[str]:
    """The ``;``-separated entries of a cell, stripped, empties dropped."""
    return [part.strip() for part in (cell or "").split(SEP) if part.strip()]


def glob_re(pattern: str) -> "re.Pattern[str]":
    """``*`` stays inside a path segment, ``**`` crosses segments, ``?`` is one character."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def repo_files(root: Path) -> List[str]:
    """Files git knows about (tracked, or untracked and not ignored); a folder that is not a git checkout is walked."""
    root = Path(root)
    done = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root,
                          capture_output=True, text=True)
    if done.returncode == 0:
        return sorted(f for f in set(done.stdout.splitlines()) if not f.startswith(CACHE_PREFIX) and (root / f).is_file())
    found = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and not (set(rel.parts) & SKIP_DIRS):
            found.append(rel.as_posix())
    return sorted(found)
