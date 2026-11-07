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

from esoi.optimization.leaderboard import arm_selection, case_identity, results_log, rival_decisions, switching_policy
from esoi.optimization.leaderboard.interface import held_out_parts, rival_pairing
from esoi.optimization.measurement_harness.interface import defect_reason, stale_reason
from esoi.optimization.when_metrics_are_run.interface import declares_simulated
from esoi.structure.intent_registry.records import FILES
from esoi.structure.intent_registry.registry import adopts
from esoi.structure.intent_registry.tables import ids
from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of
from esoi.structure.structure_check.rules.base import Context, RuleGroup

ALTERNATIVE_MARKERS = ("ALTERNATIVE", "ABLATION", "VALIDITY")
# Counts of cases are numbers too: "56 offline cases" drifts the day a case is added.
NUMBER_IN_PROSE = re.compile(
    r"(?<![\w-])\d+\s*/\s*\d+(?![\w-])|\$\s?\d|\d+(?:\.\d+)?\s*%|\b\d+\s+of\s+\d+\b"
    r"|\b\d[\d,]*\s+(?:[a-z-]+\s+){0,2}?(?:cases?|scenarios?|queries|questions|tasks|fixtures?|logs|calls|"
    r"documents|sequences|names)\b")

SUMMARIES = {
    "S10": "A measured solution's selected implementation has a recorded row and no rival beats it on the metric, or a "
           "waiver names the pending decision.",
    "S12": "Every evaluation implementation drives live package code or declares itself an alternative "
           "(ALTERNATIVE = True, or a docstring opening ALTERNATIVE, ABLATION or VALIDITY); a "
           "selected or measured implementation must be live, or waived.",
    "S16": "The latest results row of every implementation carries a cases_sha, or a waiver says why not.",
    "S20": "Every solution has a problem, an ideal, a metric, implementations, a selected implementation and a "
           "recorded run on the current cases with a git_sha (a solution whose metrics record no run is a specification and is not checked here). With --strict a run on code that "
           "changed since is advice only (it informs, never fails the check or blocks a commit), and so is a rival it was compared "
           "with (waive one rival as `<solution>:<implementation>`).",
    "S21": "Every evaluation folder is named by some solution's metric command, or is listed as shared.",
    "S22": "No score, percentage, dollar amount or case count in a waiver reason or a record field (a solution's milestones may state target values); "
           "numbers live in the results log.",
    "S24": "Every arm a metric command names has a results row.",
    "S25": "A solution whose evaluation folder has a single implementation, so nothing to compare it with, has a broken/ "
           "naive module besides __init__.py: the naive implementation a first draft would write, which the cases must fail.",
    "S31": "A metric is meaningfully real: no implementation in a metric's evaluation folder declares SIMULATED = True, and "
           "no metric record describes its judge or model as scripted, simulated, mocked or a stand-in (or a waiver "
           "names why that metric cannot be real).",
}
# A metric record that admits its judge or model is not the real one (S31).
UNREAL_METRIC = re.compile(r"\b(?:scripted|simulated|mocked|stubbed|fake|canned)\s+(?:judge|model|grader|stand-in|replies|reply|answers?)\b"
                           r"|\bstand-in\b", re.I)


