"""Derive and record the per-circumstance rows and the per-case log of a recorded run."""
from __future__ import annotations

from typing import Any, Dict, List

from esoi.optimization.leaderboard.interface import circumstances
from esoi.optimization.leaderboard.case_identity import cases_digest
from esoi.optimization.measurement_harness import balance
from esoi.optimization.measurement_harness.per_case_log import write_per_case
from esoi.optimization.measurement_harness.record_result import record_result
from esoi.optimization.measurement_harness.run_cost import run_cost
from esoi.runtime.assemble_by_name.interface import check_name
from esoi.structure.intent_registry.config import Config


def cost_weights(rows: List[Dict[str, Any]]) -> List[float]:
    """How a run's cost is shared among its cases: by tokens, else by model calls, else equally."""
    for field_name in ("tokens_in", "calls"):
        weights = [float(r.get(field_name) or 0) + (float(r.get("tokens_out") or 0) if field_name == "tokens_in" else 0) for r in rows]
        if sum(weights) > 0:
            return weights
    return [1.0] * len(rows)


def case_balanced_scores(config: Config, component: str, summary: Dict[str, Any], rows: List[Dict[str, Any]]) -> List[float]:
    """The balanced score of each case of a run (``balance.case_scores``): the run's cost shared out by tokens (by model calls, else
    equally, when no tokens were counted). Empty when the component sets no balance or the price is unknown, as for the run's own
    balanced score."""
    cost = run_cost(config, summary, summary.get("model"))
    table = config.balance.get(component)
    if table is None or cost == "" or cost is None or not rows:
        return []
    weights = cost_weights(rows)
    share = [float(cost) * w / sum(weights) for w in weights]
    return balance.case_scores([bool(r["ok"]) for r in rows], share, [float(r["seconds"]) for r in rows], table)


def record_slices(config: Config, component: str, circs: List[circumstances.Circumstance], summary: Dict[str, Any],
                  cases: List[dict], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The derived rows of a recorded run, one per circumstance it satisfies and has cases in (``slice:<id>``, or
    ``sample:N/slice:<id>``), appended to the results log, and the run's per-case log (written for every recorded run, because
    the leaderboard's paired test needs each case's outcome; a component with no circumstances gets no derived rows). A slice costs no model call: it is a sum over the cases the run already scored."""
    key = dict(component=component, impl=summary["impl"], cases_sha=cases_digest(component, config.evaluation),
               circumstances_sha=circumstances.digest(circs) if circs else "", sample=summary["sample"])
    scores = case_balanced_scores(config, component, summary, rows)
    write_per_case(config, [dict(key, case_id=str(c["id"]), heldout="yes" if c.get("heldout") else "", ok="1" if r["ok"] else "0",
                                 calls=r["calls"], tokens_in=r["tokens_in"], tokens_out=r["tokens_out"], seconds=r["seconds"],
                                 circumstances=";".join(circumstances.case_circumstances(circs, c)),
                                 score=scores[i] if scores else "") for i, (c, r) in enumerate(zip(cases, rows))])
    if not circs:
        return []   # no circumstances: no derived slice rows, but the per-case outcomes still support the paired test
    total = (summary["tokens_in"] + summary["tokens_out"]) or 0
    written = []
    for cid, found in circumstances.slices(circs, cases, circumstances.run_context(summary.get("model"), summary["impl"])).items():
        check_name(cid, "slice id")   # a '/' or ';' would make the row read as a whole run
        piece = slice_row(config, component, summary, cases, rows, cid, found, total)
        record_result(piece, config)
        written.append(piece)
    return written


def dev_and_held(cases: List[dict], rows: List[Dict[str, Any]], found: List[int]) -> Dict[str, str]:
    """The ``passed/total`` of the development cases and of the held-out cases among a slice."""
    dev = [i for i in found if not cases[i].get("heldout")]
    held = [i for i in found if cases[i].get("heldout")]
    return dict(dev=f"{sum(bool(rows[i]['ok']) for i in dev)}/{len(dev)}", heldout=f"{sum(bool(rows[i]['ok']) for i in held)}/{len(held)}")


def token_share(part: List[Dict[str, Any]], total: int, in_slice: int, in_run: int) -> float:
    """The part of a run's cost a slice carries: its share of the tokens, or of the cases when no tokens were counted."""
    return sum(r["tokens_in"] + r["tokens_out"] for r in part) / total if total else in_slice / in_run


def slice_row(config: Config, component: str, summary: Dict[str, Any], cases: List[dict], rows: List[Dict[str, Any]], cid: str,
              found: List[int], total: int) -> Dict[str, Any]:
    """The derived result row of one slice: sums over the cases it holds, cost shared by token use, scored again."""
    part = [rows[i] for i in found]
    share = token_share(part, total, len(found), len(rows))
    piece = dict(summary, cases=len(found), passed=sum(bool(r["ok"]) for r in part), **dev_and_held(cases, rows, found),
                 model_calls=sum(r["calls"] for r in part), tokens_in=sum(r["tokens_in"] for r in part),
                 tokens_out=sum(r["tokens_out"] for r in part), seconds=round(sum(r["seconds"] for r in part), 1),
                 cli_reported_cost_usd=round(summary["cli_reported_cost_usd"] * share, 4),
                 sample=(summary["sample"] + "/" if summary["sample"] else "") + f"slice:{cid}", details="derived from the run of the same date")
    for stale_key in ("balanced", "accuracy", "cost_per_case", "seconds_per_case"):
        piece.pop(stale_key, None)
    piece.update(balance.balanced(piece["passed"], piece["cases"], run_cost(config, piece, piece["model"]), piece["seconds"],
                                  config.balance.get(component)))
    return piece
