"""Build the review tracker: the intent network as five tabs (problems, solutions, implementations, ideals,
metrics) in ``<structure>/tracker/``, generated from the registry and the results log.

Each tab is a CSV, importable as one tab of a spreadsheet (``esoi sheet-sync`` keeps one in step). Structural
columns are regenerated and must match the registry (rule S17); the ``tracking_*`` columns are the reviewers'
own notes and are preserved across rebuilds (blank means "use auto_status"). The tracker is a view: nothing but
rule S17 reads it, and it is never a second source of truth for anything but those review columns.

    esoi tracker build           # rewrite the tabs, keeping tracking_* columns
    esoi tracker check           # exit 1 when a tab is out of date
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import arm_kinds, arm_selection, results_log, verdict_labels
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import header_union
from esoi.structure.intent_registry.records import (
    INTENT_LINK_COLUMNS,
    PARENT_COLUMNS,
    POLICY_COLUMNS,
    fields,
    implementation_id,
    match_implementations,
)
from esoi.structure.intent_registry.registry import Registry, first_arm
from esoi.runtime.implementation_selection.select import Table, load_table
from esoi.structure.intent_registry.tables import SEP, ids, is_command, read_csv, read_header, render_csv
from esoi.structure.intent_registry.template_sync.template import load_for

TRACKING = ["tracking_status", "tracking_owner", "tracking_updated", "tracking_notes"]
TABS = ["problems", "solutions", "implementations", "ideals", "metrics"]
# What a solution's verdict means for its status (the leaderboard decides; see verdict_labels.verdict).
STATUS_BY_VERDICT = {"WIN": "decided-by-metric", "TIE": "tie-kept", "LOSS": "beaten-by-rival",
                     "UNMEASURED": "no-rival-measured"}
ALTERNATIVE_MARKERS = ("ALTERNATIVE", "ABLATION", "VALIDITY")
Row = Dict[str, str]


def extras(config: Config) -> Dict[str, List[str]]:
    """Extra record columns each tab carries after its key: the repository's own (``tracker_extra`` in the
    configuration) and the parent-link columns (``parent_problem_ids`` ...) when the record file has them."""
    out: Dict[str, List[str]] = {}
    for tab in TABS:
        names = list(config.tracker_extra.get(tab, []))
        header = header_union(config, f"{tab}.csv")
        wanted = (["intent_id"] if config.intent_mode else []) + [*PARENT_COLUMNS, *POLICY_COLUMNS, *INTENT_LINK_COLUMNS]
        out[tab] = names + [c for c in wanted if (c in header or c == "intent_id") and c not in names]
    return out


def columns(template, extra: Optional[Dict[str, List[str]]] = None) -> Dict[str, List[str]]:
    """The columns of each tab: the key, the extras, the template's fields, then the structural and status columns."""
    def own(entity: str) -> List[str]:
        return fields(template, entity, interface_required=True)
    base = columns_without_extras(own)
    extra = extra or {}
    return {tab: cols[:1] + extra.get(tab, []) + cols[1:] for tab, cols in base.items()}


def columns_without_extras(own) -> Dict[str, List[str]]:
    return {
        "problems": ["problem_id"] + own("problem") + ["solution_ids", "ideal_ids", "component_ids", "auto_status"],
        "solutions": ["solution_id"] + own("solution") + [
            "problem_ids", "ideal_ids", "metric_ids", "implementation_ids", "interface_name", "selected_implementation_id",
            "authoritative_metric_id", "verdict", "verdict_detail", "component_ids", "auto_status"],
        "implementations": ["implementation_id", "solution_id", "filepath"] + own("implementation") + [
            "kind", "selected", "latest_result", "latest_cost_usd", "cases_sha", "auto_status"],
        "ideals": ["ideal_id", "scope"] + own("ideal") + ["problem_ids", "solution_ids", "metric_ids", "auto_status"],
        "metrics": ["metric_id"] + own("metric") + ["solution_ids", "command", "latest_result", "auto_status"]}


def stem(path: str) -> str:
    """The implementation name a path stands for: the name after ``::`` when several implementations share a
    module (``providers.py::openai``), else the file name without ``.py``."""
    if "::" in path:
        return path.partition("::")[2]
    return re.sub(r"\.py$", "", path.rsplit("/", 1)[-1])


