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
(a task or recommendation) and does not name its own solution; R5 parent links resolve; R3 also checks that a solution's ``governs_metric_ids`` and the metrics' ``run_policy_ids``
agree both ways (the solution that says when metrics are run, and the metrics it governs). A detailed solution may leave out its own problem and ideal when it names
parent ones in the overall network (``parent_problem_ids``, ``parent_ideal_ids``), and then ``problems.csv`` and
``ideals.csv`` of the detailed level may be empty.

Two levels. A repository writes its overall solution network once (problems, ideals, the overall solution, its
alternatives and top metrics: five CSVs in the folder named by ``overall`` in the configuration), and its
detailed records link up to it with optional columns on any record: ``parent_problem_ids``, ``parent_ideal_ids``,
``overall_solution_ids`` (the area of the overall solution a record belongs to) and ``parent_metric_ids``. R5
checks that each id names a record of the overall network. The overall network is itself checked with R1 to R4
(its solutions need no interface fields and its metrics no command).

Intent layout. When the structure folder holds an ``intent.csv`` it is the top intent and the records of every
intent folder below it are checked as one set (``tables`` of ``check_records``): ids are unique across the tree and
a link may name a record in any intent. ``overall_solution_ids`` belongs to the legacy layout only and is reported
there as retired. A solution none of whose metrics has a command that records a run is a specification (derived, never declared; see
``esoi.structure.intent_registry.registry``): it needs no interface fields and its metrics no command. The rules about the intents themselves are S28 and S29 (``esoi.structure.structure_check.rules.intents``).

Standard library only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from esoi.structure.intent_registry.fields import upgrade_rows
from esoi.structure.intent_registry.tables import DEFAULT_METRIC_COMMAND, ids, is_command, read_csv, read_header

FILES = {"problem": ("problems.csv", "problem_id"), "ideal": ("ideals.csv", "ideal_id"),
         "solution": ("solutions.csv", "solution_id"), "implementation": ("implementations.csv", "implementation_id"),
         "metric": ("metrics.csv", "metric_id")}
#: Template fields a record may leave empty even though the template requires them: an intent need not state
#: opportunities. (A solution states at least one milestone; a field the template marks "(optional)" is not checked.)
#: Every other template field of a record is required.
MAY_BE_EMPTY: Dict[str, Set[str]] = {"intent": {"opportunities"}}
#: Template fields that records carry in another column: an implementation's `dependencies` are its `uses_solution_ids`.
CARRIED_ELSEWHERE: Dict[str, Set[str]] = {"implementation": {"dependencies"}}
TEMPLATE_DATA = Path(__file__).resolve().parents[2] / "data" / "esoi_template.csv"
# The template says a problem is not a task or a recommendation: these openings read as one.
IMPERATIVE = {"add", "allow", "avoid", "build", "call", "change", "check", "choose", "create", "decide", "define",
              "deliver", "detect", "determine", "do", "ensure", "enable", "find", "fix", "give", "go", "hold", "implement",
              "improve", "keep", "let", "make", "measure", "move", "pick", "put", "reduce", "remove", "replace", "return",
              "run", "select", "send", "set", "settle", "show", "skip", "stop", "store", "switch", "take", "tell", "turn",
              "use", "verify", "write"}

Template = Dict[str, List[Dict[str, str]]]
# optional parent columns on any record, and the kind of overall-network record each one names
# Columns that were renamed: a file that still has the old header is reported by R1 with the new name, never a crash.
RENAMED_COLUMNS = {"solutions.csv": {"port": "interface_name"}, "implementations.csv": {"path": "filepath"}}


#: Columns that no longer exist, with where their content goes now.
REMOVED_COLUMNS = {
    "solutions.csv": {
        "metric_kind": "every metric outputs a number, so there is no kind; a solution with no recorded metric run is a "
                       "specification, derived from that",
        "invariant_reason": "put the reason in the metric's purpose",
        "gap": "put what a metric cannot see in the metric's disadvantages",
        "scoped_purpose": "split into description, purpose, approach and out_of_scope (run `esoi fields migrate`)",
        "risk_addressed": "each tag now carries its own risk_ids in the tags cell (run `esoi fields migrate`)",
        "action": "a next step is a milestone: a value of a metric, in `milestones`",
    },
    "metrics.csv": {
        "scoped_purpose": "renamed `purpose`, with what the metric cannot see in `disadvantages` (run `esoi fields migrate`)",
    },
}


