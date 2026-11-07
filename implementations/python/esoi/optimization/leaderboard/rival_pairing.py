"""Which rival rows are compared with the selected arm: the newest cases both were scored on, the rivals that share none, and the looks a pair had."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.optimization.leaderboard.arm_kinds import is_ablation
from esoi.optimization.leaderboard.case_identity import comparable, describe_cases
from esoi.optimization.leaderboard.results_log import Row, Rows, is_partial


def history_of(rows: Rows, history: Optional[Dict[str, List[Row]]] = None) -> Dict[str, List[Row]]:
    """The rows each arm has, oldest first: ``history`` when given, else just each arm's latest row."""
    return history if history is not None else {impl: [row] for impl, row in rows.items()}


def newest_shared(mine: List[Row], theirs: List[Row]) -> Optional[Tuple[int, int]]:
    """``(rival position, selected position)`` of the newest pair of rows scored on the same cases and sample, or None."""
    best = None
    for i, rival in enumerate(theirs):
        for j, own in enumerate(mine):
            if comparable(own, rival) and (best is None or (i, j) > best):
                best = (i, j)
    return best


def why_unmatched(selected: str, mine: List[Row], theirs: List[Row], recorded: List[Row]) -> str:
    """Why a rival shares no cases and sample with the selected arm: it has only named cases or slices, or the two ran on other cases."""
    if not theirs:
        return f"scored on {recorded[-1].get('sample')} only; not comparable: named cases only (no run of the whole set)"
    return f"scored on {describe_cases(theirs[-1])}, {selected} on {describe_cases(mine[-1])}: no run of the two on the same cases and sample"


def rival_pairs(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                history: Optional[Dict[str, List[Row]]] = None) -> Tuple[List[Tuple[Row, Row]], List[Tuple[str, str]]]:
    """``(pairs, unmatched)`` for ``selected``. A pair is ``(selected row, rival row)`` scored on the same cases (see
    ``cases_key``): for each rival, the newest key both arms have a row for, and on it each arm's newest row.
    ``unmatched`` is ``(rival, why)`` for each rival (ablation and validity arms excluded) that shares no key, so it is
    not compared at all."""
    every = history_of(rows, history)
    arms = {impl: [r for r in found if not is_partial(r)] for impl, found in every.items()}
    mine = arms.get(selected) or []
    pairs: List[Tuple[Row, Row]] = []
    unmatched: List[Tuple[str, str]] = []
    for impl in sorted(arms):
        theirs = arms[impl]
        if impl == selected or is_ablation((theirs or every[impl])[-1], eval_dir):
            continue
        best = newest_shared(mine, theirs)
        if best is not None:
            pairs.append((mine[best[1]], theirs[best[0]]))
        elif mine:   # never silently skipped
            unmatched.append((impl, why_unmatched(selected, mine, theirs, every[impl])))
    return pairs, unmatched


def incomparable_rivals(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                        history: Optional[Dict[str, List[Row]]] = None) -> List[Tuple[str, str]]:
    """``(implementation, reason)`` for each rival that shares no cases and sample with ``selected``: not stale, not
    comparable. Re-run it on the selected arm's sample (``esoi run --stale`` does)."""
    return rival_pairs(rows, selected, eval_dir, history)[1]


def stale_rivals(config: Config, component: str, rows: Rows, selected: str,
                 stale: Callable[[Config, str, Row, bool], str],
                 history: Optional[Dict[str, List[Row]]] = None) -> List[Tuple[str, str]]:
    """``(implementation, reason)`` for each compared rival of ``selected`` whose row no longer counts under the strict
    rules (other cases than on disk, uncommitted code, or measured code that changed since its commit): a verdict that
    rests on it (WIN or TIE) compares the selected arm's current number with a rival's old one. A rival on another
    sample is not stale, it is not compared (``incomparable_rivals``). ``stale`` is ``stale_reasons.stale_reason``, passed in
    because it needs git and the leaderboard is the inner layer."""
    pairs, _ = rival_pairs(rows, selected, config.evaluation, history)
    return [(r["impl"], why) for _, r in pairs if (why := stale(config, component, r, True))]


def looks_between(history: Optional[Dict[str, List[Row]]], first: str, second: str, cases_sha: str) -> int:
    """How many looks two arms had at the same case file: the distinct samples (3, 10, 30 cases, the full set) both have a run of.
    A claim at one of several looks spends a share of alpha (Bonferroni over looks)."""
    if not history:
        return 1
    def samples(impl: str) -> set:
        return {(r.get("sample") or "").strip() for r in history.get(impl, []) if r.get("cases_sha") == cases_sha and not is_partial(r)}
    return max(1, len(samples(first) & samples(second)))
