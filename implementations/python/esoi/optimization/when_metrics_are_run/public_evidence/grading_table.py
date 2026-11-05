"""The visible table the evidence grader reads: unit conversions, every weight in ``Params`` and the reason for each."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Tuple


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
