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
grades and ranks the records.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from esoi import implementation, solution

COLUMNS = ("evidence_id", "candidate", "dimension", "measure", "value", "unit", "better", "comparator", "source_url",
           "source_kind", "run_by_independent", "method_disclosed", "n", "benchmark_status", "date_published",
           "date_checked", "confounds", "note")
REQUIRED = ("evidence_id", "candidate", "dimension", "measure", "value", "unit", "better", "source_url", "source_kind",
            "run_by_independent", "method_disclosed", "benchmark_status", "date_checked")
DIMENSIONS = ("quality", "token_efficiency", "speed", "cost", "reliability", "safety", "maintenance")
BETTER = ("higher", "lower")
SOURCE_KINDS = ("independent_benchmark", "replication", "peer_reviewed", "vendor_reported", "maintainer_reported",
                "community_report", "own_run")
INDEPENDENT_KINDS = ("independent_benchmark", "replication", "peer_reviewed", "own_run")
VENDOR_KINDS = ("vendor_reported", "maintainer_reported")
RUN_BY = ("yes", "no", "unknown")
METHOD = ("yes", "partial", "no")
STATUS = ("live", "saturated", "archived", "contamination_risk", "unknown")
LETTERS = "ABCD"
FLAGS = ("single_source", "vendor_only", "stale", "saturated", "confounded", "contradicts", "no_method", "unit_mismatch",
         "contamination_risk", "not_comparable")
LIST_SEPARATOR = ";"

# Explicit unit table: family -> (base unit, {unit: factor to the base}). A unit not listed is its own family and compares only
# with the same string. Nothing converts between families (seconds are never tokens, dollars are never a fraction).
UNITS: Dict[str, Tuple[str, Dict[str, float]]] = {
    "time": ("s", {"ms": 0.001, "s": 1.0, "sec": 1.0, "min": 60.0, "h": 3600.0}),
    "tokens": ("tokens", {"tokens": 1.0, "ktokens": 1e3, "mtokens": 1e6}),
    "fraction": ("fraction", {"fraction": 1.0, "ratio": 1.0, "percent": 0.01, "%": 0.01}),
    "money": ("usd", {"usd": 1.0, "cents": 0.01}),
    "price_per_mtok": ("usd/mtok", {"usd/mtok": 1.0, "usd/ktok": 1e3, "usd/tok": 1e6}),
    "rate": ("tokens/s", {"tokens/s": 1.0, "tok/s": 1.0}),
    "count": ("count", {"count": 1.0, "k": 1e3}),
}
UNIT_FAMILY = {unit: (family, base, factor) for family, (base, table) in UNITS.items() for unit, factor in table.items()}

REASONS: Dict[str, str] = {
    "kind": "Who measured and how it can be checked: an independent benchmark, a replication, a peer-reviewed result and our own "
            "run are checkable by someone with no stake (4); a maintainer or community report is useful but unreviewed (2); "
            "a vendor reported its own product (1), because it chose the benchmark, the settings and the run.",
    "independence": "Whether someone with no stake ran it: yes +2; unknown 0 (not credited, not punished); no -1 (the owner ran it).",
    "method": "Whether the harness, prompts and settings are disclosed: yes +2, partial +1, no 0. A result that cannot be re-run "
              "cannot be checked.",
    "sample": "How many cases or runs: 300 or more +2, 30 or more +1, fewer or unstated 0. Small samples swing by chance.",
    "status": "A benchmark that is saturated, archived or contaminated no longer separates candidates (-2); unknown status -1; live 0.",
    "age": "Models, prices and libraries change: past half of the dimension's stale days -1, past the stale days -2, undated -1. "
           "Prices go stale fastest, quality slowest.",
    "confound": "A named confound (a different harness, prompt or tool set) means the number cannot be attributed to the "
                "candidate: -1 each, at most -2.",
    "cuts": "A 8 or more points of 10, B 6, C 4, D below. A needs near-complete disclosure; D cannot rank anything.",
    "caps": "One eval is never relied on alone: a single source is at most B; no independent source at most C; vendor-side only "
            "at most D. Agreement of independent sources is the only way to A.",
    "stale_days": "Days after which a number is stale, by dimension: cost 90 and maintenance 90, speed and token efficiency and "
                  "reliability 180, quality and safety 365.",
    "tolerance": "Relative difference inside which two numbers agree: quality, reliability and safety 0.10; cost 0.20; token "
                 "efficiency 0.25; speed and maintenance 0.30 (timings and activity vary more between runs).",
    "needs_grade": "Below this letter the evidence cannot decide alone, so a run of ours is needed (default C).",
    "blocking": "Flags that stop the evidence being used even at a good letter: vendor_only, contradicts, unit_mismatch, "
                "saturated, confounded.",
    "confidence": "How much a letter counts in the overall weighted ranking: A 1.0, B 0.9, C 0.75, D 0 (a D number is shown, never added).",
}