def kind_of(config: Config, path: str) -> str:
    """ablation / validity / alternative / live for an implementation path (documentation, not a gate)."""
    found = re.match(re.escape(config.evaluation_dir) + r"/(\w+)/impls/(\w+)\.py$", path)
    if found:
        tagged = arm_kinds.arm_kind({"component": found.group(1), "impl": found.group(2)}, config.evaluation)
        if tagged:
            return tagged
    full = config.root / path.partition("::")[0]
    if full.suffix != ".py" or not full.exists():
        return "live"
    text = full.read_text(encoding="utf-8", errors="replace")
    head = text[:600].lstrip().lstrip('"').lstrip().upper()
    if any(head.startswith(m) for m in ALTERNATIVE_MARKERS) \
            or re.search(r"^ALTERNATIVE\s*=\s*True", text, re.M):
        return "alternative"
    return "live"


def selected_path(config: Config, solution: Row, table: Optional[Table]) -> str:
    """The implementation path a solution's ``selected`` cell stands for: a selection-table name is resolved to its
    module file, any other value is already a path."""
    entry = (table or {}).get(solution["solution_id"])
    if not entry:
        return solution.get("selected", "")
    ref = entry["implementations"].get(solution.get("selected", ""))
    if ref is None:
        return solution.get("selected", "")
    target = ref["target"] if isinstance(ref, dict) else ref
    return config.module_path(target.partition(":")[0])


def is_selected_path(path: str, chosen: str, selected: str) -> bool:
    """Whether an ``implementations`` entry is the selected one: the same path, or, for ``module::name``, the entry of
    that module named by the selection (a module may hold several implementations)."""
    if path == chosen:
        return True
    module, _, name = path.partition("::")
    return bool(name) and module == chosen and name == selected


def selection_table(config: Config) -> Optional[Table]:
    """The configured selection table, or None when there is none or it cannot load (rule S14 reports that)."""
    if not config.selection_table:
        return None
    try:
        return load_table(config.selection_table, config.root)
    except Exception:
        return None


@dataclass
class Sources:
    """What the five tabs are built from: the registry, the template columns, the results log and the lookups over them."""
    config: Config
    registry: Registry
    template: Dict[str, List[Row]]
    extra: Dict[str, List[str]]
    cols: Dict[str, List[str]]
    table: Optional[Table]
    results: Dict[tuple, Row]
    verdicts: Dict[str, Row]
    impl_records: Dict[str, Row]
    metric_by_id: Dict[str, Row]
    sol_by_id: Dict[str, Row]
    by_solution: Dict[str, List[str]]

    def command_of(self, s: Row) -> str:
        """The metric commands of a solution, joined."""
        return SEP.join(self.metric_by_id[m]["command"] for m in ids(s.get("metric_ids", "")) if m in self.metric_by_id)


def load_sources(config: Config, registry: Registry, template=None) -> Sources:
    """Gather everything ``build`` reads."""
    template = template or load_for(config)
    extra = extras(config)
    by_solution: Dict[str, List[str]] = {}
    for comp in registry.components:
        for sid in ids(comp["solutions"]):
            by_solution.setdefault(sid, []).append(comp["component_id"])
    return Sources(
        config, registry, template, extra, columns(template, extra), selection_table(config),
        {(c, i): row for c, rows in results_log.latest_results(config.results_path).items() for i, row in rows.items()},
        verdict_labels.solution_verdicts(config, registry.solutions, registry=registry),
        {r["implementation_id"]: r for r in registry.implementations}, {m["metric_id"]: m for m in registry.metrics},
        {s["solution_id"]: s for s in registry.every_solution()}, by_solution)


def problem_rows(src: Sources) -> List[Row]:
    """One row per problem, with the components that serve it and whether every solution of it is measured."""
    rows = []
    for p in src.registry.problems:
        linked = [src.sol_by_id[s] for s in ids(p.get("solution_ids", "")) if s in src.sol_by_id]
        open_ones = [s["solution_id"] for s in linked if not is_command(src.command_of(s), src.config.metric_command)]
        rows.append({**{k: p.get(k, "") for k in src.cols["problems"]},
                     "component_ids": SEP.join(sorted({c for s in linked for c in src.by_solution.get(s["solution_id"], [])})),
                     "auto_status": "open: unmeasured " + ", ".join(open_ones) if open_ones else "served"})
    return rows


