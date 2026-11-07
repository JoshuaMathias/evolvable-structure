"""``esoi follow``: a child repository benefits when its parent's selections improve, and keeps its own metric as the check.

A child that builds on a parent (``[parent]`` in the configuration, or an Assembler with a parent) inherits the parent's selected
arm of every solution it does not decide itself, and overrides it where it differs (rule S35, ``overrides.csv``). Neither is
re-checked on its own: an override outlives its reason, and an inherited arm changes under the child unnoticed. ``follow`` compares,
per solution, the parent's CURRENT selected arm with the arm the child holds (its lock, or its own selected arm for an override) and
judges the parent's arm on the CHILD's own metric by the child's own selection rule (``leaderboard.decisions``):

* ``adopt``: the parent's arm holds (not worse than the child's arm): drop the override, or update the lock.
* ``keep``: the child's metric says the parent's arm loses: keep the override (or the lock), with the numbers.
* ``drop``: the parent's arm now beats the child's own arm: the override can be dropped.
* ``not-measured``: the child has no comparable row for the parent's arm: the report lists the exact command that records it and its
  cost class. Nothing is run unless ``--run-free`` is passed, and then only arms the harness declares offline (no model). A paid
  arm is never run here.

A recorded row whose measured code changed (the configured staleness rule, ``esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness``) is shown as stale with the command that
re-records it. The output is advice only (exit 0 whatever it finds); a malformed override is reported, not failed. No new field in the
records.
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from esoi.runtime.assemble_by_name.interface import OVERRIDES_FILE, UNCONFIRMED, check_reasons, package_assembler, parent_defaults
from esoi.optimization.measurement_harness import interface as harness
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reason
from esoi.optimization.when_metrics_are_run import interface as gating
from esoi.optimization.leaderboard import arm_selection, case_identity, ranking, results_log, rival_decisions, switching_policy
from esoi.optimization.leaderboard.interface import rival_pairs
from esoi.runtime.implementation_selection import variants
from esoi.runtime.implementation_selection.interface import lock as lock_module
from esoi.structure.intent_registry import registry as registry_module
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import read_rows
from esoi.runtime.implementation_selection.select import default_name, records_defaults, snapshot_defaults

SCHEMA = "esoi.follow/1"
VERDICTS = ("adopt", "keep", "drop", "not-measured")
HEADLINE = {"adopt": "ADOPT", "keep": "KEEP THE OVERRIDE", "drop": "OVERRIDE CAN BE DROPPED", "not-measured": "NOT MEASURED"}


@dataclass
class Step:
    """A command that records a row, with its cost class (``free``: offline, no model; ``paid``: may call a model)."""
    command: str
    cost: str
    free: bool
    component: str = ""
    impl: str = ""
    args: List[str] = field(default_factory=list)


@dataclass
class Finding:
    solution_id: str
    kind: str            # "override" (the child's own arm differs from the parent's) or "inherited" (the child follows the parent)
    parent_arm: str
    child_arm: str
    verdict: str
    advice: str
    numbers: str = ""
    stale: str = ""
    steps: List[Step] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"solution_id": self.solution_id, "kind": self.kind, "parent_arm": self.parent_arm, "child_arm": self.child_arm,
                "verdict": self.verdict, "advice": self.advice, "numbers": self.numbers, "stale": self.stale,
                "commands": [{"command": s.command, "cost": s.cost, "runs_with_run_free": s.free} for s in self.steps]}


@dataclass
class Report:
    parent: str
    findings: List[Finding] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    checked: int = 0

    @property
    def nothing_changed(self) -> bool:
        return not self.findings and not self.problems

    def as_dict(self) -> Dict[str, Any]:
        return {"schema": SCHEMA, "parent": self.parent, "checked": self.checked, "nothing_changed": self.nothing_changed,
                "solutions": [f.as_dict() for f in self.findings], "problems": self.problems, "skipped": self.skipped}


# the parent's current selections

def parent_selections(config: Config, parent: str = "") -> Tuple[Dict[str, str], str]:
    """``({solution_id: parent arm}, label)``. ``parent`` is a path to the parent's records folder (or its ``esoi.toml``) or
    snapshot (``esoi_selection.json``), else an importable package whose ``assembler()`` (or ``ASSEMBLER``) has a parent chain; with
    none given, the ``[parent]`` table of the configuration, else the parent chain of the configured package's assembler.
    Raises ``ValueError`` when the parent cannot be read."""
    from esoi.structure.intent_registry import config as config_module
    if parent:
        path = Path(parent).expanduser()
        path = path if path.is_absolute() else Path.cwd() / path
        if path.is_file() and path.suffix == ".json":
            return clean(snapshot_defaults(path)), str(parent)
        if path.exists():
            return clean(records_defaults(config_module.load(path))), str(parent)
        return from_package(parent, parent), parent
    if config.parent:
        return parent_defaults(config), "the [parent] table"
    if config.package:
        return from_package(config.package, config.package, own=True), f"the parent chain of {config.package}"
    raise ValueError("no parent: pass --parent PACKAGE_OR_PATH, or give the configuration a [parent] table")


def clean(found: Dict[str, str]) -> Dict[str, str]:
    return {sid: variants.base_of(name).lower() for sid, name in found.items() if name}


def from_package(name: str, label: str, own: bool = False) -> Dict[str, str]:
    """The selections of a package's Assembler: its own (``own`` False) or its parents' (``own`` True), nearest parent first."""
    try:
        assembler = package_assembler(name)
    except ImportError as error:
        raise ValueError(f"{label!r} is neither a path nor an importable package ({error})") from error
    chain = list(assembler.chain())
    out: Dict[str, str] = {}
    for one in (chain[1:] if own else chain[:1]):
        for sid, arm in one.packaged().defaults.items():
            out.setdefault(sid, variants.base_of(arm).lower())
    return out


# the child's own records

def lock_arms(lock_file: str) -> Tuple[Dict[str, str], str]:
    """``({solution_id: locked arm}, problem)`` from the child's lock file; ``{}`` when there is none."""
    if not lock_file or not Path(lock_file).is_file():
        return {}, ""
    try:
        found = lock_module.read(lock_file)
    except lock_module.LockError as error:
        return {}, f"the lock {lock_file} cannot be read: {error}"
    return {sid: variants.base_of(str(e["arm"])).lower() for sid, e in found["solutions"].items()}, ""


