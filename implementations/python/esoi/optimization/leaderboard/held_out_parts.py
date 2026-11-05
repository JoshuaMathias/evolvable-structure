"""The selection part and held-out part of a case set: per-case outcomes of a run, and rows restricted to one part so a claim is computed on cases the choice never saw."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import stats
from esoi.optimization.leaderboard.arm_kinds import is_ablation
from esoi.optimization.leaderboard.case_identity import comparable, unverified
from esoi.optimization.leaderboard.ranking import estimate, rank
from esoi.optimization.leaderboard.results_log import Row, Rows, is_partial
from esoi.optimization.leaderboard.switching_policy import Policy


def part_of(row: Row) -> str:
    """``"selection"`` or ``"heldout"`` for a row made by ``part_row``, else ``""`` (the whole case set)."""
    return (row.get("part") or "").strip()


def part_row(per_case: Optional[List[Row]], row: Row, fraction: float, heldout: bool) -> Optional[Row]:
    """A copy of a results row restricted to the selection part or the held-out part of its cases (``stats.in_heldout``), with the
    case count and pass count of that part, or ``None`` when the per-case log does not hold exactly that run. Cost and calls stay
    those of the whole run; the row is marked with ``part`` so the tests read only that part."""
    found = case_outcomes(per_case, row)
    if found is None:
        return None
    mine = {c: ok for c, ok in found.items() if stats.in_heldout(c, fraction) == heldout}
    out = dict(row)
    out.update({"cases": str(len(mine)), "passed": str(sum(mine.values())), "part": "heldout" if heldout else "selection",
                "split": f"{fraction:g}", "balanced": "", "balanced_all": row.get("balanced", ""), "cases_all": row.get("cases", ""), "passed_all": row.get("passed", "")})
    return out


def whole_row(row: Row) -> Row:
    """The results row a ``part_row`` was made from (its whole case set again)."""
    if not part_of(row):
        return row
    out = {k: v for k, v in row.items() if k not in ("part", "split", "cases_all", "passed_all", "balanced_all")}
    out.update({"cases": row.get("cases_all", ""), "passed": row.get("passed_all", ""), "balanced": row.get("balanced_all", "")})
    return out


def selection_view(history: Dict[str, List[Row]], per_case: Optional[List[Row]], policy: Policy) -> Tuple[Dict[str, List[Row]], Policy]:
    """``(history, policy)`` to choose a leader with: with a holdout, every run restricted to the selection part of its cases (a run the
    per-case log cannot split is left out) and the policy without the holdout, since the choice is made on that part; without one, the
    history and policy as given."""
    if not policy.holdout:
        return history, policy
    part = {impl: [p for r in rs if (p := part_row(per_case, r, policy.holdout, False)) is not None] for impl, rs in history.items()}
    return {impl: rs for impl, rs in part.items() if rs}, Policy(policy.alpha, policy.min_cases, policy.require_stage,
                                                                  policy.require_significance, policy.origin, 0.0)


def selection_leader(rows: Rows, per_case: Optional[List[Row]], fraction: float, selected: str, eval_dir: Optional[Path] = None) -> Optional[str]:
    """The arm with the highest result on the selection part of the cases the selected arm was scored on (the standing rule applied to
    that part: an exact tie keeps ``selected``), or ``None`` when the selected arm has no per-case rows to split."""
    parts = {impl: part_row(per_case, r, fraction, False) for impl, r in rows.items() if not is_partial(r) and not is_ablation(r, eval_dir)}
    parts = {impl: p for impl, p in parts.items() if p is not None}
    own = parts.get(selected)
    if own is None:
        return None
    same = {impl: p for impl, p in parts.items() if comparable(p, own)}
    best = max(estimate(p) for p in same.values())
    top = {impl: p for impl, p in same.items() if estimate(p) == best}
    return selected if selected in top else rank(top)[0]["impl"]


def case_outcomes(per_case: Optional[List[Row]], row: Row) -> Optional[Dict[str, bool]]:
    """``{case id: passed}`` of the run a results row summarises, or ``None`` when the per-case log does not hold exactly that
    run (no rows, another count, or another pass total: the log keeps the newest run of a sample, the row may be older)."""
    if not per_case or unverified(row):
        return None
    sample = (row.get("sample") or "").strip()
    found = {r["case_id"]: stats.passed(r.get("ok")) for r in per_case
             if r.get("component") == row.get("component") and r.get("impl") == row.get("impl")
             and r.get("cases_sha") == row.get("cases_sha") and (r.get("sample") or "").strip() == sample}
    if part_of(row):   # a part of the run: the cases of that part must be all the row counts
        found = {c: ok for c, ok in found.items() if stats.in_heldout(c, float(row.get("split") or 0)) == (part_of(row) == "heldout")}
    try:
        total, passed = int(float(row.get("cases") or 0)), int(float(row.get("passed") or 0))
    except ValueError:
        return None
    return found if found and len(found) == total and sum(found.values()) == passed else None


def case_numbers(per_case: Optional[List[Row]], row: Row) -> Optional[Dict[str, float]]:
    """``{case id: balanced score of that case}`` for a run whose authoritative metric is the balanced score, or ``None`` when the
    per-case log holds no complete set of scores for exactly that run."""
    if case_outcomes(per_case, row) is None:
        return None
    sample = (row.get("sample") or "").strip()
    found: Dict[str, float] = {}
    for r in per_case or []:
        if (r.get("component"), r.get("impl"), r.get("cases_sha"), (r.get("sample") or "").strip()) == \
                (row.get("component"), row.get("impl"), row.get("cases_sha"), sample):
            if part_of(row) and stats.in_heldout(r["case_id"], float(row.get("split") or 0)) != (part_of(row) == "heldout"):
                continue
            try:
                found[r["case_id"]] = float(r.get("score") or "")
            except ValueError:
                return None
    return found