def implementation_rows(src: Sources, s: Row, comp: str, chosen_impl: str) -> Tuple[List[Row], List[str], str]:
    """The implementation rows of one solution, their ids, and the id of the selected one."""
    sid = s["solution_id"]
    rows, impl_ids, selected_id = [], [], ""
    chosen = selected_path(src.config, s, src.table)
    entries = ids(s.get("implementations", ""))
    claimed, _ = match_implementations(sid, entries, {i: r for i, r in src.impl_records.items() if r.get("solution_id") == sid})
    for path in entries:
        iid = claimed.get(path) or implementation_id(sid, path)
        impl_ids.append(iid)
        is_sel = is_selected_path(path, chosen, s.get("selected", ""))
        selected_id = iid if is_sel else selected_id
        res = src.results.get((comp, stem(path))) if comp else None
        rec = src.impl_records.get(iid, {})
        rows.append({
            "implementation_id": iid, "solution_id": sid, "filepath": path,
            **{k: rec.get(k, "") for k in src.extra["implementations"]},
            **{k: rec.get(k, "") for k in fields(src.template, "implementation", True)}, "kind": kind_of(src.config, path),
            "selected": "yes" if is_sel else "",
            "latest_result": f"{res.get('passed', '')}/{res.get('cases', '')}" if res else "",
            "latest_cost_usd": res.get("cost_usd", "") if res else "",
            "cases_sha": res.get("cases_sha", "") if res else "",
            "auto_status": "selected" if is_sel else ("measured" if res else "unmeasured")})
    return rows, impl_ids, selected_id


def solution_row(src: Sources, s: Row, impl_ids: List[str], selected_id: str, has_metric: bool, measured: bool) -> Row:
    """The solution tab row: its fields, its implementations, its verdict and its status."""
    sid = s["solution_id"]
    verdict = src.verdicts.get(sid, {})
    return {
        **{k: s.get(k, "") for k in src.extra["solutions"]},
        **{k: s.get(k, "") for k in ["solution_id"] + fields(src.template, "solution", True)
           + ["problem_ids", "ideal_ids", "metric_ids", "interface_name", "authoritative_metric_id"]},
        "implementation_ids": SEP.join(impl_ids), "selected_implementation_id": selected_id,
        "verdict": verdict.get("verdict", ""), "verdict_detail": verdict.get("detail", ""),
        "component_ids": SEP.join(src.by_solution.get(sid, [])),
        "auto_status": "specification" if not has_metric
        else (STATUS_BY_VERDICT.get(verdict.get("verdict", ""), "decided-by-hand") if measured else "decided-by-hand")}


def solution_and_implementation_rows(src: Sources) -> Tuple[List[Row], List[Row], Dict[str, List[tuple]]]:
    """The solution and implementation rows, and for each metric the solutions that use it with their selected run."""
    sol_rows, impls = [], []
    metric_users: Dict[str, List[tuple]] = {}
    for s in src.registry.every_solution():
        command = src.command_of(s)
        has_metric = is_command(command, src.config.metric_command)
        comp, chosen_impl = arm_selection.selected_arm(src.config, {**s, "metric_command": command}, "", src.registry)
        rows, impl_ids, selected_id = implementation_rows(src, s, comp, chosen_impl)
        impls += rows
        sel_res = src.results.get((comp, chosen_impl)) if comp else None
        sol_rows.append(solution_row(src, s, impl_ids, selected_id, has_metric, bool(sel_res)))
        for mid in ids(s.get("metric_ids", "")):
            if mid in src.metric_by_id:
                metric_users.setdefault(mid, []).append((s, sel_res, has_metric))
    return sol_rows, impls, metric_users


def metric_row(src: Sources, mid: str, users: List[tuple]) -> Row:
    """The row of one metric, however many solutions it serves."""
    m = src.metric_by_id[mid]
    many = len(users) > 1
    texts = [(f"{u[0]['solution_id']}: " if many else "") + f"{u[1].get('passed', '')}/{u[1].get('cases', '')}" for u in users if u[1]]
    return {
        **{k: m.get(k, "") for k in src.extra["metrics"]},
        **{k: m.get(k, "") for k in ["metric_id"] + fields(src.template, "metric", True) + ["solution_ids", "command"]},
        "latest_result": " ".join(t for t in texts if t) if many else (texts[0] if texts else ""),
        "auto_status": "specification" if not any(u[2] for u in users)
        else "measured" if any(u[1] for u in users)
        else ("needs_run" if any(u[2] for u in users) else "needs_metric")}