def declares_alternative(tree: ast.Module) -> bool:
    """True when the module sets ``ALTERNATIVE = True`` or its docstring opens with an alternative marker."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ALTERNATIVE" for t in node.targets):
            if isinstance(node.value, ast.Constant) and node.value.value is True:
                return True
    doc = (ast.get_docstring(tree) or "").lstrip().upper()
    return any(doc.startswith(m) for m in ALTERNATIVE_MARKERS)


def drives_live_code(ctx: Context, tree: ast.Module) -> bool:
    """True when the module imports a live package or calls one of the configured live calls."""
    live_imports, live_calls = set(ctx.config.live_imports), set(ctx.config.live_calls)
    return any(node_is_live(node, live_imports, live_calls) for node in nodes_of(tree))


def node_is_live(node: ast.AST, live_imports: set, live_calls: set) -> bool:
    """Whether one syntax node imports a live package or names a live call."""
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").split(".")[0] in live_imports
    if isinstance(node, ast.Import):
        return any(a.name.split(".")[0] in live_imports for a in node.names)
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and f"{node.value.id}.{node.attr}" in live_calls


def impl_kind(ctx: Context, path: Path) -> str:
    """Classify an evaluation implementation file: ``alternative`` (declares itself an alternative),
    ``live`` (imports or drives package code) or ``unclear`` (neither)."""
    tree = tree_of(path)
    if tree is None:
        return "unclear"
    if declares_alternative(tree):
        return "alternative"
    return "live" if drives_live_code(ctx, tree) else "unclear"


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


def check_live_code(ctx: Context) -> List[str]:
    """S12: every evaluation implementation is live or declares itself an alternative, and a selected or measured one is live."""
    bad: List[str] = []
    config = ctx.config
    kinds: Dict[str, str] = {}
    for impl_path in sorted(config.evaluation.glob("*/impls/*.py")):
        if impl_path.name == "__init__.py":
            continue
        rel = str(impl_path.relative_to(config.root))
        kinds[rel] = impl_kind(ctx, impl_path)
        if kinds[rel] == "unclear" and not ctx.waived("S12", rel):
            bad.append(f"S12 {rel}: neither wraps live {config.package or 'package'} code nor declares itself an "
                       "alternative (set ALTERNATIVE = True, or open the docstring with ALTERNATIVE/ABLATION/"
                       "VALIDITY): the number would not measure the live code")
    for r in ctx.solutions:
        bad += alternative_problems(ctx, r, kinds)
    return bad


def alternative_problems(ctx: Context, r: Dict[str, str], kinds: Dict[str, str]) -> List[str]:
    """S12 for one solution whose selected or measured implementation is an alternative, not live code."""
    bad: List[str] = []
    sel = r["selected"].split("::")[0]
    if kinds.get(sel) == "alternative" and not ctx.waived("S12", f"{r['solution_id']}:{Path(sel).stem}"):
        bad.append(f"S12 {r['solution_id']}: selected {sel} is an alternative, not live code; select the live "
                   "implementation or add a waiver naming the decision")
    arms = ctx.harness_arms(r.get("metric_command", ""))
    if arms:
        measured = f"{ctx.config.evaluation_dir}/{arms[0][0]}/impls/{arms[0][1]}.py"
        if kinds.get(measured) == "alternative" and not ctx.waived("S12", f"{r['solution_id']}:{arms[0][1]}"):
            bad.append(f"S12 {r['solution_id']}: the measured implementation {measured} is an alternative, not "
                       "live code, so the recorded number would not be the selected one's")
    return bad


def check_provenance(ctx: Context) -> List[str]:
    """S16: the latest results row of every implementation carries a cases_sha."""
    return [f"S16 {comp}/{impl}: latest results row has no cases_sha (re-run with --record, "
            "or add a waiver saying why it cannot be re-run)"
            for comp, rows in sorted(ctx.results.items()) for impl, row in sorted(rows.items())
            if case_identity.unverified(row) and not ctx.waived("S16", f"{comp}/{impl}")]


def check_selection(ctx: Context) -> List[str]:
    """S10: a selected implementation has a recorded row and no rival beats it on the metric."""
    bad: List[str] = []
    config, results = ctx.config, ctx.results
    per_case = results_log.per_case_rows(config)
    chosen = switching_policy.policies(config, ctx.registry, per_case)
    for r in ctx.solutions:
        if ctx.harness_arms(r.get("metric_command", "")):
            bad += rival_problems(ctx, r, per_case, chosen)
    return bad


def rival_problems(ctx: Context, r: Dict[str, str], per_case, chosen) -> List[str]:
    """S10 for one measured solution: its selected implementation has a row, and no rival beats it on the metric."""
    config = ctx.config
    comp, sel = arm_selection.selected_arm(config, r, "", ctx.registry)   # the records' `selected`, not the command's order
    if sel not in ctx.results.get(comp, {}):
        if not ctx.waived("S10", f"{r['solution_id']}:unmeasured"):   # advice: a measurement is made when it is worth its cost
            ctx.advisory.append(f"S10 {r['solution_id']}: selected {sel} has no row in the results log (run with --record when a decision needs it)")
        return []
    pick_history, pick_policy = held_out_parts.selection_view(ctx.history.get(comp, {}), per_case, chosen.get(comp) or switching_policy.Policy())
    if sel not in pick_history:
        return []
    better = [x["impl"] for x in rival_decisions.challengers({i: rs[-1] for i, rs in pick_history.items()}, sel, config.evaluation, pick_history, per_case, pick_policy)]
    if better and not ctx.waived("S10", f"{r['solution_id']}:{','.join(sorted(better))}"):
        return [f"S10 {r['solution_id']}: {', '.join(better)} beat the selected {sel} in the results log; "
                "adopt the winner or add a waiver naming the pending decision"]
    return []


def check_arms_have_rows(ctx: Context) -> List[str]:
    """S24: every arm a metric command names (after the first, which S10 reports) has a results row."""
    return [f"S24 {r['solution_id']}: the metric_command names {comp}/{impl}, which has no row in the results log "
            "(record it, or waive it naming why)"
            for r in ctx.solutions for comp, impl in ctx.harness_arms(r.get("metric_command", ""))[1:]
            if impl not in ctx.results.get(comp, {}) and not ctx.waived("S24", f"{r['solution_id']}:{impl}")]


def check_naive_baselines(ctx: Context) -> List[str]:
    """S25: a metric with a single implementation has a naive module in broken/ for the cases to fail."""
    bad: List[str] = []
    evaluation = ctx.config.evaluation
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
            bad.append(f"S25 {sid}: {ctx.config.evaluation_dir}/{arms[0][0]}/broken/ has no naive module (add the naive "
                       "implementation a first draft would write; a test proves the cases fail it)")
    return bad


def simulated_problems(ctx: Context, r: Dict[str, str]) -> List[str]:
    """S31 for the implementations a solution's harness command measures that declare SIMULATED = True."""
    bad: List[str] = []
    config, sid = ctx.config, r["solution_id"]
    for comp in sorted({c for c, _ in ctx.harness_arms(r.get("metric_command", ""))}):
        for impl_path in sorted((config.evaluation / comp / "impls").glob("*.py")):
            if impl_path.name != "__init__.py" and declares_simulated(impl_path) and not ctx.waived("S31", f"{sid}:{impl_path.stem}"):
                bad.append(f"S31 {sid}: {config.evaluation_dir}/{comp}/impls/{impl_path.name} declares SIMULATED = True, "
                           "so the metric measures a scripted stand-in, not the real thing; measure real behaviour on "
                           "real inputs (a real model call, real data), keep the scripted version as a unit test, or "
                           "waive naming why this metric cannot be real")
    return bad


