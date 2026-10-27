"""Rules about measurement: S10, S12, S16, S20, S21, S22, S24, S25 and S31.

S10 selection follows the measurements, S12 measured code is live, S16 provenance, S20 a complete solution with a
current recorded run, S21 every evaluation folder is a metric, S22 numbers live only in the results log, S24
recorded claims are true, S25 an invariant solution's cases are proved to discriminate, S31 a metric measures the real
thing rather than a scripted or simulated stand-in for it.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List

from .. import leaderboard
from ..harness import declares_simulated, stale_reason
from ..records import FILES
from ..tables import ids
from .base import Context, RuleGroup, parse_file

ALTERNATIVE_MARKERS = ("ALTERNATIVE", "BASELINE", "ABLATION", "FLOOR", "VALIDITY")
# Counts of cases are numbers too: "56 offline cases" drifts the day a case is added.
NUMBER_IN_PROSE = re.compile(
    r"(?<![\w-])\d+\s*/\s*\d+(?![\w-])|\$\s?\d|\d+(?:\.\d+)?\s*%|\b\d+\s+of\s+\d+\b"
    r"|\b\d[\d,]*\s+(?:[a-z-]+\s+){0,2}?(?:cases?|scenarios?|queries|questions|tasks|fixtures?|logs|calls|"
    r"documents|sequences|names)\b")

SUMMARIES = {
    "S10": "A measured solution's selected implementation has a recorded row and no rival beats it on the metric, or a "
           "waiver names the pending decision.",
    "S12": "Every evaluation implementation drives live package code or declares itself an alternative "
           "(ALTERNATIVE = True, or a docstring opening ALTERNATIVE, BASELINE, ABLATION, FLOOR or VALIDITY); a "
           "selected or measured implementation must be live, or waived.",
    "S16": "The latest results row of every implementation carries a cases_sha, or a waiver says why not.",
    "S20": "Every solution has a problem, an ideal, a metric, implementations, a selected implementation and a "
           "recorded run on the current cases with a git_sha (a solution whose metrics record no run is a specification and is not checked here). With --strict the run must "
           "also be on committed code that has not changed since, and so must every rival it was compared with "
           "(waive one rival as `<solution>:<implementation>`).",
    "S21": "Every evaluation folder is named by some solution's metric command, or is listed as shared.",
    "S22": "No score, percentage, dollar amount or case count in a waiver reason or a record field (a solution's milestones may state target values); "
           "numbers live in the results log.",
    "S24": "Every arm a metric command names has a results row.",
    "S25": "A solution whose evaluation folder has a single implementation, so nothing to compare it with, has a broken/ "
           "baseline module besides __init__.py: the naive implementation a first draft would write, which the cases must fail.",
    "S31": "A metric is meaningfully real: no implementation in a metric's evaluation folder declares SIMULATED = True, and "
           "no metric record describes its judge or model as scripted, simulated, mocked or a stand-in (or a waiver "
           "names why that metric cannot be real).",
}
# A metric record that admits its judge or model is not the real one (S31).
UNREAL_METRIC = re.compile(r"\b(?:scripted|simulated|mocked|stubbed|fake|canned)\s+(?:judge|model|grader|stand-in|replies|reply|answers?)\b"
                           r"|\bstand-in\b", re.I)


def impl_kind(ctx: Context, path: Path) -> str:
    """Classify an evaluation implementation file: ``alternative`` (declares itself a baseline or alternative),
    ``live`` (imports or drives package code) or ``unclear`` (neither)."""
    tree = parse_file(path)
    if tree is None:
        return "unclear"
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ALTERNATIVE" for t in node.targets):
            if isinstance(node.value, ast.Constant) and node.value.value is True:
                return "alternative"
    doc = (ast.get_docstring(tree) or "").lstrip().upper()
    if any(doc.startswith(m) for m in ALTERNATIVE_MARKERS):
        return "alternative"
    live_imports, live_calls = set(ctx.config.live_imports), set(ctx.config.live_calls)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in live_imports:
            return "live"
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] in live_imports for a in node.names):
            return "live"
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and f"{node.value.id}.{node.attr}" in live_calls:
            return "live"
    return "unclear"


# A milestone is a value of a metric, so its target value is the one number a record field may carry.
NUMBERS_ALLOWED = {("solutions.csv", "milestones")}


def record_prose(ctx: Context) -> List[tuple]:
    """(file, id, column, text) for every free-text field of the intent records, per the template, except the
    fields that state target values (``NUMBERS_ALLOWED``)."""
    sources = {"problems.csv": ctx.registry.problems, "ideals.csv": ctx.registry.ideals,
               "solutions.csv": ctx.registry.solutions, "implementations.csv": ctx.registry.implementations,
               "metrics.csv": ctx.registry.metrics}
    out = []
    for entity, (name, key) in FILES.items():
        columns = [t["field_key"] for t in ctx.template.get(entity, []) if t["group"] != "meta"]
        out += [(name, row.get(key, ""), col, row[col]) for row in sources[name] for col in columns
                if col in row and (name, col) not in NUMBERS_ALLOWED]
    return out


def run(ctx: Context) -> List[str]:
    bad: List[str] = []
    config, results = ctx.config, ctx.results
    evaluation = config.evaluation

    kinds: Dict[str, str] = {}
    for impl_path in sorted(evaluation.glob("*/impls/*.py")):
        if impl_path.name == "__init__.py":
            continue
        rel = str(impl_path.relative_to(config.root))
        kinds[rel] = impl_kind(ctx, impl_path)
        if kinds[rel] == "unclear" and not ctx.waived("S12", rel):
            bad.append(f"S12 {rel}: neither wraps live {config.package or 'package'} code nor declares itself an "
                       "alternative (set ALTERNATIVE = True, or open the docstring with ALTERNATIVE/BASELINE/"
                       "ABLATION/FLOOR/VALIDITY): the number would not measure the live code")
    for r in ctx.solutions:
        sel = r["selected"].split("::")[0]
        if sel in kinds and kinds[sel] == "alternative" and not ctx.waived("S12", f"{r['solution_id']}:{Path(sel).stem}"):
            bad.append(f"S12 {r['solution_id']}: selected {sel} is an alternative, not live code; select the live "
                       "implementation or add a waiver naming the decision")
        arms = ctx.harness_arms(r.get("metric_command", ""))
        if arms:
            measured = f"{config.evaluation_dir}/{arms[0][0]}/impls/{arms[0][1]}.py"
            if kinds.get(measured) == "alternative" and not ctx.waived("S12", f"{r['solution_id']}:{arms[0][1]}"):
                bad.append(f"S12 {r['solution_id']}: the measured implementation {measured} is an alternative, not "
                           "live code, so the recorded number would not be the selected one's")

    for comp, rows in sorted(results.items()):
        for impl, row in sorted(rows.items()):
            if leaderboard.unverified(row) and not ctx.waived("S16", f"{comp}/{impl}"):
                bad.append(f"S16 {comp}/{impl}: latest results row has no cases_sha (re-run with --record, "
                           "or add a waiver saying why it cannot be re-run)")

    for r in ctx.solutions:
        arms = ctx.harness_arms(r.get("metric_command", ""))
        if not arms:
            continue
        comp, sel = arms[0]
        rows = results.get(comp, {})
        if sel not in rows:
            if not ctx.waived("S10", f"{r['solution_id']}:unmeasured"):
                bad.append(f"S10 {r['solution_id']}: selected {sel} has no row in the results log (run with --record)")
            continue
        better = [x["impl"] for x in leaderboard.challengers(rows, sel, evaluation, ctx.history.get(comp))]
        if better and not ctx.waived("S10", f"{r['solution_id']}:{','.join(sorted(better))}"):
            bad.append(f"S10 {r['solution_id']}: {', '.join(better)} beat the selected {sel} in the results log; "
                       "adopt the winner or add a waiver naming the pending decision")

    for r in ctx.solutions:
        sid = r["solution_id"]
        for comp, impl in ctx.harness_arms(r.get("metric_command", ""))[1:]:   # the first arm is S10's
            if impl not in results.get(comp, {}) and not ctx.waived("S24", f"{sid}:{impl}"):
                bad.append(f"S24 {sid}: the metric_command names {comp}/{impl}, which has no row in the results log "
                           "(record it, or waive it naming why)")

    for r in ctx.solutions:
        sid = r["solution_id"]
        arms = ctx.harness_arms(r.get("metric_command", ""))
        if not arms:
            continue
        own = [f for f in (evaluation / arms[0][0] / "impls").glob("*.py") if f.name != "__init__.py"]
        if len(own) != 1:
            continue
        broken = evaluation / arms[0][0] / "broken"
        baselines = [f for f in broken.glob("*.py") if f.name != "__init__.py"] if broken.is_dir() else []
        if not baselines and not ctx.waived("S25", sid):
            bad.append(f"S25 {sid}: {config.evaluation_dir}/{arms[0][0]}/broken/ has no baseline module (add the naive "
                       "implementation a first draft would write; a test proves the cases fail it)")

    for r in ctx.solutions:
        sid = r["solution_id"]
        for comp in sorted({c for c, _ in ctx.harness_arms(r.get("metric_command", ""))}):
            for impl_path in sorted((evaluation / comp / "impls").glob("*.py")):
                if impl_path.name != "__init__.py" and declares_simulated(impl_path) and not ctx.waived("S31", f"{sid}:{impl_path.stem}"):
                    bad.append(f"S31 {sid}: {config.evaluation_dir}/{comp}/impls/{impl_path.name} declares SIMULATED = True, "
                               "so the metric measures a scripted stand-in, not the real thing; measure real behaviour on "
                               "real inputs (a real model call, real data), keep the scripted version as a unit test, or "
                               "waive naming why this metric cannot be real")
    for m in ctx.registry.metrics:
        for col in ("purpose", "record"):
            hit = UNREAL_METRIC.search(m.get(col, ""))
            if hit and not ctx.waived("S31", m.get("metric_id", "")):
                bad.append(f"S31 metrics.csv {m.get('metric_id', '')}: `{col}` says {hit.group(0)!r}; a metric must measure "
                           "the real thing (real model, real inputs and outputs), so change the metric or waive naming why")

    metric_text = " ".join(r.get("metric_command", "") + " " + r.get("metric", "") for r in ctx.solutions)
    if evaluation.is_dir():
        named = {comp for r in ctx.solutions for comp, _ in ctx.harness_arms(r.get("metric_command", ""))}
        for folder in sorted(p for p in evaluation.iterdir() if p.is_dir()):
            name = folder.name
            if name in config.shared_eval_dirs:
                continue
            if name not in named and not re.search(re.escape(config.evaluation_dir) + rf"/{re.escape(name)}\b", metric_text):
                bad.append(f"S21 {config.evaluation_dir}/{name}: no solutions.csv metric_command or declared arm names this "
                           "folder; make it a solution's metric or delete it")

    prose = [("waivers.csv", f"{w['rule']} {w['path']}", "reason", w["reason"]) for w in ctx.registry.waivers]
    prose += record_prose(ctx)
    seen = set()
    for where, ident, col, text in prose:
        hit = NUMBER_IN_PROSE.search(text)
        if hit and (where, ident, col) not in seen:
            seen.add((where, ident, col))
            bad.append(f"S22 {where} {ident}: `{col}` states a number ({hit.group(0)!r}); numbers live in the results "
                       "log and the leaderboard, so name what was measured instead")

    for r in ctx.solutions:
        sid = r["solution_id"]
        needed = ("selected",) if ctx.waived("S26", sid) else ("problem_ids", "ideal_ids", "metric_ids", "selected")
        for col in needed:
            parent = {"problem_ids": "parent_problem_ids", "ideal_ids": "parent_ideal_ids"}.get(col)
            if parent and r.get(parent, "").strip():
                continue   # the problem or ideal is named in the overall network
            if col in r and not r[col].strip():
                bad.append(f"S20 {sid}: `{col}` is empty (a solution needs a problem, an ideal, a metric and a selected implementation)")
        if not ids(r["implementations"]):
            bad.append(f"S20 {sid}: lists no implementation")
        arms = ctx.harness_arms(r.get("metric_command", ""))
        if not arms:
            continue   # no command that records a run: a specification, not a finding
        comp, sel = arms[0]
        row = results.get(comp, {}).get(sel)
        if row is None:
            continue   # S10 reports the missing row
        for impl, rival_why in leaderboard.stale_rivals(config, comp, results.get(comp, {}), sel, stale_reason,
                                                          ctx.history.get(comp)):
            waived = ctx.waived("S20", f"{sid}:{impl}")   # in use now, though only --strict reports the finding
            if ctx.strict and not waived:
                bad.append(f"S20 {sid}: the verdict compares {sel} with rival {impl}, but {rival_why}; re-run "
                           f"`esoi run {comp} --impl {impl} --record` on committed code")
        for impl, rival_why in leaderboard.incomparable_rivals(results.get(comp, {}), sel, config.evaluation,
                                                                ctx.history.get(comp)):
            waived = ctx.waived("S20", f"{sid}:{impl}")
            if ctx.strict and not waived:
                bad.append(f"S20 {sid}: rival {impl} is not comparable with {sel} ({rival_why}); re-run "
                           f"`esoi run --stale` so both are recorded on the same sample")
        why = stale_reason(config, comp, row, ctx.strict)
        if not why:
            if not ctx.strict and stale_reason(config, comp, row, True):
                ctx.waived("S20", sid)   # strict-only: a waiver for it is in use now, not unused
            continue
        if not ctx.waived("S20", sid):
            bad.append(f"S20 {sid}: {why}; re-run `esoi run {comp} --impl {sel} --record` on committed code")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
