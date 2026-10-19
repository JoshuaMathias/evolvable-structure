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

from . import config as config_module
from .config import Config
from .select import load_table
from .tables import read_csv

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
    if csv_path.exists():
        return {row["solution_id"] for row in read_csv(csv_path)}, True
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
        accepted = set(got.parameters)
        for pname, param in wanted.parameters.items():
            if pname in ("self", "cls") or param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
                continue
            if param.default is not inspect.Parameter.empty:
                continue
            if pname not in accepted:
                problems.append(f"{name} does not accept parameter {pname!r}")
    return problems


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
    port = row[f"{p}_port"].strip()
    if kind == "implementation":
        if not row["symbol"].strip():
            report.problems.append(f"C3 {rid}: an implementation row needs a symbol")
        else:
            try:
                cls = resolve_symbol(f"{row['module'].strip()}:{row['symbol'].strip()}")
            except Exception as exc:   # any import failure is the finding
                report.problems.append(f"C3 {rid}: {row['module']}:{row['symbol']} does not import ({type(exc).__name__}: {exc})")
                cls = None
            if cls is not None and port:
                try:
                    port_cls = resolve_port(port, options)
                except Exception:
                    report.problems.append(f"C3 {rid}: port {port!r} is not defined by the library")
                else:
                    for why in conformance_problems(cls, port_cls):
                        report.problems.append(f"C3 {rid}: {row['symbol']} does not satisfy {port}: {why}")
            elif cls is not None and not (row["gap"].strip() and row["action"].strip()):
                report.problems.append(f"C3 {rid}: an implementation row must name the port it claims, or state the gap "
                                       "(the library has no Protocol for it) and the action")
    elif kind in ("call", "config"):
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
    elif not row["action"].strip():
        report.problems.append(f"C5 {rid}: a duplicate row must state the action that removes it")
    status = row["status"].strip()
    if status not in STATUSES:
        report.problems.append(f"C6 {rid}: status {status!r} is not one of {', '.join(STATUSES)}")
    elif status != "done" and not (row["gap"].strip() and row["action"].strip()):
        report.problems.append(f"C6 {rid}: status {status} needs both a gap and an action")
    if not row["metric"].strip() and not (row["gap"].strip() and row["action"].strip()):
        report.problems.append(f"C6 {rid}: no metric, so the gap and the action must say what proof is missing")
    for test in [t.strip() for t in row["tests"].split(";") if t.strip()]:
        if not (root / test.split("::")[0]).exists():
            report.problems.append(f"C7 {rid}: test {test} does not exist under {root}")


def cases_hash(files: List[str], root: Path) -> str:
    """sha256 (first 12 hex) over the named files' bytes, in sorted order: the identity of a case set."""
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode())
        digest.update((Path(root) / name).read_bytes())
    return digest.hexdigest()[:12]


def check_solutions(report: ConsumerReport, rows: List[Dict[str, str]], solutions: Path, results: Path, root: Path) -> None:
    """C9 to C11: every integration point sits in a solution with a current recorded result."""
    sols = {r.get("solution_id", ""): r for r in read_csv(solutions)}
    result_rows = read_csv(results)
    latest: Dict[str, Dict[str, str]] = {}
    for r in result_rows:
        if r.get("kind", "offline") in ("live", "component"):
            continue   # live proofs and scored components are recorded beside the gating offline run
        latest[r.get("solution_id", "")] = r
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
    for sid in sorted(used):
        sol = sols[sid]
        if not sol.get("selected", "").strip():
            report.problems.append(f"C9 {sid}: no selected implementation")
        res = latest.get(sid)
        if res is None:
            report.problems.append(f"C10 {sid}: no recorded result")
            continue
        if not res.get("git_sha", "").strip() or not res.get("cases_sha", "").strip():
            report.problems.append(f"C10 {sid}: the latest result lacks a git sha or a cases hash")
        if res.get("passed", "") != res.get("cases", "x"):
            if sol.get("gap", "").strip():
                report.notes.append(f"{sid}: latest result {res.get('passed')}/{res.get('cases')}, the solution's gap names why")
            else:
                report.problems.append(f"C10 {sid}: latest result {res.get('passed')}/{res.get('cases')} is not all passing and the solution states no gap")
        files = [f for f in sol.get("metric_files", "").split(";") if f.strip()]
        if files and all((root / f).exists() for f in files) and cases_hash(files, root) != res.get("cases_sha", ""):
            report.problems.append(f"C10 {sid}: stale result, the metric files changed since it was recorded")
    for sid in sorted(used):
        sol = sols[sid]
        kind = sol.get("metric_kind", "").strip()
        if not kind:
            continue
        if kind == "invariant":
            if not sol.get("invariant_reason", "").strip():
                report.problems.append(f"C11 {sid}: an invariant solution states why best cannot vary (invariant_reason)")
        elif kind == "eval":
            comp, impl = sol.get("component", "").strip(), sol.get("component_impl", "").strip()
            row = next((r for r in reversed(result_rows) if r.get("kind") == "component"
                        and r.get("solution_id") == sid and r.get("component") == comp and r.get("impl") == impl), None)
            if not comp or not impl:
                report.problems.append(f"C11 {sid}: an eval solution names its component and component_impl")
            elif row is None:
                report.problems.append(f"C11 {sid}: no recorded component run for {comp}/{impl}")
            elif not row.get("git_sha", "").strip() or not row.get("cases_sha", "").strip():
                report.problems.append(f"C11 {sid}: the component run {comp}/{impl} lacks a git sha or a cases hash")
        else:
            report.problems.append(f"C11 {sid}: metric_kind {kind!r} is not eval or invariant")
    report.notes.append(f"{len(used)} solutions carry integration points; {len(sols) - len(used)} defined without one")


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
    with Path(registry).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in options.required_columns if c not in (reader.fieldnames or [])]
        if missing:
            report.problems.append(f"C1 {registry}: missing columns {', '.join(missing)}")
            return report
        rows = [{k: (v or "") for k, v in row.items() if k} for row in reader]
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
