"""The score a row is ranked by and the order of rows: pass rate or balanced score first, then cost, with the figures shown beside a result."""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Tuple

from esoi.optimization.leaderboard.results_log import Row, Rows


def pass_rate(row: Row) -> float:
    """The score a row is ranked by. A row recorded with a balanced score (its component sets ``[balance.<component>]``,
    see ``esoi.optimization.measurement_harness.balance``) ranks by that, so accuracy bought with a large price in money or time does not win by itself.
    Otherwise passed over cases; a blank or malformed count reads as zero, so one bad line cannot stop the whole board."""
    try:
        if str(row.get("balanced") or "").strip():
            return float(row["balanced"])
    except ValueError:
        pass
    def count(name: str) -> int:
        try:
            return int(float(row.get(name) or 0))
        except ValueError:
            return 0
    return count("passed") / max(count("cases"), 1)


def dollars(row: Row) -> float:
    """The recorded dollar cost; a model-calling run whose cost is blank (no price known) counts as unbounded, never
    as free."""
    if cost_known(row):
        return float(row["cost_usd"])
    return float("inf") if is_sampled(row) else 0.0


def cost_known(row: Row) -> bool:
    """Whether the row records a dollar cost (a blank cell means the price was unknown; 0 is a real zero)."""
    return row.get("cost_usd") is not None and str(row["cost_usd"]).strip() != ""


def rank(rows: Rows) -> List[Row]:
    """Best first: pass rate, then cost (lower is better)."""
    return sorted(rows.values(), key=lambda r: (-pass_rate(r), dollars(r), r["impl"]))


SIMULATED = "simulated"


def is_simulated(row: Row) -> bool:
    """A run of an arm that declared itself a deterministic stand-in for a model (model ``simulated``)."""
    return (row.get("model") or "").strip() == SIMULATED


def is_sampled(row: Row) -> bool:
    """A run that called a model: its pass rate and tokens move between re-runs of the same code. A simulated run
    counts the calls a model would make but is deterministic."""
    return int(float(row.get("model_calls") or 0)) > 0 and not is_simulated(row)


def higher(row: Row, other: Row) -> bool:
    """True when ``row`` has the strictly better point estimate on the authoritative metric. A screen for cascading stages, never a
    reason to switch the selected arm (that takes ``decisions``)."""
    return estimate(row) > estimate(other)


def passes(row: Row) -> int:
    try:
        return int(float(row.get("passed") or 0))
    except ValueError:
        return 0


def cost_per_passing(row: Row) -> Optional[Tuple[str, float]]:
    """``(unit, amount)`` per passing case, shown beside a result: dollars when the cost is recorded, else model calls; ``None``
    with no passing case. It informs a reader; it decides nothing (cost and speed count only inside the authoritative metric)."""
    if passes(row) <= 0:
        return None
    if cost_known(row):
        return "usd", float(row["cost_usd"]) / passes(row)
    calls = float(row.get("model_calls") or 0)
    return ("calls", calls / passes(row)) if calls > 0 else None


def estimate(row: Row) -> Fraction:
    """The point estimate on the authoritative metric: the balanced score when the run has one, else the pass rate."""
    return Fraction(pass_rate(row)).limit_denominator(10000)


def uses_balanced(own: Row, other: Row) -> bool:
    return bool(str(own.get("balanced") or "").strip() and str(other.get("balanced") or "").strip())


def tokens_label(row: Row) -> str:
    """Tokens in and out, compact (``1.29M``, ``610k``, ``0``): the number spend verdicts are decided on."""
    total = float(row.get("tokens_in") or 0) + float(row.get("tokens_out") or 0)
    return f"{total / 1e6:.2f}M" if total >= 1e6 else f"{total / 1e3:.0f}k" if total >= 1e3 else f"{total:.0f}"
