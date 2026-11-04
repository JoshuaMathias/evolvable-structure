"""Rules S41 to S44, advisory: a cascade runs ONE criterion at rising cost, and every stage's metric is one number.

Joshua, 2026-11-04: "that's not how cascade is used ... every stage metric must be a single number which represents what
alternative is best across all factors". The lesson is in ``docs/explanation/a-cascade-runs-one-criterion.md``. Each finding goes to
``esoi check --findings`` with its next action and never fails a check, except S43 where ``[rules.S43] problem = true`` (the
repository opts in). Detectable from the records:

* S41: a metric with a cascade of two or more stages whose command scores more than one component. The cascade decides on the rows of the
  first component only, so the others are a second criterion beside it, not a stage of it.
* S42: a solution with two or more metrics that each have recorded results and rank the same arms in separate leaderboards.
* S43: a solution whose ``selected`` names an arm marked ``BASELINE`` or ``FLOOR`` (a floor that exists to show a floor).
* S44: a ``[balance.<component>]`` table (weights and budgets) that changed in a later commit of ``esoi.toml`` than the date of the
  first row scored with it.

Not detectable from the records, so not checked: a solution with several metrics and no ``authoritative_metric_id`` is already rule R6
(inside S26); whether the metric is aimed at what the solution is for, and whether a stage's pass test hides a second criterion, need a
person's reading. A waiver excuses one key: the metric id (S41), the solution id (S42, S43) or the component (S44).
"""
from __future__ import annotations

import subprocess
import tomllib
from typing import Dict, List, Tuple

from .. import cascade, leaderboard
from ..tables import ids
from .base import Context, RuleGroup

SUMMARIES = {
    "S41": "Advisory: the stages of one metric's cascade are one number at rising fidelity, so the metric's command scores one component; "
           "a cascade whose command scores several has a second criterion beside it (waive as the metric id).",
    "S42": "Advisory: a solution whose several metrics each have recorded results for the same arms ranks them in separate leaderboards; "
           "make one metric authoritative and the others case sources of it (waive as the solution id).",
    "S43": "Advisory (a problem with `[rules.S43] problem = true`): no solution selects an arm marked BASELINE or FLOOR, which only shows a "
           "floor (waive as the solution id).",
    "S44": "Advisory: a `[balance.<component>]` table (weights and budgets) was fixed before any alternative was scored, so it did not change "
           "in a commit dated after the first row scored with it (waive as the component).",
}


def single_number(ctx: Context) -> List[str]:
    out: List[str] = []
    for metric in ctx.registry.metrics:
        mid = metric.get("metric_id", "")
        stages, errors = cascade.load_stages(ctx.config, metric)
        components = list(dict.fromkeys(c for c, _ in ctx.harness_arms(metric.get("command", ""))))
        if errors or len([s for s in stages if not s.unrun]) < 2 or len(components) < 2 or ctx.waived("S41", mid):
            continue
        out.append(f"S41 {mid}: its cascade has {len(stages)} stages but its command scores {len(components)} components "
                   f"({', '.join(components)}); the cascade decides on the rows of {components[0]} only, so the others are a second criterion beside it. "
                   "Stages of one metric must be the same number at rising fidelity: make the others case sources of one component "
                   "(mixed in proportion to real inputs), or split them into separate metrics of separate solutions, then run `esoi cascade`")
    return out


def recorded_arms(ctx: Context, metric: Dict[str, str]) -> Tuple[str, ...]:
    """The rival arms (not ablation or validity arms) a metric's command names that have a recorded row, as a sorted tuple."""
    found = set()
    for component, impl in ctx.harness_arms(metric.get("command", "")):
        rows = ctx.history.get(component, {}).get(impl)
        if rows and not leaderboard.is_ablation(rows[-1], ctx.config.evaluation):
            found.add(impl)
    return tuple(sorted(found))