def metric_rows(src: Sources, metric_users: Dict[str, List[tuple]]) -> List[Row]:
    """One row per metric, however many solutions it serves."""
    return [metric_row(src, mid, users) for mid, users in metric_users.items()]


def ideal_rows(src: Sources) -> List[Row]:
    """One row per ideal of the solutions, then one per principle of the whole repository."""
    solutions_of_ideal: Dict[str, List[str]] = {}
    for s in src.registry.every_solution():
        for iid in ids(s.get("ideal_ids", "")):
            solutions_of_ideal.setdefault(iid, []).append(s["solution_id"])
    rows = []
    for i in src.registry.ideals:
        sids = solutions_of_ideal.get(i["ideal_id"], [])
        measured = any(first_arm(src.config, src.command_of(src.sol_by_id[sid]))[0] for sid in sids)
        rows.append({**{k: i.get(k, "") for k in src.extra["ideals"]},
                     **{k: i.get(k, "") for k in ["ideal_id"] + fields(src.template, "ideal", True) + ["problem_ids"]},
                     "scope": "solution", "solution_ids": SEP.join(sids),
                     "metric_ids": SEP.join(m for sid in sids for m in ids(src.sol_by_id[sid].get("metric_ids", ""))),
                     "auto_status": "measured" if measured else "unmeasured"})
    for p in src.registry.principles:
        rows.append({"ideal_id": p["principle_id"].lower(), "scope": "principle", "name": p.get("name", ""),
                     "principle": p.get("statement", ""), "state_description": "",
                     "hints_of_measurement": p.get("how_measured", ""), "problem_ids": "",
                     "solution_ids": "the whole repo", "metric_ids": "",
                     "auto_status": "enforced-by-check" if "(S" in p.get("how_measured", "") else "behaviour-eval"})
    return rows


def build(config: Config, registry: Registry, template=None) -> Dict[str, List[Row]]:
    """The five tabs, from the first-class records (problems, solutions, implementations, ideals, metrics)."""
    src = load_sources(config, registry, template)
    sol_rows, impls, metric_users = solution_and_implementation_rows(src)
    return {"problems": problem_rows(src), "solutions": sol_rows, "implementations": impls,
            "ideals": ideal_rows(src), "metrics": metric_rows(src, metric_users)}


def merge_tracking(config: Config, tab: str, rows: List[Row], key: str) -> List[Row]:
    """Carry the hand-edited ``tracking_*`` columns of the committed tab over to the rebuilt rows."""
    old = {r.get(key, ""): r for r in read_csv(config.tracker_dir / f"{tab}.csv")}
    for r in rows:
        for col in TRACKING:
            r[col] = old.get(r[key], {}).get(col, "")
    return rows


def stale(config: Config, registry: Registry, template=None) -> List[str]:
    """Tabs whose structural columns differ from what the registry now produces."""
    template = template or load_for(config)
    cols = columns(template, extras(config))
    out = []
    for tab, rows in build(config, registry, template).items():
        have = read_csv(config.tracker_dir / f"{tab}.csv")
        want = merge_tracking(config, tab, rows, cols[tab][0])
        path = config.tracker_dir / f"{tab}.csv"
        header_ok = bool(have) and read_header(path) == cols[tab] + TRACKING
        if [{k: r.get(k, "") for k in cols[tab]} for r in have] != [{k: r.get(k, "") for k in cols[tab]} for r in want] \
                or (have and not header_ok) or (not have and want):
            out.append(tab)
    return out


def write(config: Config, registry: Registry, say=print) -> None:
    template = load_for(config)
    cols = columns(template, extras(config))
    config.tracker_dir.mkdir(parents=True, exist_ok=True)
    for tab, rows in build(config, registry, template).items():
        rows = merge_tracking(config, tab, rows, cols[tab][0])
        (config.tracker_dir / f"{tab}.csv").write_text(render_csv(cols[tab] + TRACKING, rows), encoding="utf-8")
        say(f"{tab}: {len(rows)} rows")
