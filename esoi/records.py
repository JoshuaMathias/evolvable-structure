"""Check that the intent records specify every field of the ESOI template and link as the template says.

The template is the evolvable-structure skill's intent template (Problem, Solution, Implementation, Ideal,
Metric), parsed into ``esoi_template.csv`` by ``esoi template sync``; nothing here invents a field. Each entity
has one hand-edited CSV in the structure folder:

    problem         problems.csv         key problem_id         links: solution_ids, ideal_ids
    ideal           ideals.csv           key ideal_id           links: problem_ids
    solution        solutions.csv        key solution_id        links: problem_ids, ideal_ids, metric_ids, implementations
    implementation  implementations.csv  key implementation_id  links: solution_id
    metric          metrics.csv          key metric_id          links: solution_ids

Rules (one rule of a registry's own check, and ``esoi records`` for a repository that has no components):
R1 every file has records and the template's columns; R2 every ``required=yes`` template field (and a solution's
interface fields when ``interface_required``) is non-empty in each record; R3 links resolve and agree on both
sides and every problem has a solution and an ideal; R4 a problem is not phrased as the template says it is not
(a task or recommendation) and does not name its own solution; R5 parent links resolve.

Two levels. A repository writes its overall solution network once (problems, ideals, the overall solution, its
alternatives and top metrics: five CSVs in the folder named by ``overall`` in the configuration), and its
detailed records link up to it with optional columns on any record: ``parent_problem_ids``, ``parent_ideal_ids``,
``overall_solution_ids`` (the area of the overall solution a record belongs to) and ``parent_metric_ids``. R5
checks that each id names a record of the overall network. The overall network is itself checked with R1 to R4
(its solutions need no interface fields and its metrics no command).

Standard library only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from .tables import ids, read_csv

FILES = {"problem": ("problems.csv", "problem_id"), "ideal": ("ideals.csv", "ideal_id"),
         "solution": ("solutions.csv", "solution_id"), "implementation": ("implementations.csv", "implementation_id"),
         "metric": ("metrics.csv", "metric_id")}
TEMPLATE_DATA = Path(__file__).resolve().parent / "data" / "esoi_template.csv"
# The template says a problem is not a task or a recommendation: these openings read as one.
IMPERATIVE = {"add", "allow", "avoid", "build", "call", "change", "check", "choose", "create", "decide", "define",
              "deliver", "detect", "determine", "do", "ensure", "enable", "find", "fix", "give", "go", "hold", "implement",
              "improve", "keep", "let", "make", "measure", "move", "pick", "put", "reduce", "remove", "replace", "return",
              "run", "select", "send", "set", "settle", "show", "skip", "stop", "store", "switch", "take", "tell", "turn",
              "use", "verify", "write"}

Template = Dict[str, List[Dict[str, str]]]
# optional parent columns on any record, and the kind of overall-network record each one names
PARENT_COLUMNS = {"parent_problem_ids": "problem", "parent_ideal_ids": "ideal",
                  "overall_solution_ids": "solution", "parent_metric_ids": "metric"}
Overall = Dict[str, Set[str]]


def overall_ids(folder: Path) -> Overall:
    """The record ids of an overall network folder, by entity."""
    return {entity: {r.get(key, "") for r in read_csv(Path(folder) / name)} - {""}
            for entity, (name, key) in FILES.items()}


def load_template(path: Optional[Path] = None) -> Template:
    """The template rows by entity, in file order. Without a path, the copy shipped with the package."""
    out: Template = {}
    for row in read_csv(Path(path) if path else TEMPLATE_DATA):
        out.setdefault(row["entity"], []).append(row)
    return out


def fields(template: Template, entity: str, interface_required: bool) -> List[str]:
    """The field keys a record of ``entity`` must carry and fill."""
    groups = {"specify"} | ({"interface"} if interface_required else set())
    return [r["field_key"] for r in template.get(entity, []) if r["group"] in groups]


def implementation_id(solution_id: str, path: str) -> str:
    """The record id of an implementation named by a solution's ``implementations`` cell."""
    stem = path.rsplit("/", 1)[-1]
    return f"{solution_id}:{stem[:-3] if stem.endswith('.py') else stem}"


