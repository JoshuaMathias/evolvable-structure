"""Public evidence: grade what others measured, so it complements our own results and never replaces them.

Outside evals of a model, a library or a tool (a public benchmark, a replication, a paper, a vendor's launch post, a maintainer's
benchmark page, a forum report) say something about token efficiency, speed, quality, cost and reliability that a small private
test cannot. They are also easy to over-read: one number is one number, a vendor measured its own product, a benchmark everyone
tops no longer separates anything, and a harness difference looks like a model difference. This module reads such evidence from a
CSV and judges it the way a careful scientist would, with no model call: every grade is computed from the columns below by the
visible table ``DEFAULTS`` (each weight has its reason in ``REASONS``).

The record: one CSV row per reported number, columns ``COLUMNS``::

    evidence_id, candidate, dimension, measure, value, unit, better, comparator, source_url, source_kind,
    run_by_independent, method_disclosed, n, benchmark_status, date_published, date_checked, confounds, note

``load`` and ``parse_text`` check every row and raise ``EvidenceError`` listing every problem (line, column, what to write); no
row is dropped silently.

The grade of one (candidate, dimension) pair, an ``Estimate``:

1. Rows are grouped by *basis*: the same measure on the same comparator. Different bases are never merged; units inside a basis
   convert only through ``UNITS`` and otherwise raise the flag ``unit_mismatch``.
2. Each row scores points (source kind, independence, method disclosed, sample size, benchmark status, age, named confounds);
   the best row's points give a letter A to D.
3. The letter is capped by what the sources are: only vendor-side rows (vendor or maintainer reported, or not run by anyone
   independent) is ``vendor_only`` and at most D; no independent row at all is at most C; one distinct source is
   ``single_source`` and at most B.
4. Two or more independent sources that agree within the dimension's tolerance raise it one letter; two rows that disagree
   beyond it (``contradicts``, both rows named) lower it one letter.

``needs_own_run`` is true when the letter is below ``DEFAULTS.needs_grade`` or a flag in ``DEFAULTS.blocking`` is raised, and
``settle`` says what one run of ours would settle it. ``rank`` orders candidates per dimension on one shared basis: a candidate
with only vendor-side evidence is placed below every candidate with independent evidence, whatever its number. ``agrees_with_results``
compares a ranking with our own recorded scores; a conflict is information about our cases or the public benchmark, not an error.

Standard library only. The cascade shows the graded line per implementation (``esoi cascade``) and ``esoi evidence`` lists,
grades and ranks the records."""
from __future__ import annotations

import datetime
import statistics
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from esoi import implementation, solution
from esoi.optimization.when_metrics_are_run.public_evidence.evidence_records import Evidence, FLAGS, LETTERS, norm
from esoi.optimization.when_metrics_are_run.public_evidence.grading_table import DEFAULTS, Params, UNIT_FAMILY


def convert(value: float, unit: str) -> Tuple[float, str]:
    """``(value in the family's base unit, base unit)``; an unlisted unit is its own base."""
    key = unit.strip().lower()
    if key in UNIT_FAMILY:
        _, base, factor = UNIT_FAMILY[key]
        return value * factor, base
    return value, unit.strip()


def age_days(e: Evidence, today: datetime.date) -> Optional[int]:
    published = e.date_published
    return (today - published).days if published else None


def row_points(e: Evidence, today: datetime.date, p: Params = DEFAULTS) -> Tuple[int, List[str]]:
    """Points of one row (0 to 10) and the parts, so a grade can be explained."""
    parts: List[Tuple[str, int]] = [("kind " + e.source_kind, p.kind[e.source_kind]),
                                    ("independence " + e.run_by_independent, p.independence[e.run_by_independent]),
                                    ("method " + e.method_disclosed, p.method[e.method_disclosed])]
    parts.append((f"n={e.n}" if e.n else "n unstated", next((pts for floor, pts in p.sample_steps if e.n and e.n >= floor), 0)))
    parts.append(("benchmark " + e.benchmark_status, p.status[e.benchmark_status]))
    stale = p.stale_days[e.dimension]
    days = age_days(e, today)
    if days is None:
        parts.append(("undated", p.undated))
    elif days > stale:
        parts.append((f"{days} days old", p.stale_penalty))
    elif days > stale / 2:
        parts.append((f"{days} days old", p.half_age_penalty))
    if e.confounds:
        parts.append(("confound named", max(p.confound_floor, p.confound_penalty * len(e.confounds))))
    return sum(points for _, points in parts), [f"{label} {points:+d}" for label, points in parts if points]


def letter_for(points: int, p: Params = DEFAULTS) -> str:
    a, b, c = p.cuts
    return "A" if points >= a else "B" if points >= b else "C" if points >= c else "D"


