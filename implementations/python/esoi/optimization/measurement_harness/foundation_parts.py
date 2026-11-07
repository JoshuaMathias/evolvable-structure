"""A metric builds on the metric of the library it depends on: it measures on that foundation without re-running it.

A consumer of a library (a service that implements the library's seats) is judged on the cases the library already measures, plus cases of its
own (its real requests, its own source systems). Re-scoring the library's cases in the consumer, with a copy of the library's case files and
scorer, measures the same thing twice and lets the copy drift from the library. This module makes the consumer's metric BUILD ON the library's:

    [builds_on.context_selection.retrieval]          # <consumer component>.<a name for this foundation>
    repo = "../hub"                                   # the foundation's repository (it has its own esoi.toml)
    component = "context_retrieval"                   # the foundation's component, scored by ITS score.py
    share = 0.5                                       # the share of the consumer's number the foundation's cases carry
    on_stale = "run"                                  # "run" (default) or "report" when the recorded result cannot be reused
    arm_prefix = "lib_"                               # optional: the consumer's arm lib_<x> is the foundation's arm <x>

A consumer may build on several foundations (a selection metric and a bootstrap metric, say); the shares of all of them are below 1, and the
consumer's own cases carry the rest. Nothing here knows any particular library.

An arm says which foundation arm it is: ``FOUNDATION_ARMS = {"retrieval": "bm25_body"}`` in its module (or ``FOUNDATION_ARM = "bm25_body"`` when
there is one foundation). An arm that names none for a foundation does not build on it and the shares renormalise over the parts it has.

The rule when ``esoi run`` runs the consumer's arm over a whole set:

1. The consumer runs only its OWN cases (``load_cases`` of its score module holds no copy of the foundation's cases).
2. For each foundation the arm names, the foundation's latest whole-set row for that arm is REUSED when it is current by the foundation's own
   rule (``stale_reasons.stale_reason`` in the foundation's repository: same cases digest, committed code, the arm's code unchanged since its commit).
   Its per-case results join the consumer's per-case log; no foundation case is run.
3. When the row is missing or stale, nothing stale is mixed in. ``on_stale = "run"`` runs the foundation's cases through the FOUNDATION'S scorer
   (its ``score_case``, one code path): with the foundation's own build of the named arm, or, for an arm that names none, through the consumer
   score module's ``foundation_fn(foundation_name, fn)`` adapter (it returns None for a foundation the arm cannot be adapted to: the arm does not build on it). ``on_stale = "report"`` refuses the run and says why the foundation is stale.
4. The number is the blend of the parts at their shares: per-case accuracy, cost and seconds are weighted by share, then folded by the consumer's
   own ``[balance.<component>]`` (the weights stay the consumer's). The row records ``builds_on``: ``name=component:arm@git_sha/cases_sha`` for each
   part, and the row is STALE when the foundation's cases or the foundation arm's code changed since (``stale_reason``), so an improvement to the
   foundation (a new case kind, a scorer fix) reaches the consumer's number the next time it is run.
5. A sampled or ``--only`` run scores the consumer's own cases only and says so; composition is for whole sets.

Cascades: a consumer stage written ``name [inherits=stage]`` is passed only when the foundation's stage of that name passed for the foundation
arm (``inherited_gate``), so the consumer inherits the gate instead of re-proving it. A gate beside ``inherits`` tightens, never loosens (S47).
"""
from __future__ import annotations

import importlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import case_identity, results_log
from esoi.optimization.measurement_harness import arm_loading, balance, case_loading, component_folder, run_errors
from esoi.optimization.when_metrics_are_run.interface import BudgetExceeded
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import builds_on, code_provenance, stale_reasons
from esoi.structure.intent_registry.config import Config


@dataclass
class Part:
    """The foundation's contribution to one composed run."""
    name: str
    arm: str
    cases: int
    passed: float
    model_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost: Any = 0.0        # dollars, or "" when the foundation's price is unknown
    seconds: float = 0.0
    dev: str = ""
    heldout: str = ""
    how: str = "reused"    # reused | run
    identity: str = ""
    reason: str = ""       # why the recorded result was not reused
    per_case: List[Dict[str, Any]] = field(default_factory=list)


def recorded_part(f: builds_on.Foundation, arm: str) -> Tuple[Optional[Part], str]:
    """The foundation's latest whole-set row for ``arm`` as a part, or ``(None, why it cannot be reused)``."""
    fconf = builds_on.load_config(f)
    rows = [r for r in results_log.all_results(fconf.results_path).get(f.target, {}).get(arm, []) if not (r.get("sample") or "").strip()]
    if not rows:
        return None, f"the foundation has no recorded whole-set result for {arm}"
    row = rows[-1]
    if why := stale_reasons.stale_reason(fconf, f.target, row):
        return None, why
    return part_from_row(f, arm, row, fconf), ""


