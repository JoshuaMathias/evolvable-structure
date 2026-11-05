"""Dimension 4, reuse and duplication: code copied between files.

Every file's tokens (names, numbers and strings reduced to their kind, imports and docstrings left out) are cut into windows of
``Budgets.clone_window`` tokens, each reduced to a rolling hash. A window whose hash is also found in another file is copied code; a token is
copied when any copied window covers it. The part is the share of tokens that are not copied, stretched so that the duplication budget (a share
of copied tokens) scores zero. The same arithmetic written out in six places is six files sharing windows. Calls per request, the symptom of
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


def copied(project: Project, n: int) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, Counter]]:
    """Per file: tokens, tokens covered by copied windows, and which other files the copies are shared with."""
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
    partners: Dict[str, Counter] = {}
    for path, hs in hashes.items():
        mark = [0] * (len(project.modules[path].tokens) + 1)
        peers: Counter = Counter()
        for start, h in enumerate(hs):
            others = where[h] - {path}
            if others:
                mark[start] += 1
                mark[start + n] -= 1
                peers.update(others)
        run, count = 0, 0
        for delta in mark[:-1]:
            run += delta
            count += 1 if run > 0 else 0
        covered[path] = count
        partners[path] = peers
    return tokens, covered, partners


def measure(project: Project, budgets: Budgets) -> Dimension:
    tokens, covered, partners = copied(project, budgets.clone_window)
    total = sum(tokens.values())
    if total == 0:
        return Dimension("reuse", None)
    ratio = sum(covered.values()) / total
    score = round(max(0.0, 1 - ratio / budgets.duplication_budget), 4)
    worst = sorted(((covered[p], p) for p in covered if covered[p] > 0), reverse=True)
    offenders = [f"{p}: {c} of {tokens[p]} tokens copied, shared with {', '.join(q for q, _ in partners[p].most_common(3))}" for c, p in worst[:50]]
    return Dimension("reuse", score, {"share_of_code_copied": round(ratio, 4), "reuse_score": score}, offenders)