def renamed_column_problems(name: str, header: Iterable[str], label: str) -> List[str]:
    """R1 lines for each old column name still in the header of record file ``name``, and each removed column."""
    out = [f"R1 {label}: has the old column `{old}`, renamed `{new}` (rename it in the header; the values stay)"
           for old, new in RENAMED_COLUMNS.get(name, {}).items() if old in header]
    out += [f"R1 {label}: has the removed column `{old}` ({advice}); delete the column"
            for old, advice in REMOVED_COLUMNS.get(name, {}).items() if old in header]
    return out


#: The one place that names the columns a records file may carry besides the template's fields. A human-readable
#: field is part of the specification only when its owner approved it, which means it is in the template (SKILL.md) or
#: in the project's own `[records] approved_fields`. Everything here is technical: an id, a link to a record, a file
#: path, a command a machine runs, or the name of the interface a solution defines. Any column ending `_id` or `_ids`
#: is a link or an id, and any starting `tracking_` is the review tracker's own; neither needs listing.
TECHNICAL_COLUMNS = {
    "solutions.csv": {"interface_name", "implementations", "selected",
                      "adopts", "specializes",   # @library/solution: the library solution this row adopts (a reference only) or specializes
                      "delegates_to", "change_driver"},   # the role statement: who owns what the solution is not responsible for; what kind of change moves its metric
    "implementations.csv": {"filepath", "sub_intent", "selected"},   # selected: the legacy overall network flags its chosen way
    "metrics.csv": {"command"},
    "intent.csv": {"implements"},
    "problems.csv": {"name"},   # the short human label every generated page leads with (the sentence is long); S46 informs when it is missing
}


def unapproved_column_problems(name: str, header: Iterable[str], template: Template, label: str,
                               approved: Optional[Dict[str, Set[str]]] = None) -> List[str]:
    """R7 lines for each column of record file ``name`` that is neither a field of the template, nor technical
    (``TECHNICAL_COLUMNS``, ``*_id``, ``*_ids``, ``tracking_*``), nor approved by the project's owner."""
    entity = next((e for e, (file_name, _) in FILES.items() if file_name == name), "intent" if name == "intent.csv" else "")
    if not entity:
        return []
    allowed = {r["field_key"] for r in template.get(entity, []) if r["group"] != "meta"}
    allowed |= TECHNICAL_COLUMNS.get(name, set()) | (approved or {}).get(name, set())
    removed = set(REMOVED_COLUMNS.get(name, {})) | set(RENAMED_COLUMNS.get(name, {})) | ({"opportunity"} if entity == "intent" else set())
    return [f"R7 {label}: column `{column}` is not in the template, is not a technical column (an id, a link, a file path "
            "or a command) and is not approved. Propose the field to the person who owns the specification; add it to "
            f"`approved_fields` under `[records]` in esoi.toml (`{name.removesuffix('.csv')} = [\"{column}\"]`), or to the "
            "template in SKILL.md, only once they approve."
            for column in header
            if column not in allowed and column not in removed and not column.endswith(("_id", "_ids"))
            and not column.startswith("tracking_")]


def solutions_with_a_command(metric_rows: Iterable[Dict[str, str]], pattern: str = DEFAULT_METRIC_COMMAND) -> Set[str]:
    """Ids of the solutions that have a metric with a command that records a run; every other solution is a
    specification."""
    return {sid for m in metric_rows if is_command(m.get("command", ""), pattern) for sid in ids(m.get("solution_ids", ""))}


PARENT_COLUMNS = {"parent_problem_ids": "problem", "parent_ideal_ids": "ideal",
                  "overall_solution_ids": "solution", "parent_metric_ids": "metric"}
# optional columns of an implementation in the intent layout: the sub-intent it is specified as, and the solutions
# (in any intent) it builds on through their interfaces
INTENT_LINK_COLUMNS = ["sub_intent", "uses_solution_ids"]
# optional columns that tie a metric to the solution that says when it is run (see docs/explanation/when-metrics-are-run.md)
POLICY_COLUMNS = ["governs_metric_ids", "run_policy_ids"]
Overall = Dict[str, Set[str]]


