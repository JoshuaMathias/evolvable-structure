"""Rank candidates per dimension from graded public evidence and compare that order with our own recorded scores."""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading import Estimate, all_estimates, basis_label, spread
from esoi.optimization.when_metrics_are_run.public_evidence.evidence_records import DIMENSIONS, Evidence, LETTERS, norm
from esoi.optimization.when_metrics_are_run.public_evidence.grading_table import DEFAULTS, Params


@dataclass
class Placement:
    candidate: str
    rank: int
    estimate: Estimate
    reason: str
    tied_with: Tuple[str, ...] = ()


@dataclass
class DimensionRanking:
    dimension: str
    weight: float
    basis: str
    better: str
    ordered: List[Placement]
    not_comparable: List[Tuple[str, str]]
    no_evidence: List[str]

    def agrees_with_results(self, own_results: Mapping[str, float], better: str = "higher", tolerance: float = 0.02) -> "Agreement":
        return agrees_with_results(self, own_results, better, tolerance)


@dataclass
class Overall:
    candidate: str
    score: float
    covered: float
    notes: List[str]


@dataclass
class Ranking:
    dimensions: Dict[str, DimensionRanking]
    overall: List[Overall]

    def agrees_with_results(self, own_results: Mapping[str, float], dimension: str = "", better: str = "higher",
                            tolerance: float = 0.02) -> "Agreement":
        """Compare one dimension (default: the heaviest) with our own recorded scores, ``{candidate: score}``."""
        chosen = dimension or max(self.dimensions, key=lambda d: self.dimensions[d].weight)
        return agrees_with_results(self.dimensions[chosen], own_results, better, tolerance)


def shared_basis_estimates(asked: Sequence[str], found: Mapping, dim: str) -> Tuple[Optional[Tuple[str, str]], Dict[str, Estimate]]:
    """The basis most candidates have on a dimension (more candidates, then better grades) and each candidate's estimate on it."""
    options: Dict[Tuple[str, str], List[Estimate]] = {}
    for cand in asked:
        for est in found.get((cand, dim), []):
            options.setdefault(est.basis, []).append(est)
    best_basis = max(options, key=lambda b: (len({norm(x.candidate) for x in options[b]}),
                                             -sum(LETTERS.index(x.grade) for x in options[b]), b), default=None)
    return best_basis, {norm(est.candidate): est for est in (options[best_basis] if best_basis else [])}


def place_candidates(picked: Mapping[str, Estimate], dim: str, p: Params) -> List[Placement]:
    """The candidates in order, grade D ones after the rest, each with a note and the candidates it is within tolerance of."""
    direction = x_better(picked)
    usable = sorted((x for x in picked.values() if x.grade != "D"), key=lambda x: x.value, reverse=(direction == "higher"))
    weak = sorted((x for x in picked.values() if x.grade == "D"), key=lambda x: x.value, reverse=(direction == "higher"))
    placements: List[Placement] = []
    for index, est in enumerate(usable + weak, 1):
        tied = tuple(q.candidate for q in placements
                     if q.estimate.grade != "D" and est.grade != "D" and spread(q.estimate.value, est.value) <= p.tolerance[dim])
        placements.append(Placement(est.candidate, index, est, placement_note(est, bool(usable), tied, p.tolerance[dim]), tied))
    return placements


def placement_note(est: Estimate, others_usable: bool, tied: Tuple[str, ...], tolerance: float) -> str:
    """The note on one placement: the grade and figure, flags, how to settle it, whether it is provisional and whom it ties with."""
    note = (f"grade {est.grade}: {est.value:g} {est.unit}" + (f"; flags: {', '.join(est.flags)}" if est.flags else "")
            + ("; " + est.settle if est.needs_own_run and est.settle else ""))
    if est.grade == "D":
        note = ("provisional, placed below every candidate with better evidence: " if others_usable else "provisional: ") + note
    if tied:
        note += f"; within {tolerance:.0%} of {', '.join(tied)}, so not a real difference"
    return note


def rank_dimension(dim: str, weight: float, asked: Sequence[str], names: Mapping[str, str], found: Mapping, p: Params) -> DimensionRanking:
    """The shortlist of one dimension on its shared basis, with who was skipped (other basis) and who has no evidence."""
    best_basis, picked = shared_basis_estimates(asked, found, dim)
    have = {cand for cand in asked if (cand, dim) in found}
    skipped = [(names[c], f"no row on {basis_label(best_basis)}; its evidence is on "
                          + ", ".join(sorted(basis_label(x.basis) for x in found[(c, dim)])))
               for c in asked if c in have and c not in picked]
    return DimensionRanking(dim, weight, basis_label(best_basis) if best_basis else "", x_better(picked) if picked else "",
                            place_candidates(picked, dim, p), skipped, [names[c] for c in asked if c not in have])


def overall_of(cand: str, name: str, dimensions: Mapping[str, float], result: Mapping[str, DimensionRanking], p: Params, total: float) -> Overall:
    """One candidate's weighted overall score across the dimensions it has comparable evidence on."""
    score, covered, notes = 0.0, 0.0, []
    for dim, weight in dimensions.items():
        place = next((q for q in result[dim].ordered if norm(q.candidate) == cand), None)
        if place is None:
            notes.append(f"{dim}: no comparable evidence")
            continue
        count = len(result[dim].ordered)
        position = 1.0 if count == 1 else 1 - (place.rank - 1) / (count - 1)
        confidence = p.confidence[place.estimate.grade]
        score += weight * position * confidence
        covered += weight * (confidence > 0)
        notes.append(f"{dim}: rank {place.rank} of {count}, grade {place.estimate.grade}")
    return Overall(name, score / total, covered / total, notes)


