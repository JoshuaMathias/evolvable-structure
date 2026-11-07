"""Source access: what a request reads from the systems a store is built from or answered from, metered, priced and bounded.

Reading source systems (a server's records, local files) is a cost of its own and a risk of its own, so it is metered like a model call
and declared where the balance is: a ``[balance.<component>.source_access]`` table, committed before any arm is scored.

    [balance.myselect.source_access]
    usd_per_record = 0.00001      # the constant price of one record read; also usd_per_mb and usd_per_call
    max_records_per_request = 200  # the per-request read budget; also max_mb_per_request and max_calls_per_request
    allowed_scopes = ["workspace"]     # nothing is read outside these scopes ("" in the list allows an unscoped read)
    forbid_full_scan = true        # a request never scans a whole source (the default)

An arm reports a read with ``meter.read(records=.., bytes=.., calls=.., scope=.., full_scan=..)``. The price of each read is added to the
run's cost, and a request (one case) that breaks a limit FAILS, with the reason in its note: the limits are gates, not prices. A consumer
that builds on a foundation (``esoi.runtime.consumer_check.foundation``) inherits the foundation's table and may TIGHTEN it, never loosen it: ``loosening`` names every
limit of the consumer's table that is looser than the foundation's (rule S47). Standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Set

PRICES = ("usd_per_record", "usd_per_mb", "usd_per_call")
LIMITS = {"max_records_per_request": "records", "max_mb_per_request": "mb", "max_calls_per_request": "calls"}
BYTES_PER_MB = 1_000_000


@dataclass
class Reads:
    """What was read: records, bytes and calls, the scopes touched and whether a whole source was scanned."""
    records: int = 0
    bytes: int = 0
    calls: int = 0
    scopes: Set[str] = field(default_factory=set)
    full_scan: bool = False

    def copy(self) -> "Reads":
        return Reads(self.records, self.bytes, self.calls, set(self.scopes), self.full_scan)

    def minus(self, before: "Reads") -> "Reads":
        """The reads made since ``before`` (a ``copy`` taken earlier)."""
        return Reads(self.records - before.records, self.bytes - before.bytes, self.calls - before.calls, set(self.scopes), self.full_scan)


def check_source_access(sub: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` for an unknown key or a negative price or limit."""
    known = set(PRICES) | set(LIMITS) | {"allowed_scopes", "forbid_full_scan"}
    if unknown := sorted(set(sub) - known):
        raise ValueError(f"source_access has unknown key(s): {', '.join(unknown)}")
    for key in (*PRICES, *LIMITS):
        if key in sub and float(sub[key]) < 0:
            raise ValueError(f"source_access {key} cannot be negative")


def settings(table: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """The validated ``source_access`` table of a ``[balance.<component>]`` table, or None when there is none. Raises ValueError for a
    negative price or limit or an unknown key (a typo must not loosen a gate silently)."""
    sub = (table or {}).get("source_access")
    if not sub:
        return None
    check_source_access(sub)
    return {"prices": {k: float(sub[k]) for k in PRICES if k in sub}, "limits": {k: float(sub[k]) for k in LIMITS if k in sub},
            "allowed_scopes": None if "allowed_scopes" not in sub else {str(s) for s in sub["allowed_scopes"]},
            "forbid_full_scan": bool(sub.get("forbid_full_scan", True))}


def price(reads: Reads, table: Optional[Mapping[str, Any]]) -> float:
    """The dollars the reads cost at the table's constants (0.0 with no table)."""
    cfg = settings(table)
    if cfg is None:
        return 0.0
    p = cfg["prices"]
    return (reads.records * p.get("usd_per_record", 0.0) + reads.bytes / BYTES_PER_MB * p.get("usd_per_mb", 0.0)
            + reads.calls * p.get("usd_per_call", 0.0))


def violation(reads: Reads, table: Optional[Mapping[str, Any]]) -> str:
    """Why one request's reads break a gate, or an empty string: a full scan, a read budget spent, a scope outside the allowed ones."""
    cfg = settings(table)
    if cfg is None:
        return ""
    if cfg["forbid_full_scan"] and reads.full_scan:
        return "the request scanned a whole source"
    used = {"records": reads.records, "mb": reads.bytes / BYTES_PER_MB, "calls": reads.calls}
    for key, limit in cfg["limits"].items():
        if used[LIMITS[key]] > limit:
            return f"the request read {used[LIMITS[key]]:g} {LIMITS[key]}, over {key} = {limit:g}"
    if cfg["allowed_scopes"] is not None and (outside := sorted(reads.scopes - cfg["allowed_scopes"])):
        return f"the request read outside the allowed scopes ({', '.join(repr(s) for s in outside)})"
    return ""


def loosening(own: Optional[Mapping[str, Any]], foundation: Optional[Mapping[str, Any]]) -> List[str]:
    """Every limit of the consumer's ``[balance.<c>]`` table that is looser than the foundation's: a larger budget, a scope the
    foundation does not allow, full scans allowed where they are forbidden, or a gate the foundation has that the consumer drops.
    An empty list means the consumer inherits the foundation's gates unchanged or tightens them."""
    theirs = settings(foundation)
    if theirs is None:
        return []
    mine = settings(own) or {"prices": {}, "limits": {}, "allowed_scopes": None, "forbid_full_scan": True}
    out = [f"{key} is {mine['limits'][key]:g}, above the foundation's {limit:g}"
           for key, limit in theirs["limits"].items() if key in mine["limits"] and mine["limits"][key] > limit]
    if theirs["forbid_full_scan"] and not mine["forbid_full_scan"]:
        out.append("forbid_full_scan is off, the foundation forbids a full scan")
    return out + wider_scopes(mine["allowed_scopes"], theirs["allowed_scopes"])


def wider_scopes(mine: Optional[set], theirs: Optional[set]) -> List[str]:
    """The note for scopes the consumer allows that the foundation does not."""
    if theirs is None or mine is None or not (extra := sorted(mine - theirs)):
        return []
    return [f"allowed_scopes adds {', '.join(repr(s) for s in extra)}, which the foundation does not allow"]
