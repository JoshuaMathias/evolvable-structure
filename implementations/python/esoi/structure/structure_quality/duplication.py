"""Dimension 4, reuse and duplication: code copied between files.

Every file's tokens (names, numbers and strings reduced to their kind, imports and docstrings left out) are cut into windows of
``Budgets.clone_window`` tokens, each reduced to a rolling hash. A window whose hash is also found in another file is copied code; a token is
copied when any copied window covers it. The score is a graded curve of the copied share (``reuse_score``). The same arithmetic written out in six places is six files sharing windows. A token covered by a window that
``Budgets.family_files`` or more files share is boilerplate (many wrappers with one body, which a table-driven helper would remove); the rest is
accidental clones; both shares are reported and both count, through the one copied share scored by ``reuse_score``. Calls per request, the symptom of
duplicated work at run time, need traces and are a case source of a consumer, not read here.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

from esoi.structure.structure_quality.balance import Budgets, Dimension
from esoi.structure.structure_quality.project import Project

MOD = (1 << 61) - 1
BASE = 1000003


def window_hashes(ids: List[int], n: int) -> List[int]:
    """The rolling hash of every run of ``n`` token ids (empty when there are fewer than ``n``)."""
    if len(ids) < n:
        return []
    top = pow(BASE, n, MOD)
    h = 0
    out: List[int] = []
    for i, t in enumerate(ids):
        h = (h * BASE + t + 1) % MOD
        if i >= n:
            h = (h - (ids[i - n] + 1) * top) % MOD
        if i >= n - 1:
            out.append(h)
    return out


def covered_counts(hashes: List[int], where: Dict[int, Set[str]], n: int, size: int, minimum: int) -> int:
    """The tokens of one file covered by a window that ``minimum`` or more files share (this file counted among them)."""
    mark = [0] * (size + 1)
    for start, h in enumerate(hashes):
        if len(where[h]) >= minimum:
            mark[start] += 1
            mark[start + n] -= 1
    run, count = 0, 0
    for delta in mark[:-1]:
        run += delta
        count += 1 if run > 0 else 0
    return count


def copied(project: Project, n: int, family: int):
    """Per file: tokens, tokens covered by any copied window, tokens covered by a window shared by ``family`` or more files (a family of same-shaped
    wrappers), and which other files the copies are shared with."""
    vocab: Dict[str, int] = {}
    hashes: Dict[str, List[int]] = {}
    where: Dict[int, Set[str]] = defaultdict(set)
    for path, module in project.modules.items():
        ids = [vocab.setdefault(tok, len(vocab)) for tok in module.tokens]
        hashes[path] = window_hashes(ids, n)
        for h in set(hashes[path]):
            where[h].add(path)
    tokens = {p: len(m.tokens) for p, m in project.modules.items()}
    covered: Dict[str, int] = {}
    families: Dict[str, int] = {}
    partners: Dict[str, Counter] = {}
    for path, hs in hashes.items():
        size = len(project.modules[path].tokens)
        covered[path] = covered_counts(hs, where, n, size, 2)
        families[path] = covered_counts(hs, where, n, size, family)
        peers: Counter = Counter()
        for h in hs:
            peers.update(where[h] - {path})
        partners[path] = peers
    return tokens, covered, families, partners


def reuse_score(ratio: float) -> float:
    """The reuse score of a copied share ``ratio`` (0 to 1): ``(1 - ratio) ** 3``. It falls steadily from 1 with no copied code to 0 with every token
    copied, so no real share of copying saturates it (5 percent copied scores 0.86, 15 percent 0.61, 30 percent 0.34, 50 percent 0.12)."""
    return round((1 - min(max(ratio, 0.0), 1.0)) ** 3, 4)


def measure(project: Project, budgets: Budgets) -> Dimension:
    tokens, covered, families, partners = copied(project, budgets.clone_window, budgets.family_files)
    total = sum(tokens.values())
    if total == 0:
        return Dimension("reuse", None)
    ratio = sum(covered.values()) / total
    boilerplate = sum(families.values()) / total
    score = reuse_score(ratio)
    worst = sorted(((covered[p], p) for p in covered if covered[p] > 0), reverse=True)
    offenders = [f"{p}: {c} of {tokens[p]} tokens copied ({'boilerplate shared by a family of ' + str(budgets.family_files) + ' or more files, a table-driven helper would remove it' if families[p] * 2 > c else 'clones'}), "
                 f"shared with {', '.join(q for q, _ in partners[p].most_common(3))}" for c, p in worst[:50]]
    return Dimension("reuse", score, {"share_of_code_copied": round(ratio, 4), "of_it_boilerplate_in_families": round(boilerplate, 4),
                                      "of_it_accidental_clones": round(ratio - boilerplate, 4), "reuse_score": score}, offenders)