def tables_of(registry) -> Dict[str, List[Dict[str, str]]]:
    """The five record tables of a loaded registry (every intent's rows, specification solutions included), by entity."""
    return {"problem": registry.problems, "ideal": registry.ideals, "solution": registry.every_solution(),
            "implementation": registry.implementations, "metric": registry.metrics}


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
    return [r["field_key"] for r in template.get(entity, [])
            if r["group"] in groups and r["field_key"] not in CARRIED_ELSEWHERE.get(entity, ())]


def checked_fields(template: Template, entity: str, interface_required: bool) -> List[str]:
    """The fields a record must carry and fill: ``fields`` without the ones the template marks ``(optional)``
    (``required`` = ``no`` on a ``specify`` row). An interface field is checked only when ``interface_required``."""
    optional = {r["field_key"] for r in template.get(entity, []) if r["group"] == "specify" and r["required"] != "yes"}
    return [k for k in fields(template, entity, interface_required) if k not in optional]


def implementation_id(solution_id: str, path: str) -> str:
    """The record id of an implementation named by a solution's ``implementations`` cell."""
    stem = path.rsplit("/", 1)[-1]
    return f"{solution_id}:{stem[:-3] if stem.endswith('.py') else stem}"


def match_implementations(solution_id: str, entries: List[str], records: Dict[str, Dict[str, str]]
                          ) -> Tuple[Dict[str, str], List[str]]:
    """Pair each entry of a solution's ``implementations`` cell with its record in ``implementations.csv``.

    An entry is ``filepath`` or ``filepath::name`` (several implementations may live in one module). Its record is, in order,
    the one whose id is the default id (``solution:file-stem``), the one whose id is ``solution:name``, or the one
    whose ``filepath`` cell equals the entry, so record ids need not follow any pattern. Returns ``({entry: record id or
    ""}, record ids no entry claimed)``; ``records`` are the records of this solution, by id."""
    claimed: Dict[str, str] = {}
    for entry in entries:
        name = entry.partition("::")[2]
        wanted = [implementation_id(solution_id, entry)] + ([f"{solution_id}:{name}"] if name else [])
        hit = next((i for i in wanted if i in records), None) \
            or next((i for i, r in records.items() if r.get("filepath", "").strip() == entry), None)
        claimed[entry] = hit or ""
    return claimed, sorted(set(records) - set(claimed.values()))


def check_headers(folder: Path, template: Template, interface_required: bool = True, label: str = "",
                  approved: Optional[Dict[str, Set[str]]] = None, metric_command: str = DEFAULT_METRIC_COMMAND) -> List[str]:
    """R1 problems in the header of each record file of one intent folder: a missing key or template column. A file
    with no rows (or none at all) is not reported here; the tree as a whole must have records of each type."""
    bad: List[str] = []
    for entity, (name, key) in FILES.items():
        path = Path(folder) / name
        if not path.is_file():
            continue
        rows = read_csv(path)
        header = read_header(path)
        # a solution of kind specification needs no interface fields, and a header may omit them only for those
        need = [key, *checked_fields(template, entity, interface_required)]
        if entity == "solution" and rows:
            commanded = solutions_with_a_command(read_csv(Path(folder) / "metrics.csv"), metric_command)
            if not any(r.get(key, "") in commanded for r in rows):
                need = [key, *checked_fields(template, entity, False)]
        missing = [k for k in need if k not in header]
        if missing:
            bad.append(f"R1 {label or folder}/{name}: missing template column(s) {', '.join(missing)}"
                       " (run `esoi template sync`, then fill them)")
        bad += renamed_column_problems(name, header, f"{label or folder}/{name}")
        bad += unapproved_column_problems(name, header, template, f"{label or folder}/{name}", approved)
    intent_path = Path(folder) / "intent.csv"
    if intent_path.is_file():
        bad += unapproved_column_problems("intent.csv", read_header(intent_path), template, f"{label or folder}/intent.csv", approved)
    return bad