def check_real_metrics(ctx: Context) -> List[str]:
    """S31: no implementation declares SIMULATED = True and no metric record admits a scripted stand-in."""
    bad: List[str] = []
    for r in ctx.solutions:
        bad += simulated_problems(ctx, r)
    for m in ctx.registry.metrics:
        for col in ("purpose", "record"):
            hit = UNREAL_METRIC.search(m.get(col, ""))
            if hit and not ctx.waived("S31", m.get("metric_id", "")):
                bad.append(f"S31 metrics.csv {m.get('metric_id', '')}: `{col}` says {hit.group(0)!r}; a metric must measure "
                           "the real thing (real model, real inputs and outputs), so change the metric or waive naming why")
    return bad


def check_evaluation_folders(ctx: Context) -> List[str]:
    """S21: every evaluation folder is named by some solution's metric command, or is listed as shared."""
    config, evaluation = ctx.config, ctx.config.evaluation
    if not evaluation.is_dir():
        return []
    metric_text = " ".join(r.get("metric_command", "") + " " + r.get("metric", "") for r in ctx.solutions)
    named = {comp for r in ctx.solutions for comp, _ in ctx.harness_arms(r.get("metric_command", ""))}
    return [f"S21 {config.evaluation_dir}/{folder.name}: no solutions.csv metric_command or declared arm names this "
            "folder; make it a solution's metric or delete it"
            for folder in sorted(p for p in evaluation.iterdir() if p.is_dir())
            if folder.name not in config.shared_eval_dirs and folder.name not in named
            and not re.search(re.escape(config.evaluation_dir) + rf"/{re.escape(folder.name)}\b", metric_text)]


def check_numbers_in_prose(ctx: Context) -> List[str]:
    """S22: no score, percentage, dollar amount or case count in a waiver reason or a record field."""
    bad: List[str] = []
    prose = [("waivers.csv", f"{w['rule']} {w['path']}", "reason", w["reason"]) for w in ctx.registry.waivers]
    prose += record_prose(ctx)
    seen = set()
    for where, ident, col, text in prose:
        hit = NUMBER_IN_PROSE.search(text)
        if hit and (where, ident, col) not in seen:
            seen.add((where, ident, col))
            bad.append(f"S22 {where} {ident}: `{col}` states a number ({hit.group(0)!r}); numbers live in the results "
                       "log and the leaderboard, so name what was measured instead")
    return bad


