"""Measure whether task-to-standard navigation reaches the standards a piece of work needed.

``standards_nav.for_task`` shows an author a few rules from the words of a task, before any code exists. This module scores
that on real work already done, with no person labelling anything. A case is a task as it was written, plus the commit the
work produced. The standards that APPLIED are the ones whose paths match the files that commit changed (and whose ``When:``
matches the file's text at that commit); the standards SHOWN are what ``for_task`` ranks first from the task text alone.

    recall     of the standards that applied (at most ``MAX_SHOWN``, the most an author is shown), the share that were shown
    precision  of the standards shown, the share that applied
    quiet      of the tasks where no standard applied, the share where nothing was shown
    f1         the harmonic mean of recall and precision, the one number a solution can name as its authoritative metric

A case file is a JSON list of ``{"id", "task", "commit", "files"}``; ``files`` are paths changed by ``commit`` in the
repository named by ``--repo``. The applicable set is recomputed from the standards as they are now, so a label never goes
stale when a standard is added. Nothing here calls a model or the network.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Set

from esoi import standards_nav as nav

Reader = Callable[[str, str], str]   # (commit, path) -> the file's text at that commit, "" when it does not exist there


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    shown: Sequence[str]
    applied: Sequence[str]
    hit: Sequence[str]


@dataclass(frozen=True)
class Measurement:
    cases: int
    needed: int
    recall: float
    precision: float
    quiet: float
    f1: float
    results: Sequence[CaseResult]


def applicable(root: Path, texts: Dict[str, str]) -> Set[str]:
    """Ids of the standards that apply to editing any of these files, given each file's path and text."""
    found: Set[str] = set()
    for std in nav.load(root):
        for path, text in texts.items():
            if nav.matches(path, std.paths) and (not std.when or not text or re.search(std.when, text)):
                found.add(std.id)
    return found


def git_reader(repo: Path) -> Reader:
    def read(commit: str, path: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else ""
    return read


def ranked_by_task(root: Path, task: str) -> List[str]:
    return [std.id for _, std, _ in nav.rank_task(root, task)]


def everything(root: Path, task: str) -> List[str]:
    """The baseline arm: ignore the task and show the first standards in the folder."""
    return [std.id for std in nav.load(root)]


def measure(root: Path, cases: Sequence[dict], read: Reader, choose: Callable[[Path, str], List[str]] = ranked_by_task) -> Measurement:
    results: List[CaseResult] = []
    for case in cases:
        texts = {path: read(case["commit"], path) for path in case["files"]}
        applied = sorted(applicable(root, texts))
        shown = choose(root, case["task"])[:nav.MAX_SHOWN]
        results.append(CaseResult(case["id"], shown, applied, sorted(set(shown) & set(applied))))
    needed = [r for r in results if r.applied]
    hits = sum(len(r.hit) for r in results)
    shown_total = sum(len(r.shown) for r in results)
    reachable = sum(min(len(r.applied), nav.MAX_SHOWN) for r in needed)
    recall = hits / reachable if reachable else 0.0
    precision = hits / shown_total if shown_total else 0.0
    unneeded = [r for r in results if not r.applied]
    quiet = sum(1 for r in unneeded if not r.shown) / len(unneeded) if unneeded else 1.0
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    return Measurement(len(results), len(needed), recall, precision, quiet, f1, results)


def cases_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def report(m: Measurement) -> str:
    lines = [f"{r.case_id}: applied {', '.join(r.applied) or 'none'}; shown {', '.join(r.shown) or 'none'}; hit {', '.join(r.hit) or 'none'}"
             for r in m.results]
    lines.append(f"cases {m.cases} (standards applied in {m.needed}); recall {m.recall:.2f} precision {m.precision:.2f} "
                 f"quiet {m.quiet:.2f} f1 {m.f1:.2f}")
    return "\n".join(lines)


def run(root: Path, repo: Path, cases_file: Path, baseline: bool = False) -> Measurement:
    choose = everything if baseline else ranked_by_task
    return measure(root, json.loads(cases_file.read_text(encoding="utf-8")), git_reader(repo), choose)
