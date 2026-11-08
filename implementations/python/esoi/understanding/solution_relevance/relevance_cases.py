"""Cases for Solution Relevance in any ESOI repository, and the scorer every repository's metric shares.

A case is a text (a commit subject, a request, a candidate) and the solutions that needed consideration for it (``gold``). Cases
come from two sources:

* the repository's own git history (``mine``): a commit's subject is the input and the gold is the solutions whose implementation
  files (``filepath`` in ``implementations.csv``) the commit changed. Bulk commits (more than ``max_files`` files or ``max_solutions``
  solutions), merges and commits that only re-record results or regenerate pages are left out; a fixed share of commits, chosen by
  a hash of the commit id, is held out;
* hand-labelled cases for what history cannot give (an outside candidate, a person's request, a bug report), written beside them.

``score_case`` grades each case by its F-score with ``BETA`` 2 (recall weighs four times precision, since a missed solution is a skipped
consideration and an extra one only costs a pass), which the balanced score takes as its accuracy; a case passes when every gold
solution is returned. Parents the classifier adds count for recall but not against precision. ``aggregate`` reports mean recall,
mean precision, mean F-score and the misses. Standard library only; no model call.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

BETA = 2.0   # recall weighs four times precision in each case's F-score (fixed before any arm was scored with it)
HELD_OUT_SHARE = 0.25
SKIP_SUBJECT = re.compile(r"^(merge|re-?record|regenerate|bump|release|esoi \d|version)\b", re.IGNORECASE)
GENERATED = re.compile(r"(^|/)(README\.md|COMPONENTS\.md|diagram\.md|results\.csv|per_case\.csv|runs\.csv)$|(^|/)tracker/")


def file_owners(registry) -> Dict[str, List[str]]:
    """``{repository-relative file: [solution ids]}`` from the implementations' ``filepath`` cells (a ``::name`` suffix is dropped)."""
    out: Dict[str, List[str]] = {}
    for row in registry.implementations:
        path = (row.get("filepath") or "").split("::", 1)[0].strip()
        sid = row.get("solution_id", "")
        if path and sid and sid not in out.setdefault(path, []):
            out[path].append(sid)
    return out


def folder_owners(config) -> Dict[str, str]:
    """``{repository-relative folder: solution id}`` for each records folder beside the code that holds exactly one solution: a file
    below it belongs to that solution unless a deeper such folder claims it."""
    from esoi.structure.intent_registry import intents
    from esoi.structure.intent_registry.tables import read_csv
    out: Dict[str, str] = {}
    for _, folder in intents.folders(config):
        rows = [r for r in read_csv(folder / "solutions.csv") if r.get("solution_id")]
        if len(rows) == 1 and folder != config.structure:
            out[folder.relative_to(config.root).as_posix()] = rows[0]["solution_id"]
    return out


def owners_of(path: str, files: Mapping[str, List[str]], folders: Mapping[str, str]) -> List[str]:
    """The solutions a changed file belongs to: the implementations that name it, else the deepest one-solution folder above it."""
    if path in files:
        return list(files[path])
    parts = path.split("/")
    for depth in range(len(parts) - 1, 0, -1):
        found = folders.get("/".join(parts[:depth]))
        if found:
            return [found]
    return []


def git_lines(root: Path, *args: str) -> List[str]:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return done.stdout.splitlines() if done.returncode == 0 else []