def worse(first: str, second: str) -> str:
    return max(first, second)


def raised(letter: str) -> str:
    return LETTERS[max(0, LETTERS.index(letter) - 1)]


def lowered(letter: str) -> str:
    return LETTERS[min(len(LETTERS) - 1, LETTERS.index(letter) + 1)]


def spread(a: float, b: float) -> float:
    top = max(abs(a), abs(b))
    return 0.0 if top == 0 else abs(a - b) / top


@dataclass
class Estimate:
    """What the evidence says about one candidate on one dimension, on one basis (measure and comparator)."""
    candidate: str
    dimension: str
    measure: str
    comparator: str
    unit: str
    better: str
    value: float
    values: List[Tuple[str, float]]
    grade: str
    points: int
    flags: Tuple[str, ...]
    rows: Tuple[str, ...]
    contradictions: List[Tuple[str, str, float]]
    reasons: List[str]
    needs_own_run: bool
    settle: str
    other_bases: Tuple[str, ...] = ()
    confounds: Tuple[str, ...] = ()

    @property
    def basis(self) -> Tuple[str, str]:
        return (self.measure.strip().lower(), self.comparator.strip().lower())

    def line(self) -> str:
        """One readable line: the number, the grade, the flags and whether a run of ours is needed."""
        on = f" on {self.comparator}" if self.comparator else ""
        flags = f"; flags: {', '.join(self.flags)}" if self.flags else ""
        more = f"; {len(self.rows)} source row(s)" if len(self.rows) > 1 else ""
        run = "; needs an own run" if self.needs_own_run else ""
        return f"{self.dimension} {self.measure}{on}: {self.value:g} {self.unit} ({self.better} is better), grade {self.grade}{flags}{more}{run}"


def settle_text(candidate: str, measure: str, comparator: str, flags: Sequence[str], ids: Sequence[str], confounds: Sequence[str],
                unit: str) -> str:
    """The single run that would settle the question, from the flags that block it."""
    where = f" on {comparator}" if comparator else " on our own cases"
    ordered = []
    if "contradicts" in flags:
        ordered.append(f"measure {measure} for {candidate} once{where}; it decides between {' and '.join(ids[:2])}")
    if "unit_mismatch" in flags:
        ordered.append(f"report {measure} for {candidate} in {unit} in one run, so the sources can be compared")
    if "confounded" in flags:
        ordered.append(f"run {candidate} and its rivals through one harness and one prompt set (named: {'; '.join(confounds)})")
    if "saturated" in flags:
        ordered.append(f"run {candidate} on our own cases or a live benchmark, since the public one no longer separates candidates")
    if "vendor_only" in flags:
        ordered.append(f"one independent run of {measure} for {candidate}{where}")
    if "stale" in flags and not ordered:
        ordered.append(f"re-measure {measure} for {candidate} on the current version")
    return ordered[0] if ordered else f"one more independent measurement of {measure} for {candidate}{where}"


def cap_by_sources(letter: str, comparable: List[Evidence], used: List[Evidence], independent: List[Evidence],
                   flags: set, reasons: List[str]) -> str:
    """The letter after the caps that come from what the sources are: vendor-side only, no independent row, one source only."""
    if all(e.vendor_side for e in comparable):
        flags.add("vendor_only")
        letter = worse(letter, "D")
        reasons.append("every source is vendor-side (vendor or maintainer reported, or run by the owner): capped at D")
    elif not independent:
        letter = worse(letter, "C")
        reasons.append("no independent source (community reports only): capped at C")
    if len({e.source_key() for e in used}) == 1:
        flags.add("single_source")
        letter = worse(letter, "B")
        reasons.append("one source only, so it is never relied on alone: capped at B")
    return letter


def find_contradictions(used: List[Evidence], converted: Dict[str, Tuple[float, str]], tol: float) -> List[Tuple[str, str, float]]:
    """Pairs of rows from different sources whose values differ beyond the tolerance."""
    found: List[Tuple[str, str, float]] = []
    for i, a in enumerate(used):
        for b in used[i + 1:]:
            gap = spread(converted[a.evidence_id][0], converted[b.evidence_id][0])
            if a.source_key() != b.source_key() and gap > tol:
                found.append((a.evidence_id, b.evidence_id, gap))
    return found


def adjust_by_agreement(letter: str, contradictions: List[Tuple[str, str, float]], independent: List[Evidence], used: List[Evidence],
                        tol: float, flags: set, reasons: List[str]) -> str:
    """Lower the letter for a contradiction, raise it when two independent sources agree."""
    agree_rows = [e for e in independent if e in used]
    if contradictions:
        flags.add("contradicts")
        reasons.append("contradiction: " + "; ".join(f"{a} and {b} differ by {s:.0%}, over the {tol:.0%} tolerance"
                                                    for a, b, s in contradictions) + ": lowered one letter")
        return lowered(letter)
    agreeing = len({e.source_key() for e in agree_rows})
    if len({e.source_key() for e in independent}) >= 2 and agreeing >= 2:
        reasons.append(f"{agreeing} independent sources agree within {tol:.0%}: raised one letter")
        return raised(letter)
    return letter


