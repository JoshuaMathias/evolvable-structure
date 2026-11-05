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


def rank(evidence: Iterable[Evidence], dimensions: Mapping[str, float], candidates: Optional[Sequence[str]] = None,
         today: Optional[datetime.date] = None, p: Params = DEFAULTS) -> Ranking:
    """Per-dimension ordered shortlists and a weighted overall. ``dimensions`` is ``{dimension: weight}``. Candidates are compared
    only on one shared basis per dimension (the measure and comparator most candidates have); the rest are listed as not comparable.
    A candidate with only vendor-side evidence (grade D) is placed below every candidate with better evidence."""
    rows = list(evidence)
    for dim in dimensions:
        if dim not in DIMENSIONS:
            raise ValueError(f"unknown dimension {dim!r}; use one of {', '.join(DIMENSIONS)}")
    found = all_estimates(rows, today, p)
    names: Dict[str, str] = {}
    for e in rows:
        names.setdefault(norm(e.candidate), e.candidate)
    asked = [norm(c) for c in candidates] if candidates else sorted(names)
    for c in (candidates or []):
        names.setdefault(norm(c), c)
    result: Dict[str, DimensionRanking] = {}
    for dim, weight in dimensions.items():
        options: Dict[Tuple[str, str], List[Estimate]] = {}
        for cand in asked:
            for est in found.get((cand, dim), []):
                options.setdefault(est.basis, []).append(est)
        have = {cand for cand in asked if (cand, dim) in found}
        best_basis = max(options, key=lambda b: (len({norm(x.candidate) for x in options[b]}),
                                                 -sum(LETTERS.index(x.grade) for x in options[b]), b), default=None)
        picked: Dict[str, Estimate] = {}
        for est in (options[best_basis] if best_basis else []):
            picked[norm(est.candidate)] = est
        skipped = [(names[c], f"no row on {basis_label(best_basis)}; its evidence is on "
                              + ", ".join(sorted(basis_label(x.basis) for x in found[(c, dim)])))
                   for c in asked if c in have and c not in picked]
        direction = x_better(picked)
        usable = sorted((x for x in picked.values() if x.grade != "D"), key=lambda x: x.value, reverse=(direction == "higher"))
        weak = sorted((x for x in picked.values() if x.grade == "D"), key=lambda x: x.value, reverse=(direction == "higher"))
        placements: List[Placement] = []
        for index, est in enumerate(usable + weak, 1):
            tied = tuple(q.candidate for q in placements
                         if q.estimate.grade != "D" and est.grade != "D" and spread(q.estimate.value, est.value) <= p.tolerance[dim])
            note = (f"grade {est.grade}: {est.value:g} {est.unit}" + (f"; flags: {', '.join(est.flags)}" if est.flags else "")
                    + ("; " + est.settle if est.needs_own_run and est.settle else ""))
            if est.grade == "D":
                note = ("provisional, placed below every candidate with better evidence: " if usable else "provisional: ") + note
            if tied:
                note += f"; within {p.tolerance[dim]:.0%} of {', '.join(tied)}, so not a real difference"
            placements.append(Placement(est.candidate, index, est, note, tied))
        result[dim] = DimensionRanking(dim, weight, basis_label(best_basis) if best_basis else "", x_better(picked) if picked else "",
                                       placements, skipped, [names[c] for c in asked if c not in have])
    total = sum(dimensions.values()) or 1.0
    overall: List[Overall] = []
    for cand in asked:
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
        overall.append(Overall(names[cand], score / total, covered / total, notes))
    overall.sort(key=lambda o: (-o.score, o.candidate))
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


def agrees_with_results(ranking: DimensionRanking, own_results: Mapping[str, float], better: str = "higher",
                        tolerance: float = 0.02) -> Agreement:
    """Does the public order of candidates match the order of our own scores? Only candidates graded better than D and present
    in ``own_results`` are compared. Two own scores within ``tolerance`` (absolute) are a tie, which neither agrees nor
    conflicts. A conflict is information: our cases differ from the public benchmark, or the public number does not hold for us;
    it never changes our result and is recorded, not raised."""
    own = {norm(k): v for k, v in own_results.items()}
    public = [q for q in ranking.ordered if q.estimate.grade != "D" and norm(q.candidate) in own]
    excluded = [f"{q.candidate}: " + ("grade D evidence is not compared" if q.estimate.grade == "D" else "")
                for q in ranking.ordered if q.estimate.grade == "D" and norm(q.candidate) in own]
    excluded += [f"{q.candidate}: no result of ours" for q in ranking.ordered if norm(q.candidate) not in own]
    pairs: List[Tuple[str, str, str]] = []
    lines: List[str] = []
    for i, a in enumerate(public):
        for b in public[i + 1:]:
            if a.candidate in b.tied_with or b.candidate in a.tied_with:
                continue
            ours = own[norm(a.candidate)] - own[norm(b.candidate)]
            if better == "lower":
                ours = -ours
            if abs(own[norm(a.candidate)] - own[norm(b.candidate)]) <= tolerance:
                pairs.append((a.candidate, b.candidate, "tie"))
                lines.append(f"{a.candidate} and {b.candidate}: public evidence prefers {a.candidate}; our scores are within {tolerance:g}, "
                             "so neither confirms nor contradicts it")
            elif ours > 0:
                pairs.append((a.candidate, b.candidate, "agree"))
                lines.append(f"{a.candidate} over {b.candidate}: public evidence (grades {a.estimate.grade}, {b.estimate.grade}) and our results agree")
            else:
                pairs.append((a.candidate, b.candidate, "conflict"))
                lines.append(f"CONFLICT {a.candidate} over {b.candidate}: public evidence (grades {a.estimate.grade}, {b.estimate.grade}) "
                             "prefers the first, our results prefer the second. Information, not an error: our cases may differ "
                             "from the benchmark's, or the public number may not hold here. Our own result stays the basis for selection")
    kinds = {kind for _, _, kind in pairs if kind != "tie"}
    verdict = "insufficient" if not kinds else "mixed" if len(kinds) > 1 else kinds.pop()
    return Agreement(ranking.dimension, verdict, pairs, excluded, lines)


def own_scores(rows: Mapping[str, Mapping[str, str]]) -> Dict[str, float]:
    """``{implementation: pass rate}`` from the newest results-log row per implementation (``leaderboard.pass_rate``)."""
    from esoi.optimization.leaderboard import ranking
    return {impl: ranking.pass_rate(dict(row)) for impl, row in rows.items()}