def held_out(sha: str) -> bool:
    return int(hashlib.sha256(sha.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < HELD_OUT_SHARE


def commits(root: Path, limit: int) -> List[Dict[str, Any]]:
    """``{sha, subject, files}`` of the newest non-merge commits, newest first."""
    out: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for line in git_lines(root, "log", "--no-merges", f"-n{limit}", "--name-only", "--format=@@%h %s"):
        if line.startswith("@@"):
            sha, _, subject = line[2:].partition(" ")
            current = {"sha": sha, "subject": subject.strip(), "files": []}
            out.append(current)
        elif line.strip() and current is not None:
            current["files"].append(line.strip())
    return out


def build(config, registry, hand: Sequence[Mapping[str, Any]], limit: int = 400) -> List[Dict[str, Any]]:
    """The case set of a repository: its hand-labelled cases first, then the cases mined from its history (a hand case whose text
    equals a commit subject replaces the mined one)."""
    texts = {c["args"]["text"] for c in hand}
    return [dict(c) for c in hand] + [c for c in mine(config, registry, limit) if c["args"]["text"] not in texts]


def mine(config, registry, limit: int = 400, max_files: int = 12, max_solutions: int = 3, prefix: str = "git") -> List[Dict[str, Any]]:
    """Cases from the repository's history: commit subject in, the solutions whose implementation files it changed out."""
    owners, folders = file_owners(registry), folder_owners(config)
    known = {r.get("solution_id", "") for r in registry.every_solution()}
    cases: List[Dict[str, Any]] = []
    for commit in commits(config.root, limit):
        files = [f for f in commit["files"] if not GENERATED.search(f)]
        if not files or len(commit["files"]) > max_files or SKIP_SUBJECT.search(commit["subject"]):
            continue
        gold = sorted({sid for f in files for sid in owners_of(f, owners, folders) if sid in known})
        if not gold or len(gold) > max_solutions:
            continue
        cases.append({"id": f"{prefix}-{commit['sha']}", "kind": "git", "area": "commit", "heldout": held_out(commit["sha"]),
                      "description": f"commit {commit['sha']}", "args": {"text": commit["subject"]}, "expect": {"gold": gold}})
    return cases


def f_score(recall: float, precision: float, beta: float = BETA) -> float:
    if recall <= 0 or precision <= 0:
        return 0.0
    return (1 + beta * beta) * precision * recall / (beta * beta * precision + recall)


def judge(gold: Sequence[str], returned: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Recall over every returned solution, precision over the solutions the classifier chose (parents it added are not counted
    against it), the F-score, and whether the case passes (every gold solution returned)."""
    wanted = set(gold)
    every = {r["solution_id"] for r in returned}
    chosen = [r["solution_id"] for r in returned if r.get("role", "solution") == "solution"]
    recall = len(wanted & every) / len(wanted) if wanted else 1.0
    precision = len(wanted & set(chosen)) / len(chosen) if chosen else (1.0 if not wanted else 0.0)
    return {"recall": round(recall, 4), "precision": round(precision, 4), "score": round(f_score(recall, precision), 4),
            "missed": sorted(wanted - every), "ok": recall == 1.0}


def score_case(fn, case: Mapping[str, Any]) -> Dict[str, Any]:
    """One case scored: ``fn(text) -> [{solution_id, role}, ...]`` is the arm; the row carries recall, precision and the misses."""
    found = judge(case["expect"]["gold"], fn(case["args"]["text"]))
    note = f"recall {found['recall']} precision {found['precision']} F2 {found['score']}" + (f"; missed {', '.join(found['missed'])}" if found["missed"] else "")
    return dict(ok=found["ok"], got=case.get("kind", ""), note=note, recall=found["recall"], precision=found["precision"],
                score=found["score"], missed=found["missed"])


def aggregate(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Mean recall and precision over the run, and how many cases missed a gold solution (each a skipped consideration)."""
    rows = [r for r in rows if "recall" in r]
    n = max(len(rows), 1)
    return {"recall": round(sum(r["recall"] for r in rows) / n, 4), "precision": round(sum(r["precision"] for r in rows) / n, 4),
            "f2": round(sum(r.get("score", 0.0) for r in rows) / n, 4), "missed_cases": sum(bool(r["missed"]) for r in rows)}


def runner(root: Path, arm: str, limit: int = 5, rank=None):
    """``fn(text)`` for one arm over the live records of the repository at ``root``, parents included: what ``esoi consider`` returns.
    ``rank(index, text, limit)`` replaces the named arm (a model arm built with ``relevance.model_arm``)."""
    from esoi.structure.intent_registry import config as config_module
    from esoi.understanding.solution_consideration import fan_out, solution_prompt
    from esoi.understanding.spec_search import spec_index
    config = config_module.load(Path(root))
    network = solution_prompt.load(config, stale=False)
    index = spec_index.build(config)
    if rank is None:
        return lambda text: fan_out.classify(network, index, text, limit, arm)
    return lambda text: fan_out.with_parents(network, rank(index, text, limit))
