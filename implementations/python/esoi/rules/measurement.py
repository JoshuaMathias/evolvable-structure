"""Rules about measurement: S10, S12, S16, S20, S21, S22, S24 and S25.

S10 selection follows the measurements, S12 measured code is live, S16 provenance, S20 a complete solution with a
current recorded run, S21 every evaluation folder is a metric, S22 numbers live only in the results log, S24
recorded claims are true, S25 an invariant solution's cases are proved to discriminate.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List

from .. import leaderboard
from ..harness import current_sha
from ..records import FILES
from ..tables import ids
from .base import Context, RuleGroup, parse_file

ALTERNATIVE_MARKERS = ("ALTERNATIVE", "BASELINE", "ABLATION", "FLOOR", "VALIDITY")
# Counts of cases are numbers too: "56 offline cases" drifts the day a case is added.
NUMBER_IN_PROSE = re.compile(
    r"(?<![\w-])\d+\s*/\s*\d+(?![\w-])|\$\s?\d|\d+(?:\.\d+)?\s*%|\b\d+\s+of\s+\d+\b"
    r"|\b\d[\d,]*\s+(?:[a-z-]+\s+){0,2}?(?:cases?|scenarios?|queries|questions|tasks|fixtures?|logs|calls|"
    r"documents|sequences|names)\b")
# A sentence in a gap or action that claims a run is missing, or tells someone to make it (S24).
STALE_CLAIM = re.compile(r"\b(?:not|never) (?:yet )?recorded\b|\bunrecorded\b|\bno recorded\b|^\s*Record\b")

SUMMARIES = {
    "S10": "An eval solution's selected implementation has a recorded row and no rival beats it, or a waiver names "
           "the pending decision; an invariant solution is never ranked.",
    "S12": "Every evaluation implementation drives live package code or declares itself an alternative "
           "(ALTERNATIVE = True, or a docstring opening ALTERNATIVE, BASELINE, ABLATION, FLOOR or VALIDITY); a "
           "selected or measured implementation must be live, or waived.",
    "S16": "The latest results row of every implementation carries a cases_sha, or a waiver says why not.",
    "S20": "Every solution has a problem, an ideal, a metric, implementations, a selected implementation and a "
           "recorded run on the current cases with a git_sha; tests alone are not a metric.",
    "S21": "Every evaluation folder is named by some solution's metric command, or is listed as shared.",
    "S22": "No score, percentage, dollar amount or case count in a gap, an action, a waiver reason or a record field; "
           "numbers live in the results log.",
    "S24": "Every arm a metric command names has a results row, and a gap or action that says an implementation is "
           "not recorded names none that already has a row.",
    "S25": "An invariant solution's evaluation folder has a broken/ baseline module besides __init__.py.",
}


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


def record_prose(ctx: Context) -> List[tuple]:
    """(file, id, column, text) for every free-text field of the intent records, per the template."""
    sources = {"problems.csv": ctx.registry.problems, "ideals.csv": ctx.registry.ideals,
               "solutions.csv": ctx.registry.solutions, "implementations.csv": ctx.registry.implementations,
               "metrics.csv": ctx.registry.metrics}
    out = []
    for entity, (name, key) in FILES.items():
        columns = [t["field_key"] for t in ctx.template.get(entity, []) if t["group"] != "meta"]
        out += [(name, row.get(key, ""), col, row[col]) for row in sources[name] for col in columns if col in row]
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
        invariant = r.get("metric_kind", "").strip() == "invariant"
        better = [] if invariant else [x["impl"] for x in leaderboard.challengers(rows, sel, evaluation)]
        if better and not ctx.waived("S10", f"{r['solution_id']}:{','.join(sorted(better))}"):
            bad.append(f"S10 {r['solution_id']}: {', '.join(better)} beat the selected {sel} in the results log; "
                       "adopt the winner or add a waiver naming the pending decision")

    for r in ctx.solutions:
        sid = r["solution_id"]
        for comp, impl in ctx.harness_arms(r.get("metric_command", ""))[1:]:   # the first arm is S10's
            if impl not in results.get(comp, {}) and not ctx.waived("S24", f"{sid}:{impl}"):
                bad.append(f"S24 {sid}: the metric_command names {comp}/{impl}, which has no row in the results log "
                           "(record it, or name the recorded arm and say in the gap that the other is unrecorded)")
        recorded = set()
        for i in ids(r["implementations"]):
            im = re.match(re.escape(config.evaluation_dir) + r"/(\w+)/impls/(\w+)\.py$", i.split("::")[0])
            if im and im.group(2) in results.get(im.group(1), {}):
                recorded.add(im.group(2))
        for sentence in re.split(r"(?<=[.;])\s+", r["gap"] + " " + r["action"]):
            if not STALE_CLAIM.search(sentence):
                continue
            for stem in sorted(recorded):
                if re.search(rf"\b{re.escape(stem)}\b", sentence) and not ctx.waived("S24", f"{sid}:{stem}"):
                    bad.append(f"S24 {sid}: the gap or action says {stem} is not recorded, but the results log has a row "
                               f"for it ({sentence.strip()[:70]!r}); update the text")

    for r in ctx.solutions:
        sid = r["solution_id"]
        arms = ctx.harness_arms(r.get("metric_command", ""))
        if r.get("metric_kind", "").strip() != "invariant" or not arms:
            continue
        broken = evaluation / arms[0][0] / "broken"
        baselines = [f for f in broken.glob("*.py") if f.name != "__init__.py"] if broken.is_dir() else []
        if not baselines and not ctx.waived("S25", sid):
            bad.append(f"S25 {sid}: {config.evaluation_dir}/{arms[0][0]}/broken/ has no baseline module (add the naive "
                       "implementation a first draft would write; a test proves the cases fail it)")

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

    prose = [("solutions.csv", r["solution_id"], col, r[col]) for r in ctx.solutions for col in ("gap", "action") if col in r]
    prose += [("waivers.csv", f"{w['rule']} {w['path']}", "reason", w["reason"]) for w in ctx.registry.waivers]
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
            if not ctx.waived("S20", sid):
                bad.append(f"S20 {sid}: metric_command is not an `esoi run <component> --impl <name>` command "
                           "(a metric is a recorded run, not tests alone)")
            continue
        comp, sel = arms[0]
        row = results.get(comp, {}).get(sel)
        if row is None:
            continue   # S10 reports the missing row
        now = leaderboard.cases_digest(comp, evaluation)
        if not row.get("git_sha", "").strip():
            why = "its latest row has no git_sha"
        elif row.get("cases_sha", "") != now:
            why = f"its latest row was recorded on other cases (cases_sha {row.get('cases_sha') or 'blank'}, now {now})"
        elif ctx.strict and row["git_sha"].endswith("-dirty"):
            why = "its latest row was recorded on uncommitted code"
        else:
            continue
        if not ctx.waived("S20", sid):
            bad.append(f"S20 {sid}: {why}; re-run `esoi run {comp} --impl {sel} --record` on committed code")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
