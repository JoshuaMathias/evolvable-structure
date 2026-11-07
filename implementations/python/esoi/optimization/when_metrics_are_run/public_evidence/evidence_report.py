"""``esoi evidence list|grade|rank|table``: check, show, grade and rank the evidence records."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable, Optional

from esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading import estimates
from esoi.optimization.when_metrics_are_run.public_evidence.evidence_ranking import rank
from esoi.optimization.when_metrics_are_run.public_evidence.evidence_records import EvidenceError, evidence_path, header_line, load, norm
from esoi.optimization.when_metrics_are_run.public_evidence.grading_table import REASONS


def show_list(rows, say: Callable[[str], None]) -> int:
    """Print each evidence row on a line."""
    for e in rows:
        say(f"{e.evidence_id}: {e.candidate} {e.dimension} {e.measure} = {e.value:g} {e.unit} [{e.source_kind}, "
            f"independent {e.run_by_independent}, method {e.method_disclosed}, {e.benchmark_status}]")
    say(f"{len(rows)} evidence row(s); public evidence is complementary and never a result row")
    return 0


def show_grade(rows, today: Optional[datetime.date], say: Callable[[str], None]) -> int:
    """Print each (candidate, dimension) estimate with its reasons."""
    for est in sorted(estimates(rows, today).values(), key=lambda x: (norm(x.candidate), x.dimension)):
        say(f"{est.candidate}: {est.line()}")
        for reason in est.reasons:
            say(f"    {reason}")
        if est.other_bases:
            say(f"    other bases, not merged: {', '.join(est.other_bases)}")
        if est.needs_own_run:
            say(f"    to settle it: {est.settle}")
    return 0


def parse_weights(weights: str, rows) -> Dict[str, float]:
    """``{dimension: weight}`` from ``a=2,b=1`` (a bare name weighs 1); every dimension of the rows weighs 1 when none is given.
    Raises ``ValueError`` naming the part that is not ``dimension=number``."""
    if not weights:
        return {d: 1.0 for d in sorted({e.dimension for e in rows})}
    wanted: Dict[str, float] = {}
    for part in weights.split(","):
        name, _, number = part.partition("=")
        try:
            wanted[name.strip()] = float(number or 1)
        except ValueError:
            raise ValueError(f"weight {part!r} is not dimension=number") from None
    return wanted


def show_rank(rows, weights: str, today: Optional[datetime.date], say: Callable[[str], None]) -> int:
    """Print the per-dimension shortlists and the weighted overall."""
    try:
        ranking = rank(rows, parse_weights(weights, rows), today=today)
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
    rows = [e for e in rows if (not candidate or norm(e.candidate) == norm(candidate)) and (not dimension or e.dimension == dimension)]
    if action == "list":
        return show_list(rows, say)
    if action == "grade":
        return show_grade(rows, today, say)
    if action == "rank":
        return show_rank(rows, weights, today, say)
    say(f"unknown action {action!r}; use list, grade, rank or table")
    return 1
