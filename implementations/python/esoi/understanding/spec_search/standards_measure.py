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
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from esoi.structure.structure_check import standards_check
from esoi.understanding.spec_search import standards_nav as nav

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


def check_breaks(std, check, files: Sequence[str], commit: str, read: Reader, added: dict) -> bool:
    """Whether what a commit added breaks one check of a standard."""
    scope = [f for f in files if nav.matches(f, std.paths)]
    if check.kind == "needs-test":
        tests = nav.glob_to_regex(check.argument or "tests/**")
        return bool(scope) and not any(tests.match(f) for f in files)
    if check.kind == "regex":
        pattern = re.compile(check.argument)
        return any(pattern.search(text) for f in scope for text in added.get(f, {}).values())
    if check.kind == "undecorated-def":
        return any(standards_check.undecorated_defs(read(commit, f), added.get(f, {})) for f in scope)
    return False


def violated(root: Path, commit: str, files: Sequence[str], read: Reader, diff: Callable[[str], str]) -> Set[str]:
    """Ids of the standards whose own checks would have flagged what ``commit`` added: the objective label for work
    that actually broke a rule, taken from the code and not from anyone's opinion."""
    added = standards_check.added_lines(diff(commit))
    return {std.id for std in nav.load(root) if any(check_breaks(std, check, files, commit, read, added) for check in std.checks)}


def git_diff(repo: Path) -> Callable[[str], str]:
    def diff(commit: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), "show", "-U0", "--no-color", "--format=", commit], capture_output=True, text=True)
        return done.stdout
    return diff