@dataclass(frozen=True)
class Params:
    """Every weight of the grader in one place; ``REASONS`` says why each default is what it is."""
    kind: Mapping[str, int] = field(default_factory=lambda: {
        "independent_benchmark": 4, "replication": 4, "peer_reviewed": 4, "own_run": 4, "maintainer_reported": 2,
        "community_report": 2, "vendor_reported": 1})
    independence: Mapping[str, int] = field(default_factory=lambda: {"yes": 2, "unknown": 0, "no": -1})
    method: Mapping[str, int] = field(default_factory=lambda: {"yes": 2, "partial": 1, "no": 0})
    sample_steps: Tuple[Tuple[int, int], ...] = ((300, 2), (30, 1))
    status: Mapping[str, int] = field(default_factory=lambda: {
        "live": 0, "unknown": -1, "saturated": -2, "archived": -2, "contamination_risk": -2})
    undated: int = -1
    half_age_penalty: int = -1
    stale_penalty: int = -2
    confound_penalty: int = -1
    confound_floor: int = -2
    cuts: Tuple[int, int, int] = (8, 6, 4)
    stale_days: Mapping[str, int] = field(default_factory=lambda: {
        "quality": 365, "safety": 365, "speed": 180, "token_efficiency": 180, "reliability": 180, "cost": 90, "maintenance": 90})
    tolerance: Mapping[str, float] = field(default_factory=lambda: {
        "quality": 0.10, "reliability": 0.10, "safety": 0.10, "cost": 0.20, "token_efficiency": 0.25, "speed": 0.30,
        "maintenance": 0.30})
    needs_grade: str = "C"
    blocking: frozenset = frozenset({"vendor_only", "contradicts", "unit_mismatch", "saturated", "confounded"})
    confidence: Mapping[str, float] = field(default_factory=lambda: {"A": 1.0, "B": 0.9, "C": 0.75, "D": 0.0})


DEFAULTS = Params()


class EvidenceError(ValueError):
    """The evidence records are not valid; ``problems`` lists every one."""

    def __init__(self, problems: List[str]):
        self.problems = problems
        super().__init__("; ".join(problems[:5]) + (f"; and {len(problems) - 5} more" if len(problems) > 5 else ""))


@dataclass(frozen=True)
class Evidence:
    """One reported number, read and checked."""
    evidence_id: str
    candidate: str
    dimension: str
    measure: str
    value: float
    unit: str
    better: str
    comparator: str
    source_url: str
    source_kind: str
    run_by_independent: str
    method_disclosed: str
    n: Optional[int]
    benchmark_status: str
    date_published: Optional[datetime.date]
    date_checked: datetime.date
    confounds: Tuple[str, ...]
    note: str
    line: int = 0

    @property
    def independent(self) -> bool:
        return self.source_kind in INDEPENDENT_KINDS and self.run_by_independent != "no"

    @property
    def vendor_side(self) -> bool:
        return self.source_kind in VENDOR_KINDS or self.run_by_independent == "no"

    @property
    def basis(self) -> Tuple[str, str]:
        return (self.measure.strip().lower(), self.comparator.strip().lower())

    def source_key(self) -> str:
        return self.source_url.strip().lower().rstrip("/")