def quality_flags(used: List[Evidence], today: datetime.date, p: Params, dim: str, flags: set, reasons: List[str]) -> None:
    """Flags about the counting rows as a whole: stale, saturated, contamination risk, confounded, no method."""
    stale_limit = p.stale_days[dim]
    ages = [age_days(e, today) for e in used]
    statuses = {e.benchmark_status for e in used}
    checks = [("stale", all(d is not None and d > stale_limit for d in ages), f"every counting row is older than {stale_limit} days"),
              ("saturated", statuses <= {"saturated", "archived"}, "the benchmark is " + "/".join(sorted(statuses)) + ": it no longer separates candidates"),
              ("contamination_risk", statuses == {"contamination_risk"}, "the benchmark may have leaked into training data"),
              ("confounded", all(e.confounds for e in used), ""),
              ("no_method", all(e.method_disclosed == "no" for e in used), "no method is disclosed, so nothing can be re-run or checked")]
    for flag, raised_flag, reason in checks:
        if raised_flag:
            flags.add(flag)
            reasons.extend([reason] if reason else [])


def headline_value(agree_rows: List[Evidence], converted: Dict[str, Tuple[float, str]], best_used: Evidence) -> float:
    """The median of two or more agreeing independent rows, else the best counting row's value."""
    if len(agree_rows) >= 2:
        return statistics.median(converted[e.evidence_id][0] for e in agree_rows)
    return converted[best_used.evidence_id][0]


def own_run_need(rows: Sequence[Evidence], letter: str, flags: Tuple[str, ...], contradictions: List[Tuple[str, str, float]],
                 confounds: Tuple[str, ...], unit: str, p: Params, reasons: List[str]) -> Tuple[bool, str]:
    """Whether the grade is too low or a blocking flag is raised, and the one run that would settle it."""
    blocked = sorted(set(flags) & set(p.blocking))
    low = LETTERS.index(letter) > LETTERS.index(p.needs_grade)
    if not (low or blocked):
        return False, ""
    first = rows[0]
    ids = [x for pair in contradictions[:1] for x in pair[:2]] or [e.evidence_id for e in rows]
    why = ([f"grade {letter} is below {p.needs_grade}"] if low else []) + ([f"flags block use: {', '.join(blocked)}"] if blocked else [])
    reasons.append("needs an own run: " + "; ".join(why))
    return True, settle_text(first.candidate, first.measure, first.comparator, flags, ids, confounds, unit)


def not_counted_reasons(comparable: List[Evidence], used: List[Evidence], converted: Dict[str, Tuple[float, str]],
                        best_used: Evidence, tol: float) -> List[str]:
    """Why each vendor-side row beside an independent one is not counted."""
    out = []
    for e in (e for e in comparable if e not in used):
        gap = spread(converted[e.evidence_id][0], converted[best_used.evidence_id][0])
        out.append(f"vendor-side row {e.evidence_id} is not counted" + (f" (it differs from the independent value by {gap:.0%})" if gap > tol else ""))
    return out


def comparable_rows(rows: Sequence[Evidence], converted: Dict[str, Tuple[float, str]], base_unit: str, flags: set,
                    reasons: List[str]) -> List[Evidence]:
    """The rows whose unit converts to the base unit; the others raise ``unit_mismatch`` and are named, not compared."""
    comparable = [e for e in rows if converted[e.evidence_id][1] == base_unit]
    for e in (e for e in rows if e not in comparable):
        flags.add("unit_mismatch")
        reasons.append(f"{e.evidence_id} reports {e.unit}, which does not convert to {base_unit}; left out, not compared")
    return comparable


def confound_notes(comparable: List[Evidence], reasons: List[str]) -> Tuple[str, ...]:
    """The confounds the rows name, sorted; each row that names some says so in the reasons."""
    reasons.extend(f"{e.evidence_id} names confounds: {'; '.join(e.confounds)}" for e in comparable if e.confounds)
    return tuple(sorted({c for e in comparable for c in e.confounds}))