def override_reasons(sid: str, cell: str, own: set) -> Tuple[Tuple[str, ...], List[str]]:
    """``(reason ids, problems)`` of one override row's ``reason_ids`` cell."""
    given: Tuple[str, ...] = ()
    problems: List[str] = []
    parts = [p.strip() for p in cell.split(";") if p.strip()]
    for part in parts:
        try:
            given += check_reasons([part], f"overrides.csv {sid}")
        except ValueError as error:
            problems.append(str(error))
    if not given and not parts:
        problems.append(f"overrides.csv {sid}: no reason is recorded (cite a problem, ideal or metric id of this repository)")
    problems += [f"overrides.csv {sid}: {r} is no problem, ideal or metric of this repository"
                 for r in given if not r.startswith(UNCONFIRMED) and r not in own]
    return given, problems


def override_rows(config: Config, loaded: Any, parent: Dict[str, str]) -> Tuple[Dict[str, Tuple[str, ...]], List[str]]:
    """``({solution_id: reason ids}, problems)`` from ``overrides.csv``; a row that is malformed is a problem line, not an error."""
    own = {r.get(key, "") for rows, key in ((loaded.problems, "problem_id"), (loaded.ideals, "ideal_id"), (loaded.metrics, "metric_id")) for r in rows}
    reasons: Dict[str, Tuple[str, ...]] = {}
    problems: List[str] = []
    try:
        rows = read_rows(config, OVERRIDES_FILE)
    except Exception as error:   # noqa: BLE001, an unreadable file is advice
        return {}, [f"overrides.csv cannot be read ({type(error).__name__}: {error})"]
    for number, row in enumerate(rows, 1):
        sid, cell = (row.get("solution_id") or "").strip(), row.get("reason_ids", "")
        if not sid:
            problems.append(f"overrides.csv row {number}: no solution_id")
            continue
        if sid not in parent:
            problems.append(f"overrides.csv {sid}: the parent has no such solution, so there is nothing to override")
        given, found = override_reasons(sid, cell, own)
        problems += found
        reasons[sid] = reasons.get(sid, ()) + given
    return reasons, problems