def norm(name: str) -> str:
    """A name compared without case, underscores or spaces (``Lexical_Only`` and ``lexical-only`` are one candidate)."""
    return re.sub(r"[\s_]+", "-", (name or "").strip().lower())


# ---------------------------------------------------------------- reading

def parse_rows(rows: Iterable[Mapping[str, str]], header: Optional[Sequence[str]] = None) -> Tuple[List[Evidence], List[str]]:
    """``(evidence, problems)`` from row dicts. Every problem names its line (header is line 1) and the column."""
    problems: List[str] = []
    if header is not None:
        for column in COLUMNS:
            if column not in header:
                problems.append(f"header: column {column} is missing")
        for column in header:
            if column not in COLUMNS:
                problems.append(f"header: column {column} is not part of the evidence record")
        if problems:
            return [], problems
    out: List[Evidence] = []
    seen: Dict[str, int] = {}
    for position, row in enumerate(rows, 2):
        before = len(problems)
        cell = {c: (row.get(c) or "").strip() for c in COLUMNS}

        def bad(column: str, message: str) -> None:
            problems.append(f"line {position} ({cell['evidence_id'] or 'no id'}): {column} {message}")

        for column in REQUIRED:
            if not cell[column]:
                bad(column, "is empty; write a value (use `unknown` where a column allows it)")
        for column, allowed in (("dimension", DIMENSIONS), ("better", BETTER), ("source_kind", SOURCE_KINDS),
                                ("run_by_independent", RUN_BY), ("method_disclosed", METHOD), ("benchmark_status", STATUS)):
            if cell[column] and cell[column] not in allowed:
                bad(column, f"is {cell[column]!r}, not one of {', '.join(allowed)}")
        if cell["evidence_id"]:
            if cell["evidence_id"] in seen:
                bad("evidence_id", f"repeats line {seen[cell['evidence_id']]}")
            seen.setdefault(cell["evidence_id"], position)
        value = n = None
        if cell["value"]:
            try:
                value = float(cell["value"])
                if value != value or value in (float("inf"), float("-inf")):
                    raise ValueError
            except ValueError:
                bad("value", f"is {cell['value']!r}, not a finite number")
        if cell["n"]:
            if cell["n"].isdigit() and int(cell["n"]) > 0:
                n = int(cell["n"])
            else:
                bad("n", f"is {cell['n']!r}, not a positive whole number (leave it empty when unstated)")
        if cell["source_url"] and not re.match(r"^https?://\S+$", cell["source_url"]):
            bad("source_url", "is not an http(s) link")
        dates: Dict[str, Optional[datetime.date]] = {}
        for column in ("date_published", "date_checked"):
            dates[column] = None
            if cell[column]:
                try:
                    dates[column] = datetime.date.fromisoformat(cell[column])
                except ValueError:
                    bad(column, f"is {cell[column]!r}, not a date like 2026-10-31")
        if len(problems) == before:
            out.append(Evidence(
                cell["evidence_id"], cell["candidate"], cell["dimension"], cell["measure"], value, cell["unit"], cell["better"],
                cell["comparator"], cell["source_url"], cell["source_kind"], cell["run_by_independent"], cell["method_disclosed"],
                n, cell["benchmark_status"], dates["date_published"], dates["date_checked"],
                tuple(c.strip() for c in cell["confounds"].split(LIST_SEPARATOR) if c.strip()), cell["note"], position))
    direction: Dict[Tuple[str, str], Evidence] = {}
    for e in out:
        first = direction.setdefault((e.dimension, e.measure.lower()), e)
        if first.better != e.better:
            problems.append(f"line {e.line} ({e.evidence_id}): better is {e.better} but {first.evidence_id} (line {first.line}) "
                            f"says {first.better} for the same measure {e.measure!r}")
    return out, problems