def candidate_names(rows: List[Evidence], candidates: Optional[Sequence[str]]) -> Tuple[Dict[str, str], List[str]]:
    """``(display name per normalised candidate, the candidates asked for)``; all candidates of the rows when none are named."""
    names: Dict[str, str] = {}
    for name in [e.candidate for e in rows]:
        names.setdefault(norm(name), name)
    asked = [norm(c) for c in candidates] if candidates else sorted(names)
    for c in (candidates or []):
        names.setdefault(norm(c), c)
    return names, asked


def rank(evidence: Iterable[Evidence], dimensions: Mapping[str, float], candidates: Optional[Sequence[str]] = None,
         today: Optional[datetime.date] = None, p: Params = DEFAULTS) -> Ranking:
    """Per-dimension ordered shortlists and a weighted overall. ``dimensions`` is ``{dimension: weight}``. Candidates are compared
    only on one shared basis per dimension (the measure and comparator most candidates have); the rest are listed as not comparable.
    A candidate with only vendor-side evidence (grade D) is placed below every candidate with better evidence."""
    rows = list(evidence)
    unknown = [dim for dim in dimensions if dim not in DIMENSIONS]
    if unknown:
        raise ValueError(f"unknown dimension {unknown[0]!r}; use one of {', '.join(DIMENSIONS)}")
    found = all_estimates(rows, today, p)
    names, asked = candidate_names(rows, candidates)
    result = {dim: rank_dimension(dim, weight, asked, names, found, p) for dim, weight in dimensions.items()}
    total = sum(dimensions.values()) or 1.0
    overall = sorted((overall_of(cand, names[cand], dimensions, result, p, total) for cand in asked), key=lambda o: (-o.score, o.candidate))
    return Ranking(result, overall)


def x_better(picked: Mapping[str, Estimate]) -> str:
    return next(iter(picked.values())).better if picked else "higher"


@dataclass
class Agreement:
    """A public ranking set against our own recorded scores. ``verdict``: agree, conflict, mixed, or insufficient."""
    dimension: str
    verdict: str
    pairs: List[Tuple[str, str, str]]       # (better publicly, other, "agree" | "conflict" | "tie")
    excluded: List[str]
    lines: List[str]


def judge_pair(a: Placement, b: Placement, gap: float, better: str, tolerance: float) -> Tuple[str, str]:
    """Whether our scores agree with the public order of ``a`` over ``b`` (``gap`` is our score of a minus b): ``(kind, line)``."""
    ours = -gap if better == "lower" else gap
    if abs(gap) <= tolerance:
        return "tie", (f"{a.candidate} and {b.candidate}: public evidence prefers {a.candidate}; our scores are within {tolerance:g}, "
                       "so neither confirms nor contradicts it")
    if ours > 0:
        return "agree", f"{a.candidate} over {b.candidate}: public evidence (grades {a.estimate.grade}, {b.estimate.grade}) and our results agree"
    return "conflict", (f"CONFLICT {a.candidate} over {b.candidate}: public evidence (grades {a.estimate.grade}, {b.estimate.grade}) "
                        "prefers the first, our results prefer the second. Information, not an error: our cases may differ "
                        "from the benchmark's, or the public number may not hold here. Our own result stays the basis for selection")


def agrees_with_results(ranking: DimensionRanking, own_results: Mapping[str, float], better: str = "higher",
                        tolerance: float = 0.02) -> Agreement:
    """Does the public order of candidates match the order of our own scores? Only candidates graded better than D and present
    in ``own_results`` are compared. Two own scores within ``tolerance`` (absolute) are a tie, which neither agrees nor
    conflicts. A conflict is information: our cases differ from the public benchmark, or the public number does not hold for us;
    it never changes our result and is recorded, not raised."""
    own = {norm(k): v for k, v in own_results.items()}
    public = [q for q in ranking.ordered if q.estimate.grade != "D" and norm(q.candidate) in own]
    excluded = [f"{q.candidate}: grade D evidence is not compared" for q in ranking.ordered if q.estimate.grade == "D" and norm(q.candidate) in own]
    excluded += [f"{q.candidate}: no result of ours" for q in ranking.ordered if norm(q.candidate) not in own]
    pairs, lines = compare_public_order(public, own, better, tolerance)
    kinds = {kind for _, _, kind in pairs if kind != "tie"}
    verdict = "insufficient" if not kinds else "mixed" if len(kinds) > 1 else kinds.pop()
    return Agreement(ranking.dimension, verdict, pairs, excluded, lines)


def compare_public_order(public: List[Placement], own: Mapping[str, float], better: str, tolerance: float) -> Tuple[List[Tuple[str, str, str]], List[str]]:
    """``(pairs, lines)``: every pair of publicly ordered candidates that is not a tie in the public order, judged against our scores."""
    pairs: List[Tuple[str, str, str]] = []
    lines: List[str] = []
    for i, a in enumerate(public):
        for b in public[i + 1:]:
            if a.candidate in b.tied_with or b.candidate in a.tied_with:
                continue
            kind, line = judge_pair(a, b, own[norm(a.candidate)] - own[norm(b.candidate)], better, tolerance)
            pairs.append((a.candidate, b.candidate, kind))
            lines.append(line)
    return pairs, lines


def own_scores(rows: Mapping[str, Mapping[str, str]]) -> Dict[str, float]:
    """``{implementation: pass rate}`` from the newest results-log row per implementation (``leaderboard.pass_rate``)."""
    from esoi.optimization.leaderboard import ranking
    return {impl: ranking.pass_rate(dict(row)) for impl, row in rows.items()}