@dataclass
class RecordSet:
    """The records being checked, by entity and id, with the ids whose own checks are relaxed and the problems found so far."""
    tables: Dict[str, List[Dict[str, str]]]
    keys: Dict[str, str]
    waived: Set[str]
    adopted: Set[str]
    index: Dict[str, Dict[str, Dict[str, str]]] = field(default_factory=dict)
    specified: Set[str] = field(default_factory=set)
    bad: List[str] = field(default_factory=list)

    def skipped(self, entity: str, row: Dict[str, str]) -> bool:
        """True for a record whose solution is waived (its records are still to be written)."""
        if entity in ("solution", "implementation"):
            return row.get("solution_id") in self.waived
        if entity == "metric":
            owners = ids(row.get("solution_ids", ""))
            return bool(owners) and all(s in self.waived for s in owners)
        return False

    def specification_only(self, entity: str, row: Dict[str, str]) -> bool:
        """True for a solution that is a specification, and for a metric that measures only specifications."""
        if entity == "solution":
            return row.get("solution_id") in self.specified
        if entity == "metric":
            owners = ids(row.get("solution_ids", ""))
            return bool(owners) and all(s in self.specified for s in owners)
        return False

    def unknown(self, owner: str, column: str, targets: Iterable[str], where: Dict[str, Dict[str, str]]) -> None:
        """R3 for each target of a link column that is not a record of ``where``."""
        self.bad += [f"R3 {owner}: {column} names {target!r}, which is not a record" for target in targets if target not in where]


def read_tables(struct: Path, tables: Optional[Dict[str, List[Dict[str, str]]]]) -> Dict[str, List[Dict[str, str]]]:
    """The rows of every record file of ``struct`` (upgraded to the current columns), unless the caller already merged them."""
    if tables is not None:
        return tables
    return {entity: upgrade_rows(entity, read_csv(Path(struct) / name)) for entity, (name, _) in FILES.items()}


def index_tables(rs: RecordSet, overall: Optional[Overall]) -> None:
    """Index each table by id; R1 for an id that appears twice and for a table with no records (a problem or ideal table may be empty under an overall network)."""
    for entity, rows in rs.tables.items():
        seen: Dict[str, Dict[str, str]] = {}
        for row in rows:
            rid = row.get(rs.keys[entity], "")
            if rid in seen:
                rs.bad.append(f"R1 {FILES[entity][0]} {rid}: id appears more than once")
            seen[rid] = row
        rs.index[entity] = seen
        if not rows and not (overall is not None and entity in ("problem", "ideal")):
            rs.bad.append(f"R1 {FILES[entity][0]}: no records")


def check_template_fields(rs: RecordSet, template: Template, interface_required: bool, merged: bool,
                          approved: Optional[Dict[str, Set[str]]]) -> None:
    """R1 for missing columns (a merged tree has its headers checked by ``check_headers``) and R2 for each required field left empty."""
    for entity, rows in rs.tables.items():
        need = checked_fields(template, entity, interface_required)
        if rows and not merged:
            name = FILES[entity][0]
            missing = [k for k in [rs.keys[entity], *need] if k not in rows[0]]
            if missing:
                rs.bad.append(f"R1 {name}: missing template column(s) {', '.join(missing)} (run `esoi template sync`, then fill them)")
            rs.bad += renamed_column_problems(name, rows[0], name)
            rs.bad += unapproved_column_problems(name, rows[0], template, name, approved)
        for row in rows:
            if rs.skipped(entity, row) or (entity == "solution" and row.get("solution_id") in rs.adopted):
                continue
            wanted = checked_fields(template, entity, False) if rs.specification_only(entity, row) else need
            empty = [k for k in wanted if k in row and not row[k].strip() and k not in MAY_BE_EMPTY.get(entity, ())]
            if empty:
                rs.bad.append(f"R2 {row.get(rs.keys[entity], '')}: template field(s) not filled: {', '.join(empty)}")