def parse_text(text: str) -> List[Evidence]:
    """The evidence in CSV text, or ``EvidenceError`` naming every problem."""
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    rows = list(reader)
    extra = [r for r in rows if None in r]
    problems: List[str] = []
    if extra:
        problems.append("a row has more cells than the header; quote any cell that contains a comma")
    found, more = parse_rows(rows, header)
    if problems or more:
        raise EvidenceError(problems + more)
    return found


def load(path: Path) -> List[Evidence]:
    return parse_text(Path(path).read_text(encoding="utf-8"))


def header_line() -> str:
    return ",".join(COLUMNS)


# ---------------------------------------------------------------- grading

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
    comparable = [e for e in rows if converted[e.evidence_id][1] == base_unit]
    for e in rows:
        if e not in comparable:
            flags.add("unit_mismatch")
            reasons.append(f"{e.evidence_id} reports {e.unit}, which does not convert to {base_unit}; left out, not compared")
    independent = [e for e in comparable if e.independent]
    vendor_only = all(e.vendor_side for e in comparable)
    used = [e for e in comparable if not e.vendor_side] or comparable
    ignored = [e for e in comparable if e not in used]
    tol = p.tolerance[dim]
    best_used = max(used, key=lambda e: (scored[e.evidence_id][0], e.date_checked))
    points, parts = scored[best_used.evidence_id]
    letter = letter_for(points, p)
    reasons.append(f"best row {best_used.evidence_id}: {points} points ({', '.join(parts)}) gives {letter}")
    if vendor_only:
        flags.add("vendor_only")
        letter = worse(letter, "D")
        reasons.append("every source is vendor-side (vendor or maintainer reported, or run by the owner): capped at D")
    elif not independent:
        letter = worse(letter, "C")
        reasons.append("no independent source (community reports only): capped at C")
    sources = {e.source_key() for e in used}
    if len(sources) == 1:
        flags.add("single_source")
        letter = worse(letter, "B")
        reasons.append("one source only, so it is never relied on alone: capped at B")
    ind_sources = {e.source_key() for e in independent}
    agree_rows = [e for e in independent if e in used]
    contradictions: List[Tuple[str, str, float]] = []
    for i, a in enumerate(used):
        for b in used[i + 1:]:
            if a.source_key() != b.source_key() and spread(converted[a.evidence_id][0], converted[b.evidence_id][0]) > tol:
                contradictions.append((a.evidence_id, b.evidence_id, spread(converted[a.evidence_id][0], converted[b.evidence_id][0])))
    if contradictions:
        flags.add("contradicts")
        letter = lowered(letter)
        reasons.append("contradiction: " + "; ".join(f"{a} and {b} differ by {s:.0%}, over the {tol:.0%} tolerance"
                                                    for a, b, s in contradictions) + ": lowered one letter")
    elif len(ind_sources) >= 2 and len({e.source_key() for e in agree_rows}) >= 2:
        letter = raised(letter)
        reasons.append(f"{len({e.source_key() for e in agree_rows})} independent sources agree within {tol:.0%}: raised one letter")
    for e in ignored:
        gap = spread(converted[e.evidence_id][0], converted[best_used.evidence_id][0])
        reasons.append(f"vendor-side row {e.evidence_id} is not counted"
                       + (f" (it differs from the independent value by {gap:.0%})" if gap > tol else ""))
    days = [age_days(e, today) for e in used]
    stale_limit = p.stale_days[dim]
    if all(d is not None and d > stale_limit for d in days):
        flags.add("stale")
        reasons.append(f"every counting row is older than {stale_limit} days")
    if all(e.benchmark_status in ("saturated", "archived") for e in used):
        flags.add("saturated")
        reasons.append("the benchmark is " + "/".join(sorted({e.benchmark_status for e in used})) + ": it no longer separates candidates")
    if all(e.benchmark_status == "contamination_risk" for e in used):
        flags.add("contamination_risk")
        reasons.append("the benchmark may have leaked into training data")
    if all(e.confounds for e in used):
        flags.add("confounded")
    if all(e.method_disclosed == "no" for e in used):
        flags.add("no_method")
        reasons.append("no method is disclosed, so nothing can be re-run or checked")
    confounds = tuple(sorted({c for e in comparable for c in e.confounds}))
    for e in comparable:
        if e.confounds:
            reasons.append(f"{e.evidence_id} names confounds: {'; '.join(e.confounds)}")
    values = [(e.evidence_id, converted[e.evidence_id][0]) for e in comparable]
    if len(agree_rows) >= 2 and not contradictions:
        value = statistics.median(converted[e.evidence_id][0] for e in agree_rows)
    else:
        value = converted[best_used.evidence_id][0]
    ordered = tuple(sorted(flags, key=FLAGS.index))
    blocked = sorted(set(ordered) & set(p.blocking))
    low = LETTERS.index(letter) > LETTERS.index(p.needs_grade)
    need = low or bool(blocked)
    ids = [x for pair in contradictions[:1] for x in pair[:2]] or [e.evidence_id for e in rows]
    settle = settle_text(first.candidate, first.measure, first.comparator, ordered, ids, confounds, base_unit) if need else ""
    if need:
        why = ([f"grade {letter} is below {p.needs_grade}"] if low else []) + ([f"flags block use: {', '.join(blocked)}"] if blocked else [])
        reasons.append("needs an own run: " + "; ".join(why))
    return Estimate(first.candidate, dim, first.measure, first.comparator, base_unit, first.better, value, values, letter, points,
                    ordered, tuple(e.evidence_id for e in rows), contradictions, reasons, need, settle, other_bases, confounds)


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


