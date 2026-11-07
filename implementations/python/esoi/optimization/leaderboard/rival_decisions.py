"""How each rival stands against the selected arm, by a two-sided exact test or, where no test is possible, a labelled best guess.

The rule is pragmatic and statistical. The authoritative metric is the pass rate, or the balanced score when the component sets
``[balance.<component>]``. By default the arm with the highest result on it at the latest comparable stage wins, significant or
not; the verdict states whether the lead is significant (McNemar for pass or fail per case, an exact sign test on paired balanced
scores, Holm-adjusted across the rivals at ``alpha`` 0.05 divided by the number of looks) or "best guess, not yet significant".
Without per-case rows, aggregate pass counts on the same cases and sample get Fisher's exact two-sided test. With
``[selection] holdout = F`` the leader is chosen on the selection part and every claim is computed on the held-out part alone.
Exactly equal estimates keep the selected arm. A project (``[switching]``) or a solution (``[switching.<solution id>]``) may opt
into a stricter policy (``esoi.optimization.leaderboard.switching_policy``)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import stats
from esoi.optimization.leaderboard.arm_kinds import is_ablation
from esoi.optimization.leaderboard.case_identity import comparable_with, largest_run, unverified
from esoi.optimization.leaderboard.held_out_parts import case_numbers, case_outcomes, part_of, part_row
from esoi.optimization.leaderboard.ranking import estimate, pass_rate, rank, uses_balanced
from esoi.optimization.leaderboard.results_log import Row, Rows, is_partial
from esoi.optimization.leaderboard.rival_pairing import looks_between, rival_pairs
from esoi.optimization.leaderboard.switching_policy import ALPHA, Policy


def best_guess(rows: Rows, eval_dir: Optional[Path] = None) -> Tuple[Optional[str], str]:
    """``(arm, why)``: the arm with the best point estimate among arms scored on the same cases as the largest run, labelled a best
    guess because no test was possible. Exactly equal leaders are a tie: ``(None, why)``, and nothing is selected."""
    live = {i: r for i, r in rows.items() if not is_partial(r) and not is_ablation(r, eval_dir)}
    if not live:
        return None, "no arm has a result"
    ranked = rank(comparable_with(live, largest_run(live)))
    top = [r for r in ranked if estimate(r) == estimate(ranked[0])]
    shown = ", ".join(f"{r['impl']} {pass_rate(r):.3g}" for r in ranked)
    if len(top) > 1:
        return None, f"best guess: a tie on the point estimate ({shown}); nothing is selected"
    return ranked[0]["impl"], f"best guess on the point estimate ({shown}); no test was possible"


@dataclass
class Decision:
    """How one rival stands against the selected arm. ``outcome``: ``rival`` (higher on the metric), ``incumbent`` (the selected
    arm is higher) or ``tie`` (exactly equal, or the policy requires significance and there is none; the selected arm stays).
    ``basis`` is ``significance`` (a two-sided exact test on shared cases was possible) or ``best guess`` (point estimates only).
    ``significant`` says whether the test passed. ``switch`` says whether a ``rival`` outcome replaces the selected arm."""
    rival: str
    outcome: str
    basis: str
    text: str
    own: Row
    other: Row
    p: Optional[float] = None          # Holm-adjusted two-sided p of the pair
    disagree: int = 0                  # cases where the two differ
    shared: int = 0
    switch: bool = False
    significant: bool = False          # the lead (or deficit) passed the two-sided test at the policy's alpha
    p_incumbent: Optional[float] = None   # the same two-sided p, read from the selected arm's side

    @property
    def rule(self) -> str:
        if self.basis != "significance":
            return "best guess"
        return "two-sided exact Fisher test" if "Fisher" in self.text else "two-sided paired test"


def same_cases(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> bool:
    """Whether both runs have per-case figures and over the same cases."""
    return a is not None and b is not None and a.keys() == b.keys()


def disagreements(per_case: Optional[List[Row]], own: Row, rival: Row) -> Optional[Tuple[int, int, int, str]]:
    """``(cases the rival is ahead on, cases the selected arm is ahead on, shared cases, test name)`` from per-case rows of exactly
    these two runs, or ``None``. Pass or fail per case uses McNemar's exact test; a balanced-score metric compares the scores of
    each case with the exact sign test (cases with equal scores are left out)."""
    balanced = uses_balanced(own, rival)
    read = case_numbers if balanced else case_outcomes
    a, b = read(per_case, own), read(per_case, rival)
    if not same_cases(a, b):
        return None
    if balanced:
        return (sum(round(b[c] - a[c], 9) > 0 for c in a), sum(round(b[c] - a[c], 9) < 0 for c in a), len(a), "exact sign test on per-case balanced scores")
    return (sum(b[c] and not a[c] for c in a), sum(a[c] and not b[c] for c in a), len(a), "exact McNemar test")


def has_balanced(own: Row, rival: Row) -> bool:
    """Whether either row carries a balanced score."""
    return bool(str(own.get("balanced") or rival.get("balanced") or "").strip())


def aggregate_counts(own: Row, rival: Row) -> Optional[Tuple[int, int, int, int]]:
    """``(rival passed, rival cases, selected passed, selected cases)`` when both rows are verified runs of the same cases and sample
    with pass counts and the metric is the pass rate: enough for an unpaired exact test when no per-case rows exist."""
    if unverified(own) or unverified(rival) or uses_balanced(own, rival) or has_balanced(own, rival):
        return None
    try:
        counts = (int(float(rival["passed"])), int(float(rival["cases"])), int(float(own["passed"])), int(float(own["cases"])))
    except (KeyError, ValueError):
        return None
    return counts if counts[1] > 0 and counts[3] > 0 and 0 <= counts[0] <= counts[1] and 0 <= counts[2] <= counts[3] else None


def decisions(rows: Rows, selected: str, eval_dir: Optional[Path] = None, history: Optional[Dict[str, List[Row]]] = None,
              per_case: Optional[List[Row]] = None, policy: Optional[Policy] = None) -> List[Decision]:
    """One ``Decision`` per rival scored on the same cases as ``selected``, on the solution's authoritative metric.

    The test is two-sided and exact (the direction is read from the data, so it is not tested one-sided) and says whether a lead is significant: its Holm-adjusted p-value (across the rivals) is below
    ``policy.alpha`` (default 0.05). With per-case rows for both arms the test is paired (McNemar for pass or fail per case, a
    sign test on per-case balanced scores). With only aggregate pass counts on the same cases and sample it is Fisher's exact test on
    the 2 by 2 table of passed and failed cases. Otherwise (a balanced aggregate, a figure with no case count) the point estimates are
    compared and labelled a best guess. A higher rival replaces the selected arm by default, its text saying whether the lead is
    significant or "best guess, not yet significant"; with ``policy.require_significance`` only a significant lead replaces it.
    Exactly equal estimates keep the selected arm."""
    policy = policy or Policy()
    pairs = rival_pairs(rows, selected, eval_dir, history)[0]
    if policy.holdout:   # claims rest on the held-out part alone; a pair with no per-case rows has no held-out part and is a best guess on its whole set
        pairs = [held_out_pair(per_case, own, rival, policy.holdout) for own, rival in pairs]
    tested = [exact_test_of(per_case, own, rival, selected, policy) for own, rival in pairs]   # (own, rival, p rival better, p selected better, differ, shared, test, evidence)
    better = iter(stats.holm([t[2] for t in tested if t[2] is not None]))
    worse = iter(stats.holm([t[3] for t in tested if t[3] is not None]))
    out: List[Decision] = []
    for own, rival, raw, _, differ, shared, test, counted in tested:
        if raw is None:
            out.append(untested_decision(own, rival, selected, policy))
            continue
        p, q = next(better), next(worse)
        looks = looks_between(history, selected, rival["impl"], own.get("cases_sha", ""))
        alpha = stats.bonferroni_alpha(policy.alpha, looks)
        if looks > 1:
            counted += f"; one of {looks} looks, alpha {alpha:.3g}"
        decision = tested_decision(own, rival, selected, policy, (p, q, alpha), (differ, shared, test, counted))
        decision.p_incumbent = q
        out.append(decision)
    return out


def held_out_pair(per_case: Optional[List[Row]], own: Row, rival: Row, holdout: float) -> Tuple[Row, Row]:
    """The held-out parts of a pair, or the whole rows when either has no held-out part."""
    a, b = part_row(per_case, own, holdout, True), part_row(per_case, rival, holdout, True)
    return (a, b) if a is not None and b is not None else (own, rival)


def exact_test_of(per_case: Optional[List[Row]], own: Row, rival: Row, selected: str, policy: Policy) -> tuple:
    """The exact test of one pair: paired when per-case rows exist, else Fisher on the pass counts, else no test (p values None)."""
    found = disagreements(per_case, own, rival) if not policy.holdout or part_of(own) else None
    if found is not None:
        ahead, behind, shared, test = found
        two = stats.mcnemar_exact(ahead, behind)   # two-sided: a direction picked from the data is not tested one-sided
        return (own, rival, two, two, ahead + behind, shared, test.replace("exact", "two-sided exact"), f"{ahead + behind} of {shared} cases disagree")
    agg = aggregate_counts(own, rival) if not policy.holdout else None
    if agg is None:
        return (own, rival, None, None, 0, 0, "", "")
    xr, nr, xo, no = agg
    two = stats.fisher_exact_two_sided(xr, nr, xo, no)
    return (own, rival, two, two, 0, min(nr, no), "two-sided exact Fisher test on the pass counts (no per-case rows)",
            f"{rival['impl']} passed {xr} of {nr}, {selected} {xo} of {no}")


def untested_decision(own: Row, rival: Row, selected: str, policy: Policy) -> Decision:
    """No test is possible: the point estimates decide, labelled a best guess."""
    name = rival["impl"]
    mine, theirs = estimate(own), estimate(rival)
    figures = f"{name} {pass_rate(rival):.3g} against {selected} {pass_rate(own):.3g}"
    note = f"best guess, not yet significant: {figures} on the point estimate; no case counts or per-case rows allow a test"
    if theirs > mine and policy.require_significance:
        return Decision(name, "rival", "best guess", note + f"; the {policy.source('require_significance')} requires significance, so {selected} stays", own, rival)
    if theirs > mine:
        return Decision(name, "rival", "best guess", note, own, rival, switch=True)
    if mine > theirs:
        return Decision(name, "incumbent", "best guess", note, own, rival)
    return Decision(name, "tie", "best guess", note + f"; exactly equal, so {selected} stays", own, rival)


def lead_not_shown_reason(policy: Policy, enough: bool, shared: int, p: float) -> str:
    """Why a lead that must be significant does not replace the selected arm."""
    if not enough:
        return f"the {policy.source('min_cases')} requires at least {policy.min_cases} shared cases and there are {shared}"
    if p < ALPHA:
        return f"it is significant at alpha {ALPHA:g} but the {policy.source('alpha')} requires alpha {policy.alpha:g}"
    return f"the {policy.source('require_significance')} requires a significant lead"


def tested_decision(own: Row, rival: Row, selected: str, policy: Policy, levels: Tuple[float, float, float], detail: Tuple[int, int, str, str]) -> Decision:
    """The decision for a pair that has a test: ``levels`` are (p rival better, p selected better, alpha), ``detail`` (differ, shared, test, evidence)."""
    p, q, alpha = levels
    differ, shared, test, counted = detail
    name = rival["impl"]
    mine, theirs = estimate(own), estimate(rival)
    figures = f"{name} {pass_rate(rival):.3g} against {selected} {pass_rate(own):.3g}"
    args = (own, rival, p, differ, shared)
    enough = shared >= policy.min_cases
    if theirs > mine and p < alpha and enough:
        return Decision(name, "rival", "significance", f"{name} is better than {selected} ({test}, Holm-adjusted p={p:.3g}, {counted})",
                        *args, switch=True, significant=True)
    if theirs > mine and not policy.require_significance:
        lead = f"{name} leads {selected} ({figures}; {test}, Holm-adjusted p={p:.3g}, {counted})"
        why = f"; {policy.source('min_cases')} asks for {policy.min_cases} shared cases and there are {shared}" if not enough else ""
        return Decision(name, "rival", "significance", f"best guess, not yet significant: {lead}; more cases would settle it{why}", *args, switch=True)
    if theirs > mine:
        return Decision(name, "tie", "significance", f"{name} is not shown better than {selected} (p={p:.3g}, {counted}); more cases "
                        f"would settle it: {lead_not_shown_reason(policy, enough, shared, p)}, so {selected} stays", *args)
    if q < alpha:
        return Decision(name, "incumbent", "significance", f"{selected} is better than {name} ({test}, Holm-adjusted p={q:.3g}, {counted})", *args, significant=True)
    if mine > theirs:
        return Decision(name, "incumbent", "significance", f"{selected} leads {name} ({figures}; best guess, not yet significant, {test}, "
                        f"Holm-adjusted p={q:.3g}, {counted})", *args)
    return Decision(name, "tie", "significance", f"{name} is exactly equal to {selected} on the metric ({figures}), so {selected} stays", *args)


def challengers(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                history: Optional[Dict[str, List[Row]]] = None, per_case: Optional[List[Row]] = None,
                policy: Optional[Policy] = None) -> List[Row]:
    """Rival rows that should replace the selected arm (see ``decisions``). A rival on other cases is skipped, and an ablation or
    validity arm is never a challenger."""
    return [d.other for d in decisions(rows, selected, eval_dir, history, per_case, policy) if d.outcome == "rival" and d.switch]
