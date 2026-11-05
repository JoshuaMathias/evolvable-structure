"""The statistics behind choosing an implementation by its metric, standard library only.

Three standard tools, each small enough to check by hand:

* ``wilson_interval(passed, cases)``: the Wilson score interval for a pass rate (95% by default). It stays inside 0 to 1 and
  behaves for small counts and for rates near 0 or 1, where the plain "rate plus or minus" interval does not.
* ``mcnemar_exact(only_a, only_b)``: the exact two-sided McNemar test for two arms scored on the same cases. Only the cases
  where they disagree carry information; under "neither arm is better" each disagreement goes either way with probability one
  half, so the p-value is a binomial tail on the disagreements.
* ``sign_test_greater(wins, losses)``: the exact one-sided sign test, the question the leaderboard asks ("is this arm better?").
  McNemar's test for pass or fail per case and the sign test on paired per-case score differences are the same binomial tail.
* ``fisher_exact_greater(passed_a, cases_a, passed_b, cases_b)``: the exact one-sided Fisher test on two arms' aggregate pass counts, for
  when only totals exist (unpaired, so weaker than the paired test, but still a test).
* ``fisher_exact_two_sided``, ``bonferroni_alpha``, ``in_heldout`` and ``split_cases``: the two-sided unpaired test for totals only, the
  alpha one of several looks at the same pair may spend, and the deterministic selection and held-out parts of a case set (a hash of
  the case id, so a case never changes part when cases are added).
* ``holm(p_values)``: Holm's correction, which keeps the chance of any false lead below the stated level when one arm is
  compared with several rivals.

``paired_comparison`` joins them for two arms' per-case rows and ``describe`` turns the result into one plain sentence.
No model, no network, no third-party package.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fractions import Fraction
from math import comb
from statistics import NormalDist
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

ALPHA = 0.05


def wilson_interval(passed: int, cases: int, confidence: float = 0.95) -> Tuple[float, float]:
    """``(low, high)`` Wilson score interval of ``passed`` out of ``cases``. Zero cases gives ``(0.0, 1.0)``: nothing is known."""
    if cases < 0 or passed < 0 or passed > cases:
        raise ValueError(f"{passed} passed of {cases} cases is not a count")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if cases == 0:
        return 0.0, 1.0
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = passed / cases
    denominator = 1 + z * z / cases
    centre = (p + z * z / (2 * cases)) / denominator
    half = z * ((p * (1 - p) / cases + z * z / (4 * cases * cases)) ** 0.5) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Exact two-sided McNemar p-value from the two disagreement counts (cases only A passed, cases only B passed). With no
    disagreement at all the arms are indistinguishable and the p-value is 1."""
    if only_a < 0 or only_b < 0:
        raise ValueError("counts cannot be negative")
    n = only_a + only_b
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(only_a, only_b) + 1))
    return float(min(Fraction(1), Fraction(2 * tail, 2 ** n)))


def sign_test_greater(wins: int, losses: int) -> float:
    """Exact one-sided p-value that the arm with ``wins`` cases ahead is better than the one with ``losses`` cases ahead:
    the chance of at least ``wins`` heads in ``wins + losses`` fair coin flips. Cases that tie are left out by the caller; with
    no disagreement at all the answer is 1."""
    if wins < 0 or losses < 0:
        raise ValueError("counts cannot be negative")
    n = wins + losses
    if n == 0:
        return 1.0
    return float(Fraction(sum(comb(n, i) for i in range(wins, n + 1)), 2 ** n))


def fisher_exact_greater(passed_a: int, cases_a: int, passed_b: int, cases_b: int) -> float:
    """Exact one-sided p-value that arm A's true pass rate is higher than arm B's, from the 2 by 2 table of passed and failed cases
    (the hypergeometric tail: given the total passes, the chance A holds at least ``passed_a`` of them)."""
    if min(passed_a, cases_a - passed_a, passed_b, cases_b - passed_b) < 0:
        raise ValueError("pass counts must lie between 0 and the number of cases")
    total, passes = cases_a + cases_b, passed_a + passed_b
    if total == 0:
        return 1.0
    tail = sum(comb(cases_a, k) * comb(cases_b, passes - k) for k in range(passed_a, min(cases_a, passes) + 1))
    return float(min(Fraction(1), Fraction(tail, comb(total, passes))))


