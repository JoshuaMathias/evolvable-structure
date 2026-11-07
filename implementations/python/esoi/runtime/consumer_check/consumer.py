"""Check a consuming repository's integration registry against the library it builds on.

A consumer (a service that implements a library's ports, passes it configuration and calls it) lists each
integration point as one row of a CSV. ``esoi consumer check`` verifies the rows against the installed library
so drift fails a normal test run. Nothing here knows any particular library: the library's name, its port
modules and the column prefix come from the ``[consumer]`` table of the consumer's configuration:

    [consumer]
    library = "mylib"                       # the importable package the consumer builds on
    column_prefix = "lib"                   # columns lib_solution_id, lib_port, lib_symbol
    port_modules = ["mylib.core.ports"]     # where a bare port name is looked up
    pin_name = "mylib"                      # the name in a requirements pin: mylib @ git+https://...@<sha>
    selection = "mylib.core.selection:SELECTION"   # fallback source of solution ids (a wheel has no docs)

Registry columns (extra columns, such as ``tracking_*``, are ignored): ``integration_id``, ``module``,
``symbol`` (empty for a pure config row), ``<prefix>_solution_id``, ``<prefix>_port``, ``<prefix>_symbol`` (for
kind call or config: the library's ``dotted.module:Name`` the consumer uses), ``kind`` (implementation | config |
call | duplicate), ``selected_by``, ``metric``, ``tests`` (``;``-separated paths under the root), ``status``
(done | partial | gap), ``gap``, ``action``.

Checks: C1 columns, kinds and unique ids; C2 solution ids exist in the library; C3 an implementation imports
and has every public method of the port it claims, accepting the port's required parameter names; C4 a call
or config row's symbol resolves; C5 duplicate rows state an action; C6 status, gap and action; C7 tests exist;
C8 pin lag (reported, never a violation unless the caller asks).

With ``solutions`` and ``results`` CSVs the check also enforces that every integration point sits in a
solution (the optional registry column ``solution_id``) with a CURRENT recorded result: C9 the solution exists
and has a selected implementation; C10 it has a result with a git sha and a cases hash, every case passing (or
the solution's gap says why not), and the hash still matches the solution's ``metric_files``; C11 the
metric kind: ``invariant`` states its reason, ``eval`` names its component and has a recorded component run.
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import inspect
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from esoi.structure.intent_registry import config as config_module
from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.config import Config
from esoi.runtime.implementation_selection.select import load_table
from esoi.structure.intent_registry.tables import read_csv

KINDS = ("implementation", "config", "call", "duplicate")
STATUSES = ("done", "partial", "gap")
BASE_COLUMNS = ("integration_id", "module", "symbol", "kind", "selected_by", "metric", "tests", "status", "gap", "action")


@dataclass
class Options:
    """The library a consumer builds on, from the ``[consumer]`` table."""
    library: str
    column_prefix: str = "lib"
    port_modules: List[str] = field(default_factory=list)
    pin_name: str = ""
    selection: str = ""
    solutions_csv: str = ""

    @classmethod
    def from_config(cls, config: Config, library: Optional[str] = None) -> "Options":
        table = dict(config.consumer)
        if library:
            table["library"] = library
        if not table.get("library"):
            raise ValueError("no library named: set [consumer] library in the configuration or pass --library")
        return cls(**{k: v for k, v in table.items() if k in cls.__dataclass_fields__})

    @property
    def required_columns(self) -> Tuple[str, ...]:
        p = self.column_prefix
        return BASE_COLUMNS + (f"{p}_solution_id", f"{p}_port", f"{p}_symbol")

    @property
    def pin_regex(self) -> "re.Pattern[str]":
        name = "".join("[-_]" if c in "-_" else re.escape(c) for c in (self.pin_name or self.library))
        return re.compile(name + r"\s*@\s*git\+\S+?@([0-9a-fA-F]{7,40})")


@dataclass
class ConsumerReport:
    """What the check found: violations, informational notes, row counts by kind, and pin lag."""
    problems: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    pin_lag: bool = False


def library_dir(options: Options) -> Path:
    """The folder holding the installed library package."""
    return Path(importlib.import_module(options.library).__file__).resolve().parent


def library_solutions_csv(source_root: Path) -> Path:
    """The library's ``solutions.csv`` in a source checkout: the default folder, else a previous default."""
    for folder in (config_module.DEFAULT_STRUCTURE_DIR, *config_module.PREVIOUS_STRUCTURE_DIRS):
        if (source_root / folder / "solutions.csv").exists():
            return source_root / folder / "solutions.csv"
    return source_root / config_module.DEFAULT_STRUCTURE_DIR / "solutions.csv"