@solution("public-evidence")
def grade_evidence(evidence: Iterable[Evidence], today: Optional[datetime.date] = None,
                   p: Params = DEFAULTS) -> Dict[Tuple[str, str], Estimate]:
    """Grade what others measured: one ``Estimate`` per candidate and dimension, with its flags and whether an own run is needed."""


@implementation("public-evidence", "graded")
def estimates(evidence: Iterable[Evidence], today: Optional[datetime.date] = None,
              p: Params = DEFAULTS) -> Dict[Tuple[str, str], Estimate]:
    """One ``Estimate`` per ``(candidate, dimension)``: the best graded basis; the others are named in ``other_bases``."""
    return {key: found[0] for key, found in all_estimates(evidence, today, p).items()}


# ---------------------------------------------------------------- ranking

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


# ---------------------------------------------------------------- against our own results

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
    from . import leaderboard
    return {impl: leaderboard.pass_rate(dict(row)) for impl, row in rows.items()}


# ---------------------------------------------------------------- the repository

def evidence_path(config) -> Path:
    """Where this repository keeps its evidence: ``[evidence] file`` in the configuration, else ``evidence.csv`` in the structure folder."""
    table = getattr(config, "evidence", {}) or {}
    return config.root / table.get("file", f"{config.structure_dir}/evidence.csv")


def load_for(config) -> List[Evidence]:
    """The repository's evidence, or an empty list when it keeps none. A malformed file raises ``EvidenceError``."""
    path = evidence_path(config)
    return load(path) if path.is_file() else []


def aliases(config) -> Dict[str, str]:
    """``{candidate: implementation}`` from ``[evidence.aliases]`` in the configuration (both normalised)."""
    table = (getattr(config, "evidence", {}) or {}).get("aliases", {})
    return {norm(k): norm(v) for k, v in table.items()}


