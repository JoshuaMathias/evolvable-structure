"""Rules S41, S42, S44 and S45, advisory: a cascade runs ONE criterion at rising cost, and every stage's metric is one number.

Joshua, 2026-11-04: "that's not how cascade is used ... every stage metric must be a single number which represents what
alternative is best across all factors". The lesson is in ``docs/explanation/a-cascade-runs-one-criterion.md``. Each finding goes to
``esoi check --findings`` with its next action and never fails a check. Detectable from the records:

* S41: a metric with a cascade of two or more stages whose command scores more than one component. The cascade decides on the rows of the
  first component only, so the others are a second criterion beside it, not a stage of it.
* S42: a solution with two or more metrics that each have recorded results and rank the same arms in separate leaderboards.
* S45: the arm that scores best has a value outside the bounds the metric declares as degenerate
  (``[balance.<component>.diagnostics.<column>] min = .., max = ..``, read from the result row's numeric columns or its details'
  ``name=number`` pairs). No arm is ever excluded from selection: every implementation competes on the one balanced metric, and a trivial
  arm that wins means the metric lacks a factor. (S43, which refused to select an arm marked BASELINE or FLOOR, is retired.)
* S44: a ``[balance.<component>]`` table (weights and budgets) that changed in a later commit of ``esoi.toml`` than the date of the
  first row scored with it.

Not detectable from the records, so not checked: a solution with several metrics and no ``authoritative_metric_id`` is already rule R6
(inside S26); whether the metric is aimed at what the solution is for, and whether a stage's pass test hides a second criterion, need a
person's reading. A waiver excuses one key: the metric id (S41), the solution id (S42) or the component (S44, S45).
"""
from __future__ import annotations

import re
import subprocess
import tomllib
from typing import Dict, List, Tuple

from esoi.optimization.leaderboard import arm_kinds, rival_decisions, cascade_stages
from esoi.structure.intent_registry.tables import ids
from esoi.structure.structure_check.rules.base import Context, RuleGroup

SUMMARIES = {
    "S41": "Advisory: the stages of one metric's cascade are one number at rising fidelity, so the metric's command scores one component; "
           "a cascade whose command scores several has a second criterion beside it (waive as the metric id).",
    "S42": "Advisory: a solution whose several metrics each have recorded results for the same arms ranks them in separate leaderboards; "
           "make one metric authoritative and the others case sources of it (waive as the solution id).",
    "S44": "Advisory: a `[balance.<component>]` table (weights and budgets) was fixed before any alternative was scored, so it did not change "
           "in a commit dated after the first row scored with it (waive as the component).",
    "S45": "Advisory: the arm that scores best on the balanced metric is not degenerate by the diagnostics the metric declares "
           "(`[balance.<component>.diagnostics.<column>]` min and max); it informs and never excludes an arm (waive as the component).",
}


def single_number(ctx: Context) -> List[str]:
    out: List[str] = []
    for metric in ctx.registry.metrics:
        mid = metric.get("metric_id", "")
        stages, errors = cascade_stages.load_stages(ctx.config, metric)
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
        if rows and not arm_kinds.is_ablation(rows[-1], ctx.config.evaluation):
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


VALUE = re.compile(r"([A-Za-z_][\w.]*)\s*=\s*(-?\d+(?:\.\d+)?)")


def diagnostic_values(row: Dict[str, str]) -> Dict[str, float]:
    """The numbers a result row carries for a diagnostic to read: its numeric columns, and ``name=number`` pairs of its details."""
    found: Dict[str, float] = {}
    for key, value in row.items():
        try:
            found[key] = float(value)
        except (TypeError, ValueError):
            continue
    for key, value in VALUE.findall(row.get("details", "") or ""):
        found.setdefault(key, float(value))
    return found


def degenerate_leader(ctx: Context) -> List[str]:
    """S45: the arm that scores best is degenerate by the diagnostics the metric itself declares. Every arm competes on the one balanced
    metric and none is excluded; when a trivial arm (one card per file, say) wins, the metric is missing a factor, so this only informs."""
    out: List[str] = []
    for component, table in sorted(ctx.config.balance.items()):
        declared = (table or {}).get("diagnostics") or {}
        rows = {impl: found[-1] for impl, found in ctx.history.get(component, {}).items() if found}
        if not declared or not rows or ctx.waived("S45", component):
            continue
        leader, _ = rival_decisions.best_guess(rows, ctx.config.evaluation)
        if leader is None:
            continue
        values = diagnostic_values(rows[leader])
        for name, bound in sorted(declared.items()):
            value = values.get(name)
            if value is None:
                continue
            low, high = bound.get("min"), bound.get("max")
            if (low is not None and value < float(low)) or (high is not None and value > float(high)):
                limit = f"below {low}" if low is not None and value < float(low) else f"above {high}"
                out.append(f"S45 {component}: {leader} scores best but its {name} is {value:g}, {limit}, which the metric's own diagnostics "
                           f"([balance.{component}.diagnostics.{name}]) call degenerate. The arm is not excluded: the metric is missing the "
                           f"factor. Next: put {name} into the balanced score (weights and budgets in [balance.{component}]) and re-record, "
                           "or, if this arm is the right answer, change the diagnostic and say why")
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
    """Every finding goes to ``ctx.advisory``; none is a problem."""
    config = ctx.config
    if not config.intent_mode:
        return []
    bad: List[str] = []
    for rule, finder in (("S41", single_number), ("S42", separate_leaderboards), ("S44", weights_fixed_first), ("S45", degenerate_leader)):
        if config.is_disabled(rule):
            continue
        ctx.advisory.extend(finder(ctx))
    return bad


GROUP = RuleGroup(SUMMARIES, run)