def separate_leaderboards(ctx: Context) -> List[str]:
    out: List[str] = []
    by_id = {m.get("metric_id", ""): m for m in ctx.registry.metrics}
    for solution in ctx.registry.every_solution():
        sid = solution.get("solution_id", "")
        mine = [by_id[m] for m in ids(solution.get("metric_ids", "")) if m in by_id]
        arms = {m["metric_id"]: recorded_arms(ctx, m) for m in mine}
        grouped: Dict[Tuple[str, ...], List[str]] = {}
        for mid, found in arms.items():
            if len(found) >= 2:
                grouped.setdefault(found, []).append(mid)
        for found, metrics in grouped.items():
            if len(metrics) < 2 or ctx.waived("S42", sid):
                continue
            chosen = (solution.get("authoritative_metric_id") or "").strip()
            say = (f"{chosen} is authoritative, so make the others case sources of it" if chosen in metrics
                   else "name one `authoritative_metric_id` and make the others case sources of it")
            out.append(f"S42 {sid}: metrics {', '.join(metrics)} each rank the same arms ({', '.join(found)}) in separate leaderboards; "
                       f"one solution has one best, so {say} (cases of each kind mixed in proportion to real inputs, one balanced score), "
                       "not stages with their own pass tests and not separate leaderboards")
    return out


def floor_arms(ctx: Context) -> List[str]:
    out: List[str] = []
    problem = bool(ctx.config.option("S43", "problem", False))
    for solution in ctx.registry.every_solution():
        sid = solution.get("solution_id", "")
        component, arm = leaderboard.selected_arm(ctx.config, solution, "", ctx.registry)
        rows = ctx.history.get(component, {}).get(arm) if component else None
        if not rows or ctx.waived("S43", sid):
            continue
        kind = leaderboard.arm_kind(rows[-1], ctx.config.evaluation)
        if kind in leaderboard.FLOOR_KINDS:
            line = (f"S43 {sid}: selected {arm} is marked {kind.upper()}, a floor that shows what the live arms must beat and is never "
                    "selected; next: select the best live arm (`esoi select --promote`), or remove the marker if this arm is the product")
            out.append(line)
    return out


def git_lines(ctx: Context, *args: str) -> List[str]:
    try:
        done = subprocess.run(["git", "-C", str(ctx.root), *args], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    return done.stdout.splitlines() if done.returncode == 0 else []


def config_file(ctx: Context) -> str:
    return ctx.config.source.name if ctx.config.source else "esoi.toml"


def balance_tables(ctx: Context, sha: str) -> Dict[str, dict]:
    text = "\n".join(git_lines(ctx, "show", f"{sha}:./{config_file(ctx)}"))
    try:
        return tomllib.loads(text).get("balance", {}) or {}
    except tomllib.TOMLDecodeError:
        return {}


def weights_fixed_first(ctx: Context) -> List[str]:
    out: List[str] = []
    scored: Dict[str, str] = {}
    for component in ctx.config.balance:
        dates = [r.get("date", "")[:10] for rows in ctx.history.get(component, {}).values() for r in rows
                 if str(r.get("balanced") or "").strip() and r.get("date")]
        if dates:
            scored[component] = min(dates)
    if not scored:
        return out
    commits = [line.split(" ", 1) for line in git_lines(ctx, "log", "--reverse", "--format=%H %cs", "--", config_file(ctx))]
    previous: Dict[str, dict] = {}
    changed: Dict[str, str] = {}   # component -> date of the latest commit that changed its table after it had one
    for sha, day in commits:
        tables = balance_tables(ctx, sha)
        for component in scored:
            now = tables.get(component)
            if now is not None and previous.get(component) is not None and now != previous[component]:
                changed[component] = day
            if now is not None:
                previous[component] = now
    for component, first in sorted(scored.items()):
        day = changed.get(component)
        if day and day > first and not ctx.waived("S44", component):
            out.append(f"S44 {component}: its [balance.{component}] table changed in a commit dated {day}, after the first row scored with it "
                       f"({first}); weights and budgets must be fixed before any alternative is scored, or every earlier row ranks on another "
                       f"criterion. Next: restore the earlier table, or re-record the arms on the new one (`esoi run --stale --plan`) and say why in the table's comment")
    return out


def run(ctx: Context) -> List[str]:
    """Every finding goes to ``ctx.advisory``; S43 is a problem only where ``[rules.S43] problem = true``."""
    config = ctx.config
    if not config.intent_mode:
        return []
    bad: List[str] = []
    for rule, finder in (("S41", single_number), ("S42", separate_leaderboards), ("S43", floor_arms), ("S44", weights_fixed_first)):
        if config.is_disabled(rule):
            continue
        found = finder(ctx)
        if rule == "S43" and config.option("S43", "problem", False):
            bad.extend(found)
        else:
            ctx.advisory.extend(found)
    return bad


GROUP = RuleGroup(SUMMARIES, run)
