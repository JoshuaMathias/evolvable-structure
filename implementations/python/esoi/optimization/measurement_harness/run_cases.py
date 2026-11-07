"""Run a component's cases one by one through its scorer, metering each, reusing rows already run for this implementation version."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Tuple

from esoi.optimization.measurement_harness import access
from esoi.optimization.measurement_harness.call_meter import CallMeter
from esoi.optimization.when_metrics_are_run.paid_gating import BudgetExceeded


def new_reused() -> Dict[str, Any]:
    """An empty tally of the spend carried over from reused rows."""
    return dict(calls=0, tokens_in=0, tokens_out=0, cost=0.0, seconds=0.0, cases=0)


def take_reused(row: Dict[str, Any], reused: Dict[str, Any]) -> float:
    """Add a reused row's spend to the tally and return its cost (removed from the row)."""
    spent = float(row.pop("cost", 0) or 0)
    for key in ("calls", "tokens_in", "tokens_out", "seconds"):
        reused[key] += row.get(key) or 0
    reused["cost"] += spent
    reused["cases"] += 1
    return spent


def score_one(scorer: Callable, fn: Callable, case: Dict[str, Any], meter: CallMeter) -> Tuple[Dict[str, Any], float]:
    """Score one case, metered: the row and the cost it spent."""
    before, t0, in0, out0, cost0 = meter.calls, time.time(), meter.tokens_in, meter.tokens_out, meter.cost_usd
    replayed0, reads0 = meter.calls_replayed, meter.reads.copy()
    try:
        row = scorer(fn, case)
    except BudgetExceeded:
        raise
    except Exception as exc:
        row = dict(ok=False, note=f"{type(exc).__name__}: {exc}")
    row.update(id=case["id"], area=case.get("area"), calls=meter.calls - before, seconds=round(time.time() - t0, 1),
               tokens_in=meter.tokens_in - in0, tokens_out=meter.tokens_out - out0)
    if meter.access and (bad := access.violation(meter.reads.minus(reads0), meter.access)):   # a read gate: the request fails
        row.update(ok=False, note=f"{bad}; {row.get('note', '')}".strip("; "))
    if meter.calls_replayed > replayed0:
        row["calls_replayed"] = meter.calls_replayed - replayed0
    return row, meter.cost_usd - cost0


def run_cases(cases: List[Dict[str, Any]], scorer: Callable, fn: Callable, meter: CallMeter, reuse: Dict[str, Any], log: Any,
              say: Callable[[str], None], stop_at_fail: bool) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    """Run the cases in order. Returns (rows, the spend carried over from reused rows, the reason it stopped early or '')."""
    rows: List[Dict[str, Any]] = []
    reused = new_reused()
    for case in cases:
        if str(case["id"]) in reuse:
            row = dict(reuse[str(case["id"])])
            spent = take_reused(row, reused)
            rows.append(row)
            log.case(row, spent, reused=True)
            say(f"[{row['id']:9}] {'PASS' if row['ok'] else 'FAIL'} reused from an earlier run of this implementation version")
            continue
        row, spent = score_one(scorer, fn, case, meter)
        rows.append(row)
        log.case(row, spent)
        say(f"[{row['id']:9}] {'PASS' if row['ok'] else 'FAIL'} calls={row['calls']} {row.get('got', '')} | {row.get('note', '')}")
        if stop_at_fail and not row["ok"]:
            return rows, reused, f"stopped at the first failing case, {row['id']}"
    return rows, reused, ""