def fisher_exact_two_sided(passed_a: int, cases_a: int, passed_b: int, cases_b: int) -> float:
    """Exact two-sided Fisher p-value on the 2 by 2 table of passed and failed cases: the total probability of the tables at most as
    likely as the one seen, given the margins."""
    if min(passed_a, cases_a - passed_a, passed_b, cases_b - passed_b) < 0:
        raise ValueError("pass counts must lie between 0 and the number of cases")
    total, passes = cases_a + cases_b, passed_a + passed_b
    if total == 0:
        return 1.0
    denominator = comb(total, passes)
    seen = comb(cases_a, passed_a) * comb(cases_b, passes - passed_a)
    tail = sum(w for k in range(max(0, passes - cases_b), min(cases_a, passes) + 1)
               if (w := comb(cases_a, k) * comb(cases_b, passes - k)) <= seen)
    return float(min(Fraction(1), Fraction(tail, denominator)))


def bonferroni_alpha(alpha: float, looks: int) -> float:
    """The alpha one claim may spend when it is one of ``looks`` looks at the same pair (stages run at 3, 10 and 30 cases are three looks)."""
    return alpha / max(1, int(looks))


def in_heldout(case_id: str, fraction: float) -> bool:
    """Whether a case belongs to the held-out part: a hash of its id decides, so the split is the same on every machine and run."""
    if fraction <= 0:
        return False
    digest = hashlib.sha256(str(case_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2 ** 64 < fraction


def split_cases(case_ids: Iterable[str], fraction: float) -> Tuple[List[str], List[str]]:
    """``(selection part, held-out part)`` of the case ids, each in the order given."""
    ids = [str(c) for c in case_ids]
    return [c for c in ids if not in_heldout(c, fraction)], [c for c in ids if in_heldout(c, fraction)]


def holm(p_values: List[float]) -> List[float]:
    """Holm-adjusted p-values, in the order given: the smallest is multiplied by the number of tests, the next by one fewer, and
    so on, never decreasing and capped at 1."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted


@dataclass(frozen=True)
class Paired:
    """Two arms scored on the same cases."""
    both: int
    only_a: int
    only_b: int
    neither: int
    p_value: float
    skipped: int = 0   # cases only one arm has a row for, left out

    @property
    def cases(self) -> int:
        return self.both + self.only_a + self.only_b + self.neither

    @property
    def passed_a(self) -> int:
        return self.both + self.only_a

    @property
    def passed_b(self) -> int:
        return self.both + self.only_b

    @property
    def p_a_better(self) -> float:
        return sign_test_greater(self.only_a, self.only_b)

    @property
    def p_b_better(self) -> float:
        return sign_test_greater(self.only_b, self.only_a)


def passed(value: Any) -> bool:
    """A per-case ``ok`` cell or flag read as pass or fail (``"1"``, ``"true"``, ``True``)."""
    return str(value).strip().lower() in ("1", "true", "yes", "pass", "passed")


Outcomes = Union[Mapping[str, Any], Iterable[Mapping[str, Any]]]


def outcomes_of(rows: Outcomes) -> Dict[str, bool]:
    """``{case id: passed}`` from a mapping, or from per-case rows with ``case_id`` (or ``id``) and ``ok``."""
    if isinstance(rows, Mapping):
        return {str(k): passed(v) for k, v in rows.items()}
    return {str(r.get("case_id", r.get("id"))): passed(r.get("ok")) for r in rows}


def paired_counts(rows_a: Outcomes, rows_b: Outcomes) -> Paired:
    """The 2 by 2 counts and the exact McNemar p-value for two arms' per-case rows, on the cases both have."""
    a, b = outcomes_of(rows_a), outcomes_of(rows_b)
    shared = [c for c in a if c in b]
    both = sum(a[c] and b[c] for c in shared)
    only_a = sum(a[c] and not b[c] for c in shared)
    only_b = sum(b[c] and not a[c] for c in shared)
    return Paired(both, only_a, only_b, len(shared) - both - only_a - only_b, mcnemar_exact(only_a, only_b),
                  skipped=len(set(a) ^ set(b)))


def describe(result: Paired, name_a: str = "A", name_b: str = "B", adjusted: Optional[float] = None, alpha: float = ALPHA) -> str:
    """One plain sentence for a pairing. ``adjusted`` is the Holm-adjusted p-value when several rivals were compared."""
    p = result.p_value if adjusted is None else adjusted
    label = "p" if adjusted is None else "Holm-adjusted p"
    head = (f"On {result.cases} shared cases, {name_a} passed {result.only_a} that {name_b} missed and {name_b} passed "
            f"{result.only_b} that {name_a} missed ({result.both} both passed, {result.neither} neither)")
    if result.only_a == result.only_b:
        verdict = "no difference in cases passed"
    else:
        better, worse = (name_a, name_b) if result.only_a > result.only_b else (name_b, name_a)
        verdict = (f"{better} passed more cases than {worse}, and that gap is larger than chance would explain" if p < alpha
                   else f"{better} passed more cases than {worse}, but a gap this size is common by chance")
    return f"{head}; exact McNemar {label} = {p:.3g}: {verdict}."