def check_records(struct: Path, template: Template, waived: Optional[Set[str]] = None,
                  interface_required: bool = True, related_problem_ids: Optional[Set[str]] = None,
                  overall: Optional[Overall] = None, require_command: bool = True,
                  require_parent: bool = False) -> List[str]:
    """Problems found in the intent records of ``struct``. ``waived`` holds solution ids whose records are still
    to be written (each is justified in the registry's waivers); their own template fields, links, implementations
    and metrics are not checked, and nothing else is relaxed. A problem may carry a ``related_problem_ids`` column
    naming problems of another registry it is the same difficulty as; when ``related_problem_ids`` (the other
    registry's ids) is given, each such id must be among them. ``overall`` holds the overall network's ids
    (``overall_ids``): every parent column must name one of them, and with ``require_parent`` every solution must
    name at least one. ``require_command`` is off for an overall network, whose metrics need no command."""
    waived = waived or set()
    bad: List[str] = []
    tables = {entity: read_csv(Path(struct) / name) for entity, (name, _) in FILES.items()}
    keys = {entity: key for entity, (_, key) in FILES.items()}
    index: Dict[str, Dict[str, Dict[str, str]]] = {}
    for entity, rows in tables.items():
        seen: Dict[str, Dict[str, str]] = {}
        for row in rows:
            rid = row.get(keys[entity], "")
            if rid in seen:
                bad.append(f"R1 {FILES[entity][0]} {rid}: id appears more than once")
            seen[rid] = row
        index[entity] = seen
        if not rows:
            bad.append(f"R1 {FILES[entity][0]}: no records")

    def skipped(entity: str, row: Dict[str, str]) -> bool:
        if entity == "solution":
            return row["solution_id"] in waived
        if entity == "implementation":
            return row.get("solution_id") in waived
        if entity == "metric":
            return bool(ids(row.get("solution_ids", ""))) and all(s in waived for s in ids(row["solution_ids"]))
        return False

    for entity, rows in tables.items():
        need = fields(template, entity, interface_required)
        if rows:
            missing = [k for k in need if k not in rows[0]]
            if missing:
                bad.append(f"R1 {FILES[entity][0]}: missing template column(s) {', '.join(missing)}"
                           " (run `esoi template sync`, then fill them)")
        for row in rows:
            if skipped(entity, row):
                continue
            empty = [k for k in need if k in row and not row[k].strip()]
            if empty:
                bad.append(f"R2 {row[keys[entity]]}: template field(s) not filled: {', '.join(empty)}")

    problems, ideals, solutions = index["problem"], index["ideal"], index["solution"]

    def unknown(owner: str, column: str, targets: Iterable[str], where: Dict[str, Dict[str, str]]) -> None:
        for target in targets:
            if target not in where:
                bad.append(f"R3 {owner}: {column} names {target!r}, which is not a record")

    for pid, row in problems.items():
        unknown(pid, "solution_ids", ids(row.get("solution_ids", "")), solutions)
        unknown(pid, "ideal_ids", ids(row.get("ideal_ids", "")), ideals)
        if not ids(row.get("solution_ids", "")):
            bad.append(f"R3 {pid}: no solution addresses this problem")
        if not ids(row.get("ideal_ids", "")):
            bad.append(f"R3 {pid}: no ideal opposes this problem")
        for sid in ids(row.get("solution_ids", "")):
            if sid in solutions and pid not in ids(solutions[sid].get("problem_ids", "")) and sid not in waived:
                bad.append(f"R3 {pid}: lists solution {sid} but {sid} does not list it in problem_ids")
        for iid in ids(row.get("ideal_ids", "")):
            if iid in ideals and pid not in ids(ideals[iid].get("problem_ids", "")):
                bad.append(f"R3 {pid}: lists ideal {iid} but {iid} does not list it in problem_ids")
    if related_problem_ids is not None:
        for pid, row in problems.items():
            for other in ids(row.get("related_problem_ids", "")):
                if other not in related_problem_ids:
                    bad.append(f"R3 {pid}: related_problem_ids names {other!r}, which is not a problem of the related registry")
    for iid, row in ideals.items():
        unknown(iid, "problem_ids", ids(row.get("problem_ids", "")), problems)
        if not ids(row.get("problem_ids", "")):
            bad.append(f"R3 {iid}: opposes no problem")
        for pid in ids(row.get("problem_ids", "")):
            if pid in problems and iid not in ids(problems[pid].get("ideal_ids", "")):
                bad.append(f"R3 {iid}: lists problem {pid} but {pid} does not list it in ideal_ids")
    for sid, row in solutions.items():
        if sid in waived:
            continue
        unknown(sid, "problem_ids", ids(row.get("problem_ids", "")), problems)
        unknown(sid, "ideal_ids", ids(row.get("ideal_ids", "")), ideals)
        unknown(sid, "metric_ids", ids(row.get("metric_ids", "")), index["metric"])
        if not ids(row.get("problem_ids", "")):
            bad.append(f"R3 {sid}: addresses no problem")
        if not ids(row.get("ideal_ids", "")):
            bad.append(f"R3 {sid}: has no ideal")
        if not ids(row.get("metric_ids", "")):
            bad.append(f"R3 {sid}: has no metric")
        for pid in ids(row.get("problem_ids", "")):
            if pid in problems and sid not in ids(problems[pid].get("solution_ids", "")):
                bad.append(f"R3 {sid}: lists problem {pid} but {pid} does not list it in solution_ids")
        for mid in ids(row.get("metric_ids", "")):
            if mid in index["metric"] and sid not in ids(index["metric"][mid].get("solution_ids", "")):
                bad.append(f"R3 {sid}: lists metric {mid} but {mid} does not list it in solution_ids")
        wanted = {implementation_id(sid, p) for p in ids(row.get("implementations", ""))}
        have = {i for i, r in index["implementation"].items() if r.get("solution_id") == sid}
        for iid in sorted(wanted - have):
            bad.append(f"R3 {sid}: implementation {iid} has no record in implementations.csv")
        for iid in sorted(have - wanted):
            bad.append(f"R3 {sid}: implementations.csv record {iid} is not in the solution's implementations cell")
    for iid, row in index["implementation"].items():
        if row.get("solution_id") not in solutions:
            bad.append(f"R3 {iid}: solution_id {row.get('solution_id')!r} is not a solution")
    for mid, row in index["metric"].items():
        unknown(mid, "solution_ids", ids(row.get("solution_ids", "")), solutions)
        if not ids(row.get("solution_ids", "")):
            bad.append(f"R3 {mid}: measures no solution")
        if require_command and not skipped("metric", row) and not row.get("command", "").strip():
            bad.append(f"R2 {mid}: command is empty")

    for entity, rows in tables.items():
        for row in rows:
            rid = row.get(keys[entity], "")
            named = False
            for column, kind in PARENT_COLUMNS.items():
                for target in ids(row.get(column, "")):
                    named = True
                    if overall is None:
                        bad.append(f"R5 {rid}: {column} names {target!r} but no overall network is configured")
                    elif target not in overall.get(kind, set()):
                        bad.append(f"R5 {rid}: {column} names {target!r}, which is not a {kind} of the overall network")
            if require_parent and entity == "solution" and not named and row.get(keys[entity]) not in waived:
                bad.append(f"R5 {rid}: names no parent problem, ideal, metric or area of the overall solution")

    solution_texts = {re.sub(r"\W+", " ", row.get(k, "").lower()).strip()
                      for row in solutions.values() for k in ("name", "scoped_purpose", "goals") if row.get(k)}
    for pid, row in problems.items():
        text = row.get("problem", "").strip()
        if not text:
            continue
        first = re.sub(r"[^a-z]", "", text.split()[0].lower()) if text.split() else ""
        if first in IMPERATIVE:
            bad.append(f"R4 {pid}: the problem reads as a task ({text.split()[0]!r} ...); the template says a problem "
                       "is a difficulty someone has, never a task or recommendation")
        if re.sub(r"\W+", " ", text.lower()).strip() in solution_texts:
            bad.append(f"R4 {pid}: the problem is identical to a solution's text")
        for sid in solutions:
            if sid in text:
                bad.append(f"R4 {pid}: the problem names its own solution {sid}")
    return bad