def check_problem_links(rs: RecordSet, related_problem_ids: Optional[Set[str]]) -> None:
    """R3 for each problem: its solutions and ideals are records, there is at least one of each, and each lists the problem back."""
    problems, ideals, solutions = rs.index["problem"], rs.index["ideal"], rs.index["solution"]
    for pid, row in problems.items():
        rs.unknown(pid, "solution_ids", ids(row.get("solution_ids", "")), solutions)
        rs.unknown(pid, "ideal_ids", ids(row.get("ideal_ids", "")), ideals)
        if not ids(row.get("solution_ids", "")):
            rs.bad.append(f"R3 {pid}: no solution addresses this problem")
        if not ids(row.get("ideal_ids", "")):
            rs.bad.append(f"R3 {pid}: no ideal opposes this problem")
        for sid in ids(row.get("solution_ids", "")):
            if sid in solutions and pid not in ids(solutions[sid].get("problem_ids", "")) and sid not in rs.waived and sid not in rs.adopted:
                rs.bad.append(f"R3 {pid}: lists solution {sid} but {sid} does not list it in problem_ids")
        for iid in ids(row.get("ideal_ids", "")):
            if iid in ideals and pid not in ids(ideals[iid].get("problem_ids", "")):
                rs.bad.append(f"R3 {pid}: lists ideal {iid} but {iid} does not list it in problem_ids")
    if related_problem_ids is not None:
        for pid, row in problems.items():
            rs.bad += [f"R3 {pid}: related_problem_ids names {other!r}, which is not a problem of the related registry"
                       for other in ids(row.get("related_problem_ids", "")) if other not in related_problem_ids]


def check_ideal_links(rs: RecordSet) -> None:
    """R3 for each ideal: the problems it opposes are records, it opposes one, and each lists the ideal back."""
    problems = rs.index["problem"]
    for iid, row in rs.index["ideal"].items():
        rs.unknown(iid, "problem_ids", ids(row.get("problem_ids", "")), problems)
        if not ids(row.get("problem_ids", "")):
            rs.bad.append(f"R3 {iid}: opposes no problem")
        for pid in ids(row.get("problem_ids", "")):
            if pid in problems and iid not in ids(problems[pid].get("ideal_ids", "")):
                rs.bad.append(f"R3 {iid}: lists problem {pid} but {pid} does not list it in ideal_ids")


def check_solution_has(rs: RecordSet, sid: str, row: Dict[str, str]) -> None:
    """R3 for a solution that addresses no problem (or none of its own intent), has no ideal or no metric; an adopted solution inherits these."""
    inherits = sid in rs.adopted   # the library says what the solution is for
    problem_ids = ids(row.get("problem_ids", ""))
    has_problem = bool(problem_ids or ids(row.get("parent_problem_ids", "")))
    if not has_problem and not inherits:
        rs.bad.append(f"R3 {sid}: addresses no problem")
    own = row.get("intent_id", "")
    if own and not inherits and has_problem and not any(rs.index["problem"].get(pid, {}).get("intent_id", "") == own for pid in problem_ids):
        rs.bad.append(f"R3 {sid}: addresses no problem of its own intent {own} (it may also link problems of other intents, "
                      "but is motivated by at least one of its own)")
    if not ids(row.get("ideal_ids", "")) and not ids(row.get("parent_ideal_ids", "")) and not inherits:
        rs.bad.append(f"R3 {sid}: has no ideal")
    if not ids(row.get("metric_ids", "")) and not inherits:
        rs.bad.append(f"R3 {sid}: has no metric")


def check_solution_back_links(rs: RecordSet, sid: str, row: Dict[str, str]) -> None:
    """R3 for a problem or metric a solution lists that does not list the solution back."""
    problems, metrics = rs.index["problem"], rs.index["metric"]
    for pid in ids(row.get("problem_ids", "")):
        if pid in problems and sid not in ids(problems[pid].get("solution_ids", "")):
            rs.bad.append(f"R3 {sid}: lists problem {pid} but {pid} does not list it in solution_ids")
    for mid in ids(row.get("metric_ids", "")):
        if mid in metrics and sid not in ids(metrics[mid].get("solution_ids", "")):
            rs.bad.append(f"R3 {sid}: lists metric {mid} but {mid} does not list it in solution_ids")


def check_solution_implementations(rs: RecordSet, sid: str, row: Dict[str, str]) -> None:
    """R3 for an implementation the solution's cell names without a record, and a record its cell does not name."""
    mine = {i: r for i, r in rs.index["implementation"].items() if r.get("solution_id") == sid}
    claimed, unclaimed = match_implementations(sid, ids(row.get("implementations", "")), mine)
    rs.bad += [f"R3 {sid}: implementation {implementation_id(sid, entry)} has no record in implementations.csv"
               for entry, rid in claimed.items() if not rid]
    rs.bad += [f"R3 {sid}: implementations.csv record {iid} is not in the solution's implementations cell" for iid in unclaimed]