def part_from_row(f: builds_on.Foundation, arm: str, row: Dict[str, str], fconf: Config) -> Part:
    """A reused ``Part`` from the foundation's recorded whole-set row, with its per-case rows when they match the row's case count."""
    per = [dict(r) for r in results_log.per_case_rows(fconf)
           if (r["component"], r["impl"], r["cases_sha"], (r["sample"] or "").strip()) == (f.target, arm, row["cases_sha"], "")]
    cost = row.get("cost_usd", "")
    return Part(f.name, arm, int(float(row["cases"])), float(row["passed"]), int(float(row.get("model_calls") or 0)),
                int(float(row.get("tokens_in") or 0)), int(float(row.get("tokens_out") or 0)),
                float(cost) if cost not in ("", None) else "", float(row.get("seconds") or 0), row.get("dev", ""), row.get("heldout", ""),
                "reused", builds_on.identity(f, arm, row["git_sha"], row["cases_sha"]),
                per_case=per if len(per) == int(float(row["cases"])) else [])


def score_one(score: Any, fn: Callable, case: Dict[str, Any], meter: Any) -> Dict[str, Any]:
    """One foundation case through the foundation's scorer; a case that raises fails and the run goes on (a budget stop does not)."""
    before, t0 = meter.calls, time.time()
    try:
        row = score.score_case(fn, case)
    except BudgetExceeded:
        raise
    except Exception as exc:
        row = dict(ok=False, note=f"{type(exc).__name__}: {exc}")
    row.update(id=case["id"], calls=meter.calls - before, seconds=round(time.time() - t0, 1), heldout=bool(case.get("heldout")))
    return row


def run_summary(f: builds_on.Foundation, arm: str, rows: List[Dict[str, Any]], spend: Tuple[Any, Dict[str, Any], float], ident: str, reason: str) -> Part:
    """The ``Part`` a run of the foundation's cases makes: counts, what the meter spent since ``spend`` began, dev and held-out ratios."""
    meter, spent, started = spend
    held = [r for r in rows if r["heldout"]]
    return Part(f.name, arm, len(rows), float(sum(bool(r["ok"]) for r in rows)), meter.calls - spent["calls"],
                meter.tokens_in - spent["tin"], meter.tokens_out - spent["tout"], round(meter.cost_usd - spent["cost"], 6),
                round(time.time() - started, 1), f"{sum(bool(r['ok']) for r in rows if not r['heldout'])}/{len(rows) - len(held)}",
                f"{sum(bool(r['ok']) for r in held)}/{len(held)}", "run", ident, reason,
                [dict(case_id=str(r["id"]), ok="1" if r["ok"] else "0", calls=r["calls"], seconds=r["seconds"]) for r in rows])


def run_part(f: builds_on.Foundation, arm: str, consumer_fn: Callable, adapter: Optional[Callable], meter: Any, say: Callable[[str], None],
             reason: str) -> Optional[Part]:
    """Run the foundation's cases through the foundation's own scorer. With a named foundation arm it is the foundation's own build of that arm;
    without one the consumer's ``adapter(name, fn)`` turns the consumer's arm into what the foundation's scorer calls."""
    fconf = builds_on.load_config(f)
    component_folder.prepare_path(fconf)
    cases = case_loading.load_cases(f.target, fconf)
    score = importlib.import_module(f"{f.target}.score")
    fn = arm_loading.load_impl(arm, f.target, fconf)(meter) if arm else adapter(f.name, consumer_fn) if adapter is not None else None
    if fn is None:
        return None
    say(f"{f.name}: running {len(cases)} foundation case(s) through {f.root.name}'s {f.target} scorer ({reason})")
    spent = dict(calls=meter.calls, tin=meter.tokens_in, tout=meter.tokens_out, cost=meter.cost_usd)
    started = time.time()
    rows = [score_one(score, fn, case, meter) for case in cases]
    sha = code_provenance.current_sha(fconf, f.target, arm) if arm else code_provenance.current_sha(fconf)
    ident = builds_on.identity(f, arm or "(consumer arm)", sha, case_identity.cases_digest(f.target, fconf.evaluation))
    return run_summary(f, arm or "(consumer arm)", rows, (meter, spent, started), ident, reason)