def git_reader(repo: Path) -> Reader:
    def read(commit: str, path: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else ""
    return read


def ranked_by_task(root: Path, task: str) -> List[str]:
    """The arm that ships: ``standards_nav.select_for_task``. Its base rates come from ``rates.csv``, so a run over the
    commits that wrote that file is in sample; ``compare`` is the held-out reading."""
    return [std.id for std, _ in nav.select_for_task(root, task)]


def everything(root: Path, task: str) -> List[str]:
    """The baseline arm: ignore the task and show the first standards in the folder."""
    return [std.id for std in nav.load(root)]


def measure(root: Path, cases: Sequence[dict], read: Reader, choose: Callable[[Path, str], List[str]] = ranked_by_task,
            diff: Optional[Callable[[str], str]] = None) -> Measurement:
    results: List[CaseResult] = []
    for case in cases:
        texts = {path: read(case["commit"], path) for path in case["files"]}
        applied = sorted(violated(root, case["commit"], list(case["files"]), read, diff) if diff else applicable(root, texts))
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


def run(root: Path, repo: Path, cases_file: Path, baseline: bool = False, label: str = "applicable") -> Measurement:
    """``label`` is ``applicable`` (the standards whose paths match the changed files) or ``violated`` (the standards whose
    checks flag what the commit added)."""
    choose = everything if baseline else ranked_by_task
    diff = git_diff(repo) if label == "violated" else None
    return measure(root, json.loads(cases_file.read_text(encoding="utf-8")), git_reader(repo), choose, diff)


def label_cases(root: Path, repo: Path, cases: Sequence[dict]) -> List[Set[str]]:
    read, diff = git_reader(repo), git_diff(repo)
    return [violated(root, case["commit"], list(case["files"]), read, diff) for case in cases]


def train(root: Path, repo: Path, cases_file: Path, today: str) -> Path:
    """Write ``rates.csv`` beside the standards: the share of the cases whose work broke each standard."""
    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    labels = label_cases(root, repo, cases)
    folder = nav.standards_dir(root)
    out = folder / "rates.csv"
    rows = ["standard,rate,cases,date"] + [f"{std.id},{sum(std.id in l for l in labels) / len(cases):.4f},{len(cases)},{today}"
                                          for std in nav.load(root)]
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return out


@dataclass(frozen=True)
class ArmReading:
    arm: str
    train_f1: float
    test_f1: float
    low_vs_baseline: float
    high_vs_baseline: float


def f1_of(counts: Sequence[Tuple[int, int, int]], idx: Sequence[int]) -> float:
    hit = sum(counts[i][0] for i in idx)
    shown = sum(counts[i][1] for i in idx)
    reach = sum(counts[i][2] for i in idx)
    recall = hit / reach if reach else 0.0
    precision = hit / shown if shown else 0.0
    return 2 * recall * precision / (recall + precision) if recall + precision else 0.0


def compare(root: Path, repo: Path, cases_file: Path, boots: int = 2000, seed: int = 7, held_out: float = 0.3) -> List[ArmReading]:
    """Score each way of choosing standards for a task on the newest ``held_out`` share of the cases, with the rates learned
    only from the older cases. ``low`` and ``high`` bound a 95 percent interval on the arm's F1 minus the baseline's
    (bootstrap over the held-out cases); an interval that excludes zero is a significant difference."""
    import random
    cases = json.loads(cases_file.read_text(encoding="utf-8"))   # newest first, as the builders write them
    labels = label_cases(root, repo, cases)
    cut = int(len(cases) * held_out)
    test, older = list(range(cut)), list(range(cut, len(cases)))
    ids = [std.id for std in nav.load(root)]
    rates = {sid: sum(sid in labels[i] for i in older) / len(older) for sid in ids}
    cache: Dict[str, Tuple[List[str], List[str]]] = {}

    def ranked(task: str) -> Tuple[List[str], List[str]]:
        if task not in cache:
            found = nav.rank_task(root, task)
            cache[task] = ([std.id for _, std, _ in found], [std.id for _, std, hits in found if hits])
        return cache[task]

    def base(task: str) -> List[str]:
        return [sid for sid in sorted(ids, key=lambda i: -rates[i]) if rates[sid] >= nav.BASE_RATE_MIN]

    def base_plus_keywords(task: str) -> List[str]:
        return nav.combine(base(task), ranked(task)[1])

    arms = {"show-the-first-four": lambda task: ids, "tag-keyword-match": lambda task: ranked(task)[0],
            "base-rate": base, "base-rate-plus-keywords": base_plus_keywords}
    counts = {name: [(len(set(choose(c["task"])[:nav.MAX_SHOWN]) & labels[i]), len(choose(c["task"])[:nav.MAX_SHOWN]),
                      min(len(labels[i]), nav.MAX_SHOWN)) for i, c in enumerate(cases)] for name, choose in arms.items()}
    read = git_reader(repo)
    shown_by_file = [sorted(applicable(root, {path: read(c["commit"], path) for path in c["files"]}))[:nav.MAX_SHOWN] for c in cases]
    counts["for-file (edit time, files known)"] = [(len(set(shown_by_file[i]) & labels[i]), len(shown_by_file[i]), min(len(labels[i]), nav.MAX_SHOWN))
                                                   for i in range(len(cases))]
    arms["for-file (edit time, files known)"] = None
    rng = random.Random(seed)
    samples = [[rng.choice(test) for _ in test] for _ in range(boots)]
    readings = []
    for name in arms:
        gaps = sorted(f1_of(counts[name], s) - f1_of(counts["show-the-first-four"], s) for s in samples)
        readings.append(ArmReading(name, f1_of(counts[name], older), f1_of(counts[name], test), gaps[int(boots * 0.025)], gaps[int(boots * 0.975) - 1]))
    return readings


def compare_report(readings: Sequence[ArmReading]) -> str:
    lines = ["arm; F1 on older commits; F1 on held-out newest commits; 95% interval of held-out F1 minus show-the-first-four"]
    lines += [f"{r.arm}; {r.train_f1:.3f}; {r.test_f1:.3f}; {r.low_vs_baseline:+.3f} to {r.high_vs_baseline:+.3f}" for r in readings]
    return "\n".join(lines)