def grade_basis(rows: Sequence[Evidence], today: datetime.date, p: Params = DEFAULTS,
                other_bases: Tuple[str, ...] = ()) -> Estimate:
    """Grade the rows of one candidate, one dimension and one basis."""
    first = rows[0]
    dim = first.dimension
    reasons: List[str] = []
    flags: set = set()
    converted = {e.evidence_id: convert(e.value, e.unit) for e in rows}
    scored = {e.evidence_id: row_points(e, today, p) for e in rows}
    best = max(rows, key=lambda e: (scored[e.evidence_id][0], not e.vendor_side, e.date_checked))
    base_unit = converted[best.evidence_id][1]
    comparable = comparable_rows(rows, converted, base_unit, flags, reasons)
    independent = [e for e in comparable if e.independent]
    used = [e for e in comparable if not e.vendor_side] or comparable
    tol = p.tolerance[dim]
    best_used = max(used, key=lambda e: (scored[e.evidence_id][0], e.date_checked))
    points, parts = scored[best_used.evidence_id]
    letter = letter_for(points, p)
    reasons.append(f"best row {best_used.evidence_id}: {points} points ({', '.join(parts)}) gives {letter}")
    letter = cap_by_sources(letter, comparable, used, independent, flags, reasons)
    contradictions = find_contradictions(used, converted, tol)
    letter = adjust_by_agreement(letter, contradictions, independent, used, tol, flags, reasons)
    reasons.extend(not_counted_reasons(comparable, used, converted, best_used, tol))
    quality_flags(used, today, p, dim, flags, reasons)
    confounds = confound_notes(comparable, reasons)
    agree_rows = [] if contradictions else [e for e in independent if e in used]
    ordered = tuple(sorted(flags, key=FLAGS.index))
    need, settle = own_run_need(rows, letter, ordered, contradictions, confounds, base_unit, p, reasons)
    return Estimate(first.candidate, dim, first.measure, first.comparator, base_unit, first.better,
                    headline_value(agree_rows, converted, best_used), [(e.evidence_id, converted[e.evidence_id][0]) for e in comparable],
                    letter, points, ordered, tuple(e.evidence_id for e in rows), contradictions, reasons, need, settle, other_bases, confounds)


def basis_label(basis: Tuple[str, str]) -> str:
    return basis[0] + (f" on {basis[1]}" if basis[1] else "")


def all_estimates(evidence: Iterable[Evidence], today: Optional[datetime.date] = None,
                  p: Params = DEFAULTS) -> Dict[Tuple[str, str], List[Estimate]]:
    """Every graded basis per ``(candidate, dimension)`` (normalised candidate name), best first."""
    today = today or datetime.date.today()
    groups: Dict[Tuple[str, str, Tuple[str, str]], List[Evidence]] = {}
    for e in evidence:
        groups.setdefault((norm(e.candidate), e.dimension, e.basis), []).append(e)
    out: Dict[Tuple[str, str], List[Estimate]] = {}
    for (cand, dim, _), rows in groups.items():
        out.setdefault((cand, dim), []).append(grade_basis(rows, today, p))
    for key, found in out.items():
        found.sort(key=lambda x: (LETTERS.index(x.grade), -len(x.rows), x.measure))
        labels = tuple(basis_label(x.basis) for x in found)
        for x in found:
            x.other_bases = tuple(label for label in labels if label != basis_label(x.basis))
    return out


@solution("public-evidence", kind="event", example={"evidence": []})
def grade_evidence(evidence: Iterable[Evidence], today: Optional[datetime.date] = None,
                   p: Params = DEFAULTS) -> Dict[Tuple[str, str], Estimate]:
    """Grade what others measured: one ``Estimate`` per candidate and dimension, with its flags and whether an own run is needed."""


@implementation("public-evidence", "graded")
def estimates(evidence: Iterable[Evidence], today: Optional[datetime.date] = None,
              p: Params = DEFAULTS) -> Dict[Tuple[str, str], Estimate]:
    """One ``Estimate`` per ``(candidate, dimension)``: the best graded basis; the others are named in ``other_bases``."""
    return {key: found[0] for key, found in all_estimates(evidence, today, p).items()}


def lines_for_implementation(estimate_map: Mapping[Tuple[str, str], Estimate], keys: str) -> List[Estimate]:
    wanted = set(keys.split(","))
    return [est for (cand, _), est in sorted(estimate_map.items()) if cand in wanted]


def public_stage_met(found: Sequence[Estimate], p: Params = DEFAULTS) -> Tuple[bool, str]:
    """Whether a ``public`` cascade stage is satisfied for an implementation: evidence rows exist and at least one dimension
    grades C or better. It never stands for a result of ours."""
    if not found:
        return False, "no public evidence rows"
    best = min(found, key=lambda x: LETTERS.index(x.grade))
    if LETTERS.index(best.grade) <= LETTERS.index("C"):
        return True, f"best grade {best.grade} ({best.dimension})"
    return False, f"best grade {best.grade} ({best.dimension}) is below C"