# the child's own metric

def steps_for(config: Config, component: str, impl: str, row: Optional[Dict[str, str]], like: Optional[Dict[str, str]]) -> Step:
    """The command that records ``impl`` on the sample ``like`` was scored on, and whether it is free."""
    why = gating.paid_reason(config, component, impl, row)
    paid = bool(why) or gating.declared_live(config, component, impl, None)
    flags = harness.sample_args(config, component, like)
    if paid:
        command = " ".join(["esoi", "run", component, "--impl", impl, *flags, "--max-calls", "<budget>", "--record"])
        return Step(command, f"paid ({why or 'declared live'}): estimate the cost, stage the sample, set the call budget and get approval first; never run here",
                    False, component, impl, flags)
    command = " ".join(["esoi", "run", component, "--impl", impl, *flags, "--record"])
    return Step(command, "free (offline, no model)", True, component, impl, flags + ["--record"])


def runnable(config: Config, loaded: Any, row: Dict[str, str], component: str, impl: str) -> bool:
    """Whether the child can run ``impl`` on ``component``: a file in its impls folder, a listed arm or a recorded implementation."""
    sid = row.get("solution_id", "")
    listed = {arm for comp, arm in registry_module.harness_arms(config, row.get("metric_command", "")) if comp == component}
    recorded = {r.get("implementation_id", "").partition(":")[2].strip().lower() for r in loaded.implementations if r.get("solution_id") == sid}
    return gating.impl_path(config, component, impl).is_file() or impl in listed or impl in recorded


def judge(config: Config, loaded: Any, row: Optional[Dict[str, str]], sid: str, kind: str, parent_arm: str, child_arm: str) -> Finding:
    """The verdict for one solution on the child's own metric."""
    found = Finding(sid, kind, parent_arm, child_arm, "not-measured", "")
    if row is None or not (comp := arm_selection.selected_arm(config, row, "", loaded)[0]):
        found.advice = f"the child records no metric of its own for {sid}, so {parent_arm} cannot be checked here; add a metric that measures the solution (esoi new solution) or follow the parent without a check"
        return found
    history = results_log.all_results(config.results_path).get(comp, {})
    rows = {impl: seen[-1] for impl, seen in history.items() if seen}
    per_case = results_log.per_case_rows(config)
    if child_arm not in rows and (measured := arm_selection.selected_arm(config, row, comp, loaded)[1]) in rows:
        child_arm, found.child_arm = measured, measured   # the records name the arm by its file; the metric knows it by its arm name
    mine, theirs = rows.get(child_arm), rows.get(parent_arm)
    add_stale(config, comp, found, ((child_arm, mine), (parent_arm, theirs)), mine)
    pairs, unmatched = rival_pairs(rows, child_arm, config.evaluation, history) if mine is not None else ([], [])
    if mine is None or not any(b["impl"] == parent_arm for _, b in pairs):
        found.advice = describe_missing(config, loaded, row, comp, child_arm, parent_arm, mine, theirs, unmatched, found)
        return found
    found.numbers, found.verdict, found.advice = decide(config, found, comp, rows, history, per_case)
    return found


def decide(config: Config, found: Finding, comp: str, rows: Dict[str, Dict[str, str]], history: Dict[str, Any], per_case: Any) -> Tuple[str, str, str]:
    """``(numbers, verdict, advice)`` of the parent's arm against the child's, from the rival decision on the child's metric."""
    sid, kind, parent_arm, child_arm = found.solution_id, found.kind, found.parent_arm, found.child_arm
    policy = switching_policy.policy_for(config, sid, comp, per_case)
    decided = [d for d in rival_decisions.decisions(rows, child_arm, config.evaluation, history, per_case, policy) if d.rival == parent_arm]
    d = decided[0]
    numbers = f"{parent_arm} {ranking.pass_rate(d.other):.3g} against {child_arm} {ranking.pass_rate(d.own):.3g} on {case_identity.describe_cases(d.own)}; {d.text}"
    return (numbers, *verdict_advice(d.outcome, kind, sid, parent_arm, child_arm, numbers))