def empty_solution_fields(ctx: Context, r: Dict[str, str]) -> List[str]:
    """S20 lines for each field a solution needs and leaves empty, and for a solution that lists no implementation."""
    sid = r["solution_id"]
    needed = ("selected",) if ctx.waived("S26", sid) else ("metric_ids", "selected") if adopts(r) \
        else ("problem_ids", "ideal_ids", "metric_ids", "selected")   # an adopted solution's problems and ideals are the library's
    bad: List[str] = []
    for col in needed:
        parent = {"problem_ids": "parent_problem_ids", "ideal_ids": "parent_ideal_ids"}.get(col)
        if parent and r.get(parent, "").strip():
            continue   # the problem or ideal is named in the overall network
        if col in r and not r[col].strip():
            bad.append(f"S20 {sid}: `{col}` is empty (a solution needs a problem, an ideal, a metric and a selected implementation)")
    if not ids(r["implementations"]):
        bad.append(f"S20 {sid}: lists no implementation")
    return bad


def rival_advice(ctx: Context, sid: str, comp: str, sel: str) -> None:
    """Advice (--strict only) on rivals the verdict compares with that are stale or not comparable."""
    results = ctx.results.get(comp, {})
    for impl, rival_why in rival_pairing.stale_rivals(ctx.config, comp, results, sel, stale_reason, ctx.history.get(comp)):
        waived = ctx.waived("S20", f"{sid}:{impl}")   # in use now, though only --strict reports the finding
        if ctx.strict and not waived:   # information: a changed file never fails the check or blocks a commit
            ctx.advisory.append(f"S20 {sid}: the verdict compares {sel} with rival {impl}, but {rival_why}; "
                                f"re-run `esoi run {comp} --impl {impl} --record` when a decision depends on the comparison")
    for impl, rival_why in rival_pairing.incomparable_rivals(results, sel, ctx.config.evaluation, ctx.history.get(comp)):
        waived = ctx.waived("S20", f"{sid}:{impl}")
        if ctx.strict and not waived:
            ctx.advisory.append(f"S20 {sid}: rival {impl} is not comparable with {sel} ({rival_why}); "
                                f"record both on the same sample when a decision depends on the comparison")


def recorded_run_problems(ctx: Context, r: Dict[str, str]) -> List[str]:
    """S20 for a solution's selected implementation: a malformed row is a problem, a stale one is advice."""
    sid = r["solution_id"]
    arms = ctx.harness_arms(r.get("metric_command", ""))
    if not arms:
        return []   # no command that records a run: a specification, not a finding
    comp, sel = arms[0]
    row = ctx.results.get(comp, {}).get(sel)
    if row is None:
        return []   # S10 reports the missing row
    rival_advice(ctx, sid, comp, sel)
    defect = defect_reason(ctx.config, comp, row)   # a malformed row (no commit, unreadable circumstances) is a problem
    if defect:
        return [] if ctx.waived("S20", sid) else [f"S20 {sid}: {defect}; re-run `esoi run {comp} --impl {sel} --record` on committed code"]
    changed = stale_reason(ctx.config, comp, row, True)   # other cases, other circumstances, changed or dirty code: advice, never a problem
    if changed and not ctx.waived("S20", sid):
        ctx.advisory.append(f"S20 {sid}: {changed}; re-run `esoi run {comp} --impl {sel} --record` when a decision or release depends on it")
    return []


def check_complete_solutions(ctx: Context) -> List[str]:
    """S20: every solution has its fields, implementations and a current recorded run."""
    bad: List[str] = []
    for r in ctx.solutions:
        bad += empty_solution_fields(ctx, r)
        bad += recorded_run_problems(ctx, r)
    return bad


def run(ctx: Context) -> List[str]:
    bad: List[str] = []
    for check in (check_live_code, check_provenance, check_selection, check_arms_have_rows, check_naive_baselines,
                  check_real_metrics, check_evaluation_folders, check_numbers_in_prose, check_complete_solutions):
        bad += check(ctx)
    return bad


GROUP = RuleGroup(SUMMARIES, run)