def measure(config: Config, component: str, impl: str, consumer_fn: Callable, adapter: Optional[Callable], meter: Any,
            say: Callable[[str], None]) -> List[Part]:
    """The part each foundation contributes for this arm: reuse a current recorded result, else the policy's choice (see the module docstring)."""
    named, parts = builds_on.declared_arms(config, component, impl), []
    for f in builds_on.declared(config, component):
        arm = named.get(f.name, "")
        if not arm and adapter is None:
            say(f"{f.name}: this arm names no foundation arm and the score module has no adapter, so it does not build on {f.name}")
            continue
        found, why = recorded_part(f, arm) if arm else (None, "the arm names no foundation arm, so it is measured by the foundation's scorer")
        if found is not None:
            say(f"{f.name}: reused {found.cases} case(s) of {f.root.name}'s {f.target} for {arm} ({found.identity}); none run again")
            parts.append(found)
        elif f.on_stale == "report":
            raise run_errors.RunError(f"the foundation {f.name} cannot be reused: {why} (on_stale = report, so nothing is run; "
                                   f"re-record {arm or 'the foundation arm'} in {f.root.name} and run again)")
        elif (ran := run_part(f, arm, consumer_fn, adapter, meter, say, why)) is not None:
            parts.append(ran)
        else:
            say(f"{f.name}: this arm names no foundation arm and the score module's foundation_fn does not adapt it, so it does not build on {f.name}")
    return parts


def part_shares(own: Dict[str, Any], parts: List[Part], foundations: List[builds_on.Foundation]) -> Dict[str, float]:
    """Each part's share (the consumer's own cases are ``""``), renormalised over the parts present."""
    weights = {p.name: next(f.share for f in foundations if f.name == p.name) for p in parts}
    if own["cases"]:
        weights[""] = 1.0 - sum(f.share for f in foundations)
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def weighted_per_case(shares: Dict[str, float], own_cases: int, own_value: float, parts: List[Part], value_of: Callable[[Part], float]) -> float:
    """The share-weighted per-case figure: the consumer's own value per own case plus each part's value per its cases."""
    own_term = shares.get("", 0.0) * own_value / own_cases if own_cases else 0.0
    return own_term + sum(shares[p.name] * value_of(p) / p.cases for p in parts if p.cases)


def totals(own: Dict[str, Any], own_cost: Any, parts: List[Part], passed: float, cases: int) -> Dict[str, Any]:
    """The summed fields of the composed row: counts, tokens, seconds, cost, the dev and held-out ratios and the foundations' identities."""
    def column(name: str) -> list:
        return [getattr(p, name) for p in parts]
    return dict(cases=cases, passed=round(passed), model_calls=own["model_calls"] + sum(column("model_calls")),
                tokens_in=own["tokens_in"] + sum(column("tokens_in")), tokens_out=own["tokens_out"] + sum(column("tokens_out")),
                seconds=round(own["seconds"] + sum(column("seconds")), 1),
                cli_reported_cost_usd=round(float(own_cost or 0) + sum(float(c or 0) for c in column("cost")), 4),
                dev=sum_ratio([own["dev"]] + column("dev")), heldout=sum_ratio([own["heldout"]] + column("heldout")),
                builds_on=";".join(column("identity")))


def blend(own: Dict[str, Any], own_cost: Any, parts: List[Part], foundations: List[builds_on.Foundation], table: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The composed summary fields: parts and the consumer's own cases weighted by share (shares renormalised over the parts present), then
    folded by the consumer's ``[balance.<component>]``. ``own`` is the consumer's own run summary (``cases``, ``passed``, ``seconds`` ...)."""
    shares = part_shares(own, parts, foundations)
    cases = own["cases"] + sum(p.cases for p in parts)
    accuracy = weighted_per_case(shares, own["cases"], own["passed"], parts, lambda p: p.passed)
    unknown = (own["cases"] and own_cost == "") or any(p.cost == "" for p in parts)
    cost_pc = None if unknown else weighted_per_case(shares, own["cases"], float(own_cost or 0), parts, lambda p: float(p.cost))
    seconds_pc = weighted_per_case(shares, own["cases"], own["seconds"], parts, lambda p: p.seconds)
    out = totals(own, own_cost, parts, accuracy * cases, cases)
    if cost_pc is not None:
        out.update(balance.balanced(accuracy * cases, cases, cost_pc * cases, seconds_pc * cases, table))
    return out


def sum_ratio(cells: List[str]) -> str:
    done = total = 0
    for cell in cells:
        try:
            a, b = (int(x) for x in cell.split("/"))
        except ValueError:
            continue
        done, total = done + a, total + b
    return f"{done}/{total}"


def note_for(part: Part, share: float) -> str:
    accuracy = part.passed / part.cases if part.cases else 0.0
    how = "reused, none run again" if part.how == "reused" else f"run through the foundation's scorer ({part.reason})"
    return f"builds on {part.name} at share {share:g}: {part.cases} cases, accuracy {accuracy:.3f}, {how}"
