"""Rules about the registry's own shape: S7, S11, S14, S18, S19 and S23.

S7 solutions, S11 metric kinds and links, S14 selection table, S18 unique ids, S19 every component serves a
solution, S23 the selected implementation is the selection table's default.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import List

from ..registry import RULE_COLUMNS
from ..tables import ids
from .base import Context, RuleGroup

SOLUTION_KINDS = {"eval", "invariant"}
PORT_CLASS = re.compile(r"^class (\w+)\((?:[\w, ]*)Protocol", re.M)

SUMMARIES = {
    "S7": "Every Protocol class is in the port cell of some solution; implementation paths and metric scripts "
          "exist; selected is a listed implementation or a selection-table name; no metric means a gap and an action.",
    "S11": "Every solution is eval or invariant (an invariant states invariant_reason), is linked from some "
           "component, and every linked id exists.",
    "S14": "Every solution with a port has a selection-table entry and no entry lacks a row; a default, when the entry "
           "holds one, is one of its implementations and each implementation's module is listed in the row's implementations cell or "
           "in the `path` of one of its implementations.csv records (several implementations may share a module).",
    "S18": "Solution and component ids are unique and no id repeats inside one cell.",
    "S19": "Every component names at least one solution.",
    "S23": "For a solution whose selection-table entry still holds a `default`, selected equals it (an entry with no "
           "`default` takes the records' `selected`, so there is nothing to compare).",
}


def ports_in_package(ctx: Context) -> set:
    config = ctx.config
    if not config.package_dir:
        return set()
    found = set()
    for path in sorted((config.root / config.package_dir).rglob("*.py")):
        if "/vendor/" in str(path):
            continue
        found.update(n for n in PORT_CLASS.findall(path.read_text(encoding="utf-8")) if not n.startswith("_"))
    return found


FILE_RULE = {"components.csv": "S2", "solutions.csv": "S7", "waivers.csv": "S9"}


def listed_modules(ctx: Context, solution_id: str, row: dict) -> set:
    """The module files a solution lists: the paths in its ``implementations`` cell and the ``path`` of each of its
    ``implementations.csv`` records (``path::name`` counts as ``path``), so one module may hold several of them."""
    paths = ids(row.get("implementations", ""))
    paths += [r.get("path", "") for r in ctx.registry.implementations if r.get("solution_id") == solution_id]
    return {p.split("::")[0].strip() for p in paths if p.strip()}


def missing_columns(ctx: Context, needs_port: bool) -> List[str]:
    """One problem per column the rules read that a registry file lacks (``port`` only when something needs it)."""
    folder = ctx.config.structure_dir
    bad = []
    for name, column in ctx.registry.missing:
        if column in RULE_COLUMNS.get(name, []) or needs_port:
            bad.append(f"{FILE_RULE[name]} {folder}/{name}: has no `{column}` column, which the rules read "
                       "(add it to the header; `esoi template sync` regenerates the header templates)")
    return bad


def run(ctx: Context) -> List[str]:
    bad: List[str] = []
    config, table = ctx.config, ctx.table or {}
    bad += missing_columns(ctx, bool(table) or bool(ports_in_package(ctx)))
    if ctx.table_error:
        bad.append(f"S14 {config.selection_table}: cannot load ({ctx.table_error})")
    covered = set()
    for r in ctx.solutions:
        sid = r["solution_id"]
        covered.update(ids(r.get("port", "")))
        records = [x for x in ctx.registry.implementations if x.get("solution_id") == sid]
        suffixes = {x.get("implementation_id", "").partition(":")[2] for x in records} - {""}
        impls = ids(r["implementations"]) + sorted(suffixes) + [x.get("implementation_id", "") for x in records] \
            + [x["path"].strip() for x in records if x.get("path", "").strip()]
        if sid in table:
            names = table[sid].get("implementations", {})
            if r["selected"] and r["selected"] not in names:
                bad.append(f"S7 {sid}: selected {r['selected']!r} is not an implementation name in the selection "
                           f"table (choices: {', '.join(sorted(names))})")
        elif r["selected"] and r["selected"] not in impls:
            bad.append(f"S7 {sid}: selected {r['selected']!r} is not among its implementations")
        for i in impls:
            if "/" in i and not (config.root / i.split("::")[0]).exists():
                bad.append(f"S7 {sid}: implementation path {i} does not exist")
        mc = r.get("metric_command", "").strip()
        arms = ctx.harness_arms(mc)
        if arms:
            comp, impl = arms[0]
            declared = impl in suffixes   # an implementation declared in code needs no wrapper file
            if not (config.evaluation / comp / "score.py").exists() or not (
                    declared or (config.evaluation / comp / "impls" / f"{impl}.py").exists()):
                bad.append(f"S7 {sid}: harness command names {comp}/{impl}, which has no score.py or impls file "
                           "(and no implementation of that name declared in code)")
        if mc and not mc.startswith("none"):
            words = mc.split()
            target = words[1] if mc.startswith("python") and len(words) > 1 else words[0]
            if target.endswith(".py") and not (config.root / target).exists():
                bad.append(f"S7 {sid}: metric script {target} does not exist")
        elif not (r["gap"].strip() and r["action"].strip()):
            bad.append(f"S7 {sid}: no metric, so gap and action are required")
    for p in sorted(ports_in_package(ctx) - covered):
        bad.append(f"S7 {p}: port is listed in the `port` cell of no solutions.csv row (add it to the row of the "
                   "solution it serves; a port needs no row of its own)")

    sol_ids = {r["solution_id"] for r in ctx.every_solution()}   # a component may serve a specification solution too
    for r in ctx.solutions:
        sid, kind = r["solution_id"], r.get("metric_kind", "").strip()
        if kind not in SOLUTION_KINDS:
            bad.append(f"S11 {sid}: solution metric_kind {kind!r} not in {sorted(SOLUTION_KINDS)}")
        elif kind == "invariant" and not r.get("invariant_reason", "").strip():
            bad.append(f"S11 {sid}: an invariant solution states in invariant_reason why 'best' cannot vary")
        elif kind == "eval" and r.get("invariant_reason", "").strip():
            bad.append(f"S11 {sid}: invariant_reason is set but metric_kind is eval")
    for r in ctx.components:
        for sid in ids(r["solutions"]):
            if sid not in sol_ids:
                bad.append(f"S11 {r['component_id']}: solution {sid!r} is not in solutions.csv")
    linked = {sid for r in ctx.components for sid in ids(r["solutions"])}
    for r in ctx.solutions:
        sid = r["solution_id"]
        if sid not in linked and not ctx.waived("S11", f"solution:{sid}"):
            bad.append(f"S11 {sid}: no component lists it in `solutions` (link it in components.csv or add a waiver)")

    if config.selection_table:
        port_rows = {r["solution_id"]: r for r in ctx.solutions if r.get("port", "").strip()}
        for sid in sorted(set(port_rows) - set(table)):
            bad.append(f"S14 {sid}: solutions.csv row has port {port_rows[sid]['port']} but no entry in "
                       f"{config.selection_table.partition(':')[0]} (add one so resolve({sid!r}) works)")
        for sid in sorted(set(table) - set(port_rows)):
            bad.append(f"S14 {sid}: selection table entry has no solutions.csv row with a port")
        for sid, entry in table.items():
            implementations = entry.get("implementations", {})
            has_default = bool(entry.get("default"))   # an entry without one takes the records' `selected`: nothing to compare
            if has_default and entry["default"] not in implementations:
                bad.append(f"S14 {sid}: default {entry.get('default')!r} is not among its implementations")
            if has_default and sid in port_rows and port_rows[sid]["selected"] != entry.get("default"):
                bad.append(f"S23 {sid}: selected {port_rows[sid]['selected']!r} differs from the selection table default "
                           f"{entry.get('default')!r}; the registry, the table and the live default must name one "
                           "implementation (change both together, or delete the table's `default` so the records' "
                           "`selected` is the only copy)")
            listed = listed_modules(ctx, sid, port_rows[sid]) if sid in port_rows else set()
            for name, ref in implementations.items():
                target = ref["target"] if isinstance(ref, dict) else ref
                module = target.partition(":")[0]
                mod_path = config.module_path(module)
                if not (config.root / mod_path).exists():
                    bad.append(f"S14 {sid}: implementation {name!r} points at {module}, which does not exist")
                elif sid in port_rows and mod_path not in listed:
                    bad.append(f"S14 {sid}: implementation {name!r} lives in {mod_path}, which neither the solution's "
                               "implementations cell nor the path of any of its implementations.csv records lists")

    for sid, n in Counter(s["solution_id"] for s in ctx.solutions).items():
        if n > 1:
            bad.append(f"S18 solutions.csv: solution id {sid} appears {n} times")
    for cid, n in Counter(c["component_id"] for c in ctx.components).items():
        if n > 1:
            bad.append(f"S18 components.csv: component id {cid} appears {n} times")
    for r in ctx.components:
        for col in ("solutions", "path"):
            for ident, n in Counter(ids(r[col])).items():
                if n > 1:
                    bad.append(f"S18 components.csv {r['component_id']}: `{col}` lists {ident} {n} times")
    for r in ctx.solutions:
        for col in ("port", "implementations"):
            for ident, n in Counter(ids(r[col])).items():
                if n > 1:
                    bad.append(f"S18 solutions.csv {r['solution_id']}: `{col}` lists {ident} {n} times")
    for r in ctx.components:
        if not ids(r["solutions"]):
            bad.append(f"S19 {r['component_id']}: serves no solution (name one in the `solutions` column, "
                       "or remove the code: nothing in this repo exists outside a solution)")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