def known_solution_ids(options: Options) -> Tuple[set, bool]:
    """Solution ids the library defines, and whether the full ``solutions.csv`` was found. A source checkout has
    the registry; a wheel install does not, and then the ids come from the selection table."""
    csv_path = Path(options.solutions_csv) if options.solutions_csv else library_solutions_csv(library_dir(options).parent)
    rows = intents.read_tree(csv_path.parent, csv_path.name)   # the whole tree: records kept beside the code are read too
    if rows:
        return {row["solution_id"] for row in rows}, True
    if options.selection.endswith(".json"):
        return set(snapshot_ids(options)), False
    if options.selection:
        return set(load_table(options.selection)), False
    return set(), False


def snapshot_ids(options: Options) -> List[str]:
    """Solution ids in the library's ``esoi_selection.json`` snapshot (``esoi select --snapshot``): the path in
    ``selection`` is absolute, or relative to the folder holding the library package or to the package itself."""
    import json
    named = Path(options.selection)
    for candidate in (named, library_dir(options).parent / named, library_dir(options) / named.name):
        if candidate.is_file():
            return list(json.loads(candidate.read_text(encoding="utf-8")))
    raise FileNotFoundError(f"selection snapshot {options.selection} not found beside the library")


def resolve_symbol(dotted: str) -> Any:
    """Import ``package.module:Name`` (or ``package.module.Name``) and return the object."""
    if ":" in dotted:
        module_name, attr = dotted.split(":", 1)
    else:
        module_name, _, attr = dotted.rpartition(".")
    obj: Any = importlib.import_module(module_name)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return obj


def resolve_port(port: str, options: Options) -> Any:
    """A port by ``module:Name``, or by bare name searched in the library's port modules."""
    if ":" in port or "." in port:
        return resolve_symbol(port)
    for module_name in options.port_modules:
        try:
            found = getattr(importlib.import_module(module_name), port, None)
        except Exception:   # an optional dependency may be absent
            continue
        if found is not None:
            return found
    raise AttributeError(f"{port} is not defined in any of {', '.join(options.port_modules) or 'the configured port modules'}")


def port_methods(port: Any) -> Dict[str, inspect.Signature]:
    """The public callable members of a Protocol class, with signatures."""
    methods: Dict[str, inspect.Signature] = {}
    for name, member in vars(port).items():
        if name.startswith("_") or not callable(member):
            continue
        try:
            methods[name] = inspect.signature(member)
        except (TypeError, ValueError):
            continue
    return methods


def conformance_problems(cls: Any, port: Any) -> List[str]:
    """Why ``cls`` does not satisfy ``port``: a missing method, or a REQUIRED parameter name it cannot accept.

    A port parameter with a default is an optional capability the library passes only after inspecting the
    implementation's signature, so an implementation that lacks it is behind, not wrong."""
    problems: List[str] = []
    for name, wanted in port_methods(port).items():
        have = getattr(cls, name, None)
        if have is None or not callable(have):
            problems.append(f"missing method {name}")
            continue
        try:
            got = inspect.signature(have)
        except (TypeError, ValueError):
            continue
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in got.parameters.values()):
            continue
        problems.extend(f"{name} does not accept parameter {pname!r}" for pname in required_parameters(wanted) if pname not in got.parameters)
    return problems