def check_solution_links(rs: RecordSet) -> None:
    """R3 for each solution that is not waived: its problems, ideals and metrics, the links back, and its implementations."""
    for sid, row in rs.index["solution"].items():
        if sid in rs.waived:
            continue
        rs.unknown(sid, "problem_ids", ids(row.get("problem_ids", "")), rs.index["problem"])
        rs.unknown(sid, "ideal_ids", ids(row.get("ideal_ids", "")), rs.index["ideal"])
        rs.unknown(sid, "metric_ids", ids(row.get("metric_ids", "")), rs.index["metric"])
        check_solution_has(rs, sid, row)
        check_solution_back_links(rs, sid, row)
        check_solution_implementations(rs, sid, row)


def check_authoritative_metric(rs: RecordSet) -> None:
    """R6 for an authoritative metric that is not one of the solution's, and for a solution with several metrics and no authoritative one."""
    for sid, row in rs.index["solution"].items():
        mine = [mid for mid, m in rs.index["metric"].items() if sid in ids(m.get("solution_ids", ""))]
        chosen = row.get("authoritative_metric_id", "").strip()
        if chosen and chosen not in mine:
            rs.bad.append(f"R6 {sid}: authoritative_metric_id {chosen!r} is not one of the solution's metrics")
        elif len(mine) > 1 and not chosen and sid not in rs.waived:
            rs.bad.append(f"R6 {sid}: has {len(mine)} metrics, so authoritative_metric_id names the one that decides "
                          "which implementation is best")


def check_run_policies(rs: RecordSet) -> None:
    """R3 for a solution's ``governs_metric_ids`` and the metrics' ``run_policy_ids``, which must agree both ways."""
    solutions, metrics = rs.index["solution"], rs.index["metric"]
    for sid, row in solutions.items():
        for mid in ids(row.get("governs_metric_ids", "")):
            if mid not in metrics:
                rs.bad.append(f"R3 {sid}: governs_metric_ids names {mid!r}, which is not a metric")
            elif sid not in ids(metrics[mid].get("run_policy_ids", "")):
                rs.bad.append(f"R3 {sid}: governs metric {mid} but {mid} does not list it in run_policy_ids")
    for mid, row in metrics.items():
        for sid in ids(row.get("run_policy_ids", "")):
            if sid not in solutions:
                rs.bad.append(f"R3 {mid}: run_policy_ids names {sid!r}, which is not a solution")
            elif mid not in ids(solutions[sid].get("governs_metric_ids", "")):
                rs.bad.append(f"R3 {mid}: lists run policy {sid} but {sid} does not list it in governs_metric_ids")


def check_implementations_and_metrics(rs: RecordSet, require_command: bool) -> None:
    """R3 for an implementation of no solution and a metric that measures none; R2 for a metric without a command where one is required."""
    solutions = rs.index["solution"]
    for iid, row in rs.index["implementation"].items():
        if row.get("solution_id") not in solutions:
            rs.bad.append(f"R3 {iid}: solution_id {row.get('solution_id')!r} is not a solution")
    for mid, row in rs.index["metric"].items():
        rs.unknown(mid, "solution_ids", ids(row.get("solution_ids", "")), solutions)
        if not ids(row.get("solution_ids", "")):
            rs.bad.append(f"R3 {mid}: measures no solution")
        if require_command and not rs.skipped("metric", row) and not rs.specification_only("metric", row) \
                and not row.get("command", "").strip():
            rs.bad.append(f"R2 {mid}: command is empty")


def parent_link_problems(rid: str, row: Dict[str, str], overall: Optional[Overall], retired: Set[str], scope: str) -> Tuple[bool, List[str]]:
    """Whether a record names any parent record, and R5 for each parent id that is retired, unconfigured or not in the overall network."""
    named = False
    bad: List[str] = []
    for column, kind in PARENT_COLUMNS.items():
        for target in ids(row.get(column, "")):
            named = True
            if column in retired:
                bad.append(f"R5 {rid}: {column} is retired in the intent layout; a solution is recorded in the intent "
                           "it serves, and an implementation lists the solutions it builds on in uses_solution_ids")
            elif overall is None:
                bad.append(f"R5 {rid}: {column} names {target!r} but no overall network is configured")
            elif target not in overall.get(kind, set()):
                bad.append(f"R5 {rid}: {column} names {target!r}, which is not a {kind} of {scope}")
    return named, bad