def implementation_candidates(config, registry, solution_id: str) -> Dict[str, str]:
    """``{implementation name: candidate key}`` for a solution. The smallest honest mapping: an implementation is matched by the
    part of its id after the colon, or its ``name``, equal to the evidence's candidate (case, ``_``, ``-`` and spaces ignored);
    ``[evidence.aliases]`` maps a candidate that is spelled differently. Nothing is guessed beyond that."""
    alias = aliases(config)
    out: Dict[str, str] = {}
    for row in registry.implementations:
        if row.get("solution_id") != solution_id:
            continue
        impl_id = row.get("implementation_id", "")
        short = impl_id.split(":", 1)[-1]
        keys = {norm(short), norm(row.get("name", ""))} | {c for c, target in alias.items() if target in (norm(short), norm(impl_id))}
        out[short] = ",".join(sorted(keys))
    return out


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


def run_cli(config, action: str = "list", candidate: str = "", dimension: str = "", weights: str = "", file: str = "",
            say: Callable[[str], None] = print, today: Optional[datetime.date] = None) -> int:
    """``esoi evidence list|grade|rank|table``. ``list`` checks and shows the rows; ``grade`` prints each (candidate, dimension)
    estimate with its reasons; ``rank`` orders candidates per dimension (``--weights quality=2,cost=1``); ``table`` prints the
    weights and why. Exit 1 when the records are invalid."""
    if action == "table":
        for key, text in REASONS.items():
            say(f"{key}: {text}")
        return 0
    path = Path(file) if file else evidence_path(config)
    if not path.is_file():
        say(f"no evidence file at {path.relative_to(config.root) if path.is_relative_to(config.root) else path}; "
            f"columns: {header_line()}")
        return 0
    try:
        rows = load(path)
    except EvidenceError as error:
        for line in error.problems:
            say(f"problem: {line}")
        return 1
    rows = [e for e in rows if not candidate or norm(e.candidate) == norm(candidate)]
    rows = [e for e in rows if not dimension or e.dimension == dimension]
    if action == "list":
        for e in rows:
            say(f"{e.evidence_id}: {e.candidate} {e.dimension} {e.measure} = {e.value:g} {e.unit} [{e.source_kind}, "
                f"independent {e.run_by_independent}, method {e.method_disclosed}, {e.benchmark_status}]")
        say(f"{len(rows)} evidence row(s); public evidence is complementary and never a result row")
        return 0
    if action == "grade":
        for est in sorted(estimates(rows, today).values(), key=lambda x: (norm(x.candidate), x.dimension)):
            say(f"{est.candidate}: {est.line()}")
            for reason in est.reasons:
                say(f"    {reason}")
            if est.other_bases:
                say(f"    other bases, not merged: {', '.join(est.other_bases)}")
            if est.needs_own_run:
                say(f"    to settle it: {est.settle}")
        return 0
    if action == "rank":
        wanted = {d: 1.0 for d in sorted({e.dimension for e in rows})}
        if weights:
            wanted = {}
            for part in weights.split(","):
                name, _, number = part.partition("=")
                try:
                    wanted[name.strip()] = float(number or 1)
                except ValueError:
                    say(f"problem: weight {part!r} is not dimension=number")
                    return 1
        try:
            ranking = rank(rows, wanted, today=today)
        except ValueError as error:
            say(f"problem: {error}")
            return 1
        for dim, shortlist in ranking.dimensions.items():
            say(f"{dim} (weight {shortlist.weight:g}; basis: {shortlist.basis or 'none'}; {shortlist.better} is better)")
            for place in shortlist.ordered:
                say(f"  {place.rank}. {place.candidate}: {place.reason}")
            for name, why in shortlist.not_comparable:
                say(f"  not comparable: {name}: {why}")
            for name in shortlist.no_evidence:
                say(f"  no evidence: {name}")
        say("overall (weighted by grade; a candidate with little graded evidence scores low):")
        for item in ranking.overall:
            say(f"  {item.candidate}: {item.score:.2f} (graded coverage {item.covered:.0%})")
        return 0
    say(f"unknown action {action!r}; use list, grade, rank or table")
    return 1