def required_parameters(wanted: inspect.Signature) -> List[str]:
    """The names of the parameters a port method requires: not self or cls, not variadic, no default."""
    skipped = (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
    return [pname for pname, param in wanted.parameters.items()
            if pname not in ("self", "cls") and param.kind not in skipped and param.default is inspect.Parameter.empty]


def read_pin(requirements: Path, options: Options) -> Optional[str]:
    """The commit a requirements file pins the library to, or None."""
    if not requirements.exists():
        return None
    match = options.pin_regex.search(requirements.read_text(encoding="utf-8"))
    return match.group(1).lower() if match else None


def git_output(options: Options, *args: str) -> Optional[str]:
    try:
        out = subprocess.run(["git", "-C", str(library_dir(options)), *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def check_pin(report: ConsumerReport, requirements: Path, options: Options) -> None:
    """C8: compare the consumer's pinned library commit with the installed checkout."""
    pin = read_pin(requirements, options)
    if pin is None:
        report.notes.append(f"no {options.library} commit pin found in {requirements}")
        return
    head = (git_output(options, "rev-parse", "HEAD") or "").lower()
    if not head:
        report.notes.append(f"pinned {options.library} {pin[:10]}; installed library is not a git checkout, lag unknown")
        return
    if head.startswith(pin) or pin.startswith(head):
        report.notes.append(f"pinned {options.library} {pin[:10]} matches the installed checkout")
        return
    behind = git_output(options, "rev-list", "--count", f"{pin}..HEAD")
    report.pin_lag = True
    detail = f"{behind} commits behind" if behind and behind.isdigit() else "pin not found in the installed checkout"
    report.notes.append(f"pin lag: requirements pin {options.library} {pin[:10]}, installed checkout is {head[:10]} ({detail})")


def check_implementation_row(row: Dict[str, str], rid: str, port: str, options: Options, report: ConsumerReport) -> None:
    """C3: an implementation row names a symbol that imports and satisfies its port, or states the gap and the action."""
    if not row["symbol"].strip():
        report.problems.append(f"C3 {rid}: an implementation row needs a symbol")
        return
    try:
        cls = resolve_symbol(f"{row['module'].strip()}:{row['symbol'].strip()}")
    except Exception as exc:   # any import failure is the finding
        report.problems.append(f"C3 {rid}: {row['module']}:{row['symbol']} does not import ({type(exc).__name__}: {exc})")
        return
    if port:
        try:
            port_cls = resolve_port(port, options)
        except Exception:
            report.problems.append(f"C3 {rid}: port {port!r} is not defined by the library")
            return
        report.problems.extend(f"C3 {rid}: {row['symbol']} does not satisfy {port}: {why}" for why in conformance_problems(cls, port_cls))
    elif not (row["gap"].strip() and row["action"].strip()):
        report.problems.append(f"C3 {rid}: an implementation row must name the port it claims, or state the gap "
                               "(the library has no Protocol for it) and the action")


def check_call_row(row: Dict[str, str], rid: str, kind: str, p: str, report: ConsumerReport) -> None:
    """C4: a call or config row's symbol resolves and its module imports."""
    symbol = row[f"{p}_symbol"].strip()
    if not symbol:
        report.problems.append(f"C4 {rid}: a {kind} row needs a {p}_symbol")
    else:
        try:
            resolve_symbol(symbol)
        except Exception as exc:
            report.problems.append(f"C4 {rid}: {p}_symbol {symbol} does not resolve ({type(exc).__name__}: {exc})")
    if row["module"].strip():
        try:
            importlib.import_module(row["module"].strip())
        except Exception as exc:
            report.problems.append(f"C4 {rid}: module {row['module']} does not import ({type(exc).__name__}: {exc})")


def check_status_and_tests(row: Dict[str, str], rid: str, root: Path, report: ConsumerReport) -> None:
    """C6 and C7: the row's status, its gap and action, its metric, and the tests it names."""
    status = row["status"].strip()
    has_gap = bool(row["gap"].strip() and row["action"].strip())
    if status not in STATUSES:
        report.problems.append(f"C6 {rid}: status {status!r} is not one of {', '.join(STATUSES)}")
    elif status != "done" and not has_gap:
        report.problems.append(f"C6 {rid}: status {status} needs both a gap and an action")
    if not row["metric"].strip() and not has_gap:
        report.problems.append(f"C6 {rid}: no metric, so the gap and the action must say what proof is missing")
    for test in [t.strip() for t in row["tests"].split(";") if t.strip()]:
        if not (root / test.split("::")[0]).exists():
            report.problems.append(f"C7 {rid}: test {test} does not exist under {root}")


def check_row(row: Dict[str, str], root: Path, solutions: set, options: Options, report: ConsumerReport) -> None:
    """Run C2 to C7 on one registry row."""
    p = options.column_prefix
    rid = row.get("integration_id", "?")
    kind = row["kind"].strip()
    if kind not in KINDS:
        report.problems.append(f"C1 {rid}: kind {kind!r} is not one of {', '.join(KINDS)}")
        return
    report.counts[kind] = report.counts.get(kind, 0) + 1
    solution = row[f"{p}_solution_id"].strip()
    if solution and solutions and solution not in solutions:
        report.problems.append(f"C2 {rid}: solution id {solution!r} is not defined by the installed {options.library}")
    if kind == "implementation":
        check_implementation_row(row, rid, row[f"{p}_port"].strip(), options, report)
    elif kind in ("call", "config"):
        check_call_row(row, rid, kind, p, report)
    elif not row["action"].strip():
        report.problems.append(f"C5 {rid}: a duplicate row must state the action that removes it")
    check_status_and_tests(row, rid, root, report)


def cases_hash(files: List[str], root: Path) -> str:
    """sha256 (first 12 hex) over the named files' bytes, in sorted order: the identity of a case set."""
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode())
        digest.update((Path(root) / name).read_bytes())
    return digest.hexdigest()[:12]


def used_solutions(report: ConsumerReport, rows: List[Dict[str, str]], sols: dict, solutions: Path) -> set:
    """C9: the solutions the integration points sit in; a point in none, or in an unknown one, is a problem."""
    used = set()
    for row in rows:
        sid = row.get("solution_id", "").strip()
        rid = row["integration_id"]
        if not sid:
            report.problems.append(f"C9 {rid}: the integration point sits in no solution (solution_id is empty)")
        elif sid not in sols:
            report.problems.append(f"C9 {rid}: solution {sid!r} is not in {solutions.name}")
        else:
            used.add(sid)
    return used


def has_provenance(row: Dict[str, str]) -> bool:
    """Whether a recorded result names the git sha and the cases hash it was measured at."""
    return bool(row.get("git_sha", "").strip() and row.get("cases_sha", "").strip())


def check_recorded_result(report: ConsumerReport, sid: str, sol: Dict[str, str], res: Optional[Dict[str, str]], root: Path) -> None:
    """C9 and C10: a selected implementation, and a recorded result with provenance that still matches the metric files."""
    if not sol.get("selected", "").strip():
        report.problems.append(f"C9 {sid}: no selected implementation")
    if res is None:
        report.problems.append(f"C10 {sid}: no recorded result")
        return
    if not has_provenance(res):
        report.problems.append(f"C10 {sid}: the latest result lacks a git sha or a cases hash")
    if res.get("passed", "") != res.get("cases", "x"):
        report.notes.append(f"{sid}: latest result {res.get('passed')}/{res.get('cases')} is not all passing")
    files = [f for f in sol.get("metric_files", "").split(";") if f.strip()]
    if files and all((root / f).exists() for f in files) and cases_hash(files, root) != res.get("cases_sha", ""):
        report.notes.append(f"C10 {sid}: stale result, the metric files changed since it was recorded (advice: run the metric when "
                            f"what it teaches is worth its cost; a stale result informs and never blocks)")


def check_component_run(report: ConsumerReport, sid: str, sol: Dict[str, str], result_rows: List[Dict[str, str]]) -> None:
    """C11: a solution that names a component run has a recorded one with provenance."""
    comp, impl = sol.get("component", "").strip(), sol.get("component_impl", "").strip()
    if not comp and not impl:
        return   # no component run is declared for this solution
    row = next((r for r in reversed(result_rows) if (r.get("kind"), r.get("solution_id"), r.get("component"), r.get("impl")) == ("component", sid, comp, impl)), None)
    if not comp or not impl:
        report.problems.append(f"C11 {sid}: a solution that names a component run names both component and component_impl")
    elif row is None:
        report.problems.append(f"C11 {sid}: no recorded component run for {comp}/{impl}")
    elif not has_provenance(row):
        report.problems.append(f"C11 {sid}: the component run {comp}/{impl} lacks a git sha or a cases hash")


def check_solutions(report: ConsumerReport, rows: List[Dict[str, str]], solutions: Path, results: Path, root: Path) -> None:
    """C9 to C11: every integration point sits in a solution with a current recorded result."""
    sols = {r.get("solution_id", ""): r for r in intents.read_tree(Path(solutions).parent, Path(solutions).name)}
    result_rows = read_csv(results)
    latest: Dict[str, Dict[str, str]] = {}
    for r in result_rows:
        if r.get("kind", "offline") in ("live", "component"):
            continue   # live proofs and scored components are recorded beside the gating offline run
        latest[r.get("solution_id", "")] = r
    used = used_solutions(report, rows, sols, solutions)
    for sid in sorted(used):
        check_recorded_result(report, sid, sols[sid], latest.get(sid), root)
    for sid in sorted(used):
        check_component_run(report, sid, sols[sid], result_rows)
    report.notes.append(f"{len(used)} solutions carry integration points; {len(sols) - len(used)} defined without one")


def read_registry(registry: Path, options: Options, report: ConsumerReport) -> Optional[List[Dict[str, str]]]:
    """The registry's rows, or None (with the problem noted) when a required column is missing."""
    with registry.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in options.required_columns if c not in (reader.fieldnames or [])]
        if missing:
            report.problems.append(f"C1 {registry}: missing columns {', '.join(missing)}")
            return None
        return [{k: (v or "") for k, v in row.items() if k} for row in reader]


def check_consumer(registry: Path, root: Path, options: Options, requirements: Optional[Path] = None,
                   solutions: Optional[Path] = None, results: Optional[Path] = None) -> ConsumerReport:
    """Check every row of a consumer registry against the installed library; optionally report pin lag."""
    report = ConsumerReport()
    root = Path(root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if not Path(registry).is_file():
        report.problems.append(f"C1 {registry}: registry file not found")
        return report
    rows = read_registry(Path(registry), options, report)
    if rows is None:
        return report
    known, full = known_solution_ids(options)
    if not full:
        report.notes.append("the library's solutions.csv was not found next to it; solution ids checked against its selection table only")
    seen = set()
    for row in rows:
        rid = row["integration_id"].strip()
        if rid in seen:
            report.problems.append(f"C1 {rid}: duplicate integration_id")
        seen.add(rid)
        check_row(row, root, known, options, report)
    if solutions is not None and results is not None:
        check_solutions(report, rows, Path(solutions), Path(results), root)
    if requirements is not None:
        check_pin(report, Path(requirements), options)
    return report