def check_parent_links(rs: RecordSet, overall: Optional[Overall], retired: Set[str], scope: str, require_parent: bool) -> None:
    """R5 for each parent link that does not resolve, and with ``require_parent`` for a solution that names none."""
    for entity, rows in rs.tables.items():
        for row in rows:
            rid = row.get(rs.keys[entity], "")
            named, found = parent_link_problems(rid, row, overall, retired, scope)
            rs.bad += found
            if require_parent and entity == "solution" and not named and row.get(rs.keys[entity]) not in rs.waived:
                rs.bad.append(f"R5 {rid}: names no parent problem, ideal, metric or area of the overall solution")


def check_problem_phrasing(rs: RecordSet) -> None:
    """R4 for a problem phrased as a task, identical to a solution's text, or naming its own solution."""
    solutions = rs.index["solution"]
    solution_texts = {re.sub(r"\W+", " ", row.get(k, "").lower()).strip()
                      for row in solutions.values() for k in ("name", "purpose", "approach", "milestones") if row.get(k)}
    for pid, row in rs.index["problem"].items():
        text = row.get("problem", "").strip()
        if not text:
            continue
        first = re.sub(r"[^a-z]", "", text.split()[0].lower())
        if first in IMPERATIVE:
            rs.bad.append(f"R4 {pid}: the problem reads as a task ({text.split()[0]!r} ...); the template says a problem "
                          "is a difficulty someone has, never a task or recommendation")
        if re.sub(r"\W+", " ", text.lower()).strip() in solution_texts:
            rs.bad.append(f"R4 {pid}: the problem is identical to a solution's text")
        rs.bad += [f"R4 {pid}: the problem names its own solution {sid}" for sid in solutions if sid in text]


def check_records(struct: Path, template: Template, waived: Optional[Set[str]] = None,
                  interface_required: bool = True, related_problem_ids: Optional[Set[str]] = None,
                  overall: Optional[Overall] = None, require_command: bool = True,
                  require_parent: bool = False, tables: Optional[Dict[str, List[Dict[str, str]]]] = None,
                  retired: Optional[Set[str]] = None, scope: str = "the overall network",
                  approved: Optional[Dict[str, Set[str]]] = None, metric_command: str = DEFAULT_METRIC_COMMAND,
                  adopted: Optional[Set[str]] = None) -> List[str]:
    """Problems found in the intent records of ``struct``. ``waived`` holds solution ids whose records are still
    to be written (each is justified in the registry's waivers); their own template fields, links, implementations
    and metrics are not checked, and nothing else is relaxed. A problem may carry a ``related_problem_ids`` column
    naming problems of another registry it is the same difficulty as; when ``related_problem_ids`` (the other
    registry's ids) is given, each such id must be among them. ``overall`` holds the overall network's ids
    (``overall_ids``): every parent column must name one of them, and with ``require_parent`` every solution must
    name at least one. ``require_command`` is off for an overall network, whose metrics need no command. ``tables``
    holds the rows of every record file already read (the intent layout merges the intents' files, and then the
    header of each file is checked by ``check_headers`` instead); ``retired`` names parent columns that are reported
    wherever they appear (``overall_solution_ids`` in the intent layout); ``scope`` names, in a parent-link message, where
    the link should have resolved. ``adopted`` holds the ids of solutions adopted from a library: the library says what they are
    for, so their template fields, problems, ideals and metric are not required here, while their metrics, implementations
    and every id that points at them are checked like any solution's."""
    rs = RecordSet(read_tables(struct, tables), {entity: key for entity, (_, key) in FILES.items()}, waived or set(), adopted or set())
    index_tables(rs, overall)
    commanded = solutions_with_a_command(rs.index["metric"].values(), metric_command)
    rs.specified = {rid for rid in rs.index["solution"] if rid not in commanded}
    check_template_fields(rs, template, interface_required, tables is not None, approved)
    check_problem_links(rs, related_problem_ids)
    check_ideal_links(rs)
    check_solution_links(rs)
    check_authoritative_metric(rs)
    check_run_policies(rs)
    check_implementations_and_metrics(rs, require_command)
    check_parent_links(rs, overall, retired or set(), scope, require_parent)
    check_problem_phrasing(rs)
    return rs.bad