def add_stale(config: Config, comp: str, found: Finding, recorded: Tuple[Tuple[str, Optional[Dict[str, str]]], ...], mine: Optional[Dict[str, str]]) -> None:
    """Note on ``found`` which of the recorded rows are stale, with the step that re-records each."""
    for impl, rec in recorded:
        if rec is not None and (why := stale_reason(config, comp, rec, True)):
            found.stale += f"{impl}: {why}; "
            found.steps.append(steps_for(config, comp, impl, rec, mine))
    found.stale = found.stale.rstrip("; ")


def verdict_advice(outcome: str, kind: str, sid: str, parent_arm: str, child_arm: str, numbers: str) -> Tuple[str, str]:
    """``(verdict, advice)`` for the parent's arm against the child's, from the decision's outcome."""
    override = kind == "override"
    if outcome == "rival":
        return "drop", (f"override can be dropped: on your own metric {parent_arm} now beats {child_arm}; remove the override of {sid}"
                        if override else f"adopt {parent_arm}: it beats {child_arm} on your own metric; update the lock: esoi lock --update --solution {sid}")
    if outcome == "tie":
        return "adopt", (f"adopt {parent_arm}: it holds on your own metric (not worse than {child_arm}); drop the override of {sid}"
                         if override else f"adopt {parent_arm}: it holds on your own metric; update the lock: esoi lock --update --solution {sid}")
    held = "the override" if override else f"the lock ({child_arm})"
    return "keep", f"keep {held}: your own metric says the parent's {parent_arm} loses to {child_arm} ({numbers})"


def describe_missing(config: Config, loaded: Any, row: Dict[str, str], comp: str, child_arm: str, parent_arm: str,
                     mine: Optional[Dict[str, str]], theirs: Optional[Dict[str, str]], unmatched: List[Tuple[str, str]], found: Finding) -> str:
    """Why there is no verdict, and the exact command that records the missing row (the child's arm first when it has none)."""
    wants = []
    if not runnable(config, loaded, row, comp, parent_arm):
        return (f"the child's component {comp} cannot run {parent_arm}: no impls/{parent_arm}.py, no listed arm and no implementation record of that name; "
                f"add it (esoi admit {row.get('solution_id', '')} {parent_arm} --why TEXT) and record it")
    if mine is None:
        wants.append((child_arm, mine, None))
        why = f"{child_arm} (the child's arm) has no recorded row"
    else:
        why = (f"{parent_arm} has no row scored on the same cases and sample as {child_arm}" if theirs is not None
               else f"{parent_arm} has no recorded row")
        wants.append((parent_arm, theirs, mine))
    for impl, rec, like in wants:
        if not any(s.impl == impl and s.component == comp for s in found.steps):
            found.steps.append(steps_for(config, comp, impl, rec, like))
    note = next((f" ({reason})" for impl, reason in unmatched if impl == parent_arm), "")
    return f"not measured: {why}{note}; record it on the child's own metric"


# the report

def changed_arm(loaded: Any, row: Optional[Dict[str, str]], sid: str, parent_arm: str, locked: Dict[str, str]) -> Tuple[bool, bool, str]:
    """``(overridden, lock_moved, child_arm)``: how the child's arm for ``sid`` stands against the parent's."""
    own = variants.base_of(default_name(row, loaded.implementations)).lower() if row else ""
    overridden = bool(own) and own != parent_arm
    lock_moved = bool(locked.get(sid)) and locked[sid] != parent_arm and not overridden
    return overridden, lock_moved, own if overridden else locked.get(sid, "")


@dataclass(frozen=True)
class Child:
    """The child being followed: its records, its solution rows, the arms its lock holds, the reasons its overrides give and its metric ids."""
    config: Config
    loaded: Any
    rows: Dict[str, Dict[str, str]]
    locked: Dict[str, str]
    reasons: Dict[str, Any]
    metric_ids: Set[str]


def compare_one(child: Child, sid: str, parent_arm: str) -> Union[Finding, str, None]:
    """The finding for one solution, a skip note, or None when nothing can have changed under the child."""
    config, loaded, locked, reasons, metric_ids = child.config, child.loaded, child.locked, child.reasons, child.metric_ids
    row = child.rows.get(sid)
    overridden, lock_moved, child_arm = changed_arm(loaded, row, sid, parent_arm, locked)
    if not child_arm or not (overridden or lock_moved):
        return None   # inherited and not locked, or unchanged
    has_metric = any(r in metric_ids for r in reasons.get(sid, ()))
    found = judge(config, loaded, row, sid, "override" if overridden else "inherited", parent_arm, child_arm)
    if overridden and not has_metric and not lock_moved and found.verdict == "not-measured":
        return f"{sid}: override of {parent_arm} cites no metric and has no row to compare; not re-checked"
    return found


def follow(config: Config, parent: str = "", solutions: Tuple[str, ...] = (), lock_file: str = "esoi.lock.json") -> Report:
    """Compare the parent's current selections with the child's lock and overrides, and judge each change on the child's metric."""
    selections, label = parent_selections(config, parent)
    report = Report(label)
    loaded = registry_module.load(config)
    rows = {r.get("solution_id", ""): r for r in loaded.every_solution()}
    locked, problem = lock_arms(str((config.root / lock_file) if not Path(lock_file).is_absolute() else lock_file))
    if problem:
        report.problems.append(problem)
    reasons, bad = override_rows(config, loaded, selections)
    report.problems += bad
    metric_ids = {m.get("metric_id", "") for m in loaded.metrics}
    child = Child(config, loaded, rows, locked, reasons, metric_ids)
    for sid in sorted(selections):
        if solutions and sid not in solutions:
            continue
        report.checked += 1
        compared = compare_one(child, sid, selections[sid])
        if isinstance(compared, str):
            report.skipped.append(compared)
        elif compared is not None:
            report.findings.append(compared)
    return report


def render_finding(found: Finding, plan: bool, say: Callable[[str], None]) -> None:
    """The lines for one finding: headline, advice, numbers, stale rows and the steps."""
    headline = "KEEP THE LOCK" if found.verdict == "keep" and found.kind == "inherited" else HEADLINE[found.verdict]
    say(f"{found.solution_id}: {headline} ({found.kind}: parent {found.parent_arm}, here {found.child_arm})")
    say(f"  {found.advice}")
    if found.numbers and found.verdict != "keep":
        say(f"  numbers: {found.numbers}")
    if found.stale:
        say(f"  stale (measured code changed or the row is not current): {found.stale}")
    for step in found.steps:
        say(f"  {'would run' if plan and step.free else 'record'}: {step.command}   [{step.cost}]")


def render(report: Report, plan: bool, say: Callable[[str], None]) -> None:
    say(f"esoi follow: parent {report.parent}, {report.checked} solution(s) compared")
    if report.nothing_changed:
        say("nothing changed: the parent's selections match what this repository holds, and no override needs a second look")
    for found in report.findings:
        render_finding(found, plan, say)
    for line in report.problems:
        say(f"malformed override: {line}" if line.startswith("overrides.csv") else f"problem: {line}")
    for line in report.skipped:
        say(f"skipped: {line}")


def run_free(config: Config, report: Report, say: Callable[[str], None]) -> int:
    """Run the free steps (offline arms only), each once. Returns how many ran."""
    ran, seen = 0, set()
    for found in report.findings:
        for step in found.steps:
            key = (step.component, step.impl)
            if step.free and key not in seen:
                seen.add(key)
                say(f"running (free, offline): {step.command}")
                harness.prepare_path(config)
                harness.run_cli([step.component, "--impl", step.impl, *step.args], config, say)
                ran += 1
    return ran


def run_cli(config: Config, parent: str = "", solutions: Tuple[str, ...] = (), plan: bool = False, free: bool = False,
            as_json: bool = False, lock_file: str = "esoi.lock.json", say: Callable[[str], None] = print) -> int:
    """``esoi follow``. Advice only: exit 0 whatever is found; 2 only when the parent cannot be read."""
    try:
        report = follow(config, parent, solutions, lock_file)
        if free and not plan:
            if run_free(config, report, say if not as_json else (lambda text: None)):
                report = follow(config, parent, solutions, lock_file)
    except ValueError as error:
        say(f"esoi follow: {error}")
        return 2
    if as_json:
        say(json.dumps(report.as_dict(), indent=1))
    else:
        render(report, plan, say)
    return 0
