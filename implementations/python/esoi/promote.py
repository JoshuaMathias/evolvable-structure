"""Promote the implementation that the solution's own metric says is best.

``esoi select --promote`` reads the leaderboard's verdict for every evaluated solution. Where a rival clearly beats the
selected implementation (the same cases, the same sample, beyond the noise: ``leaderboard.challengers``), it either

* switches the solution's ``selected`` in the records to the winner, points the metric's command at it, and writes the
  evidence into ``selected_by`` where the project has that approved column, else prints it (the date of each results row,
  the commit, the cases hash, the pass counts), when the
  solution's ``promotion`` cell says ``automatic``; or
* prints the exact proposal (the same edits) for a person to apply, when the cell is empty or says anything else.

Humans need only review metrics: the proposal and the evidence are the metric's, not an implementation to read. It never
promotes on a row without a ``cases_sha``, on rows of different cases, on a result that is stale (uncommitted code, or
code that changed since the commit), on a selection table that still holds its own default (two copies would
disagree), or on a solution that is not an evaluated one.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import leaderboard
from .config import Config
from .declarations import intent_folder
from .harness import stale_reason
from .registry import Registry, first_arm
from .select import load_table
from .tables import ids, read_csv, read_header, write_csv

AUTOMATIC = "automatic"
Row = Dict[str, str]


@dataclass
class Proposal:
    """One solution's promotion: what would change, why, and whether it may be applied without a person."""
    solution_id: str
    status: str                      # promote | propose | blocked
    current: str = ""
    winner: str = ""
    reason: str = ""
    selected: str = ""               # the new `selected` cell
    selected_by: str = ""            # the evidence written beside it
    command: str = ""                # the metric command after the switch
    metric_id: str = ""
    edits: List[str] = field(default_factory=list)


def new_selected(config: Config, registry: Registry, solution: Row, component: str, current: str, winner: str) -> str:
    """The ``selected`` cell for the winner, in the style the old one is written in (a path, ``solution:name``, a name)."""
    old = (solution.get("selected") or "").strip()
    sid = solution["solution_id"]
    if "/" in old.split("::")[0]:
        record = next((r for r in registry.implementations if r.get("implementation_id") == f"{sid}:{winner}"), {})
        path = (record.get("filepath") or "").strip()
        guess = f"{config.evaluation_dir}/{component}/impls/{winner}.py"
        return path or (guess if (config.root / guess).is_file() else "")
    return f"{sid}:{winner}" if old.startswith(f"{sid}:") else winner


def evidence(own: Row, rival: Row, current: str, winner: str, today: str) -> str:
    sample = f", sample {rival['sample']}" if (rival.get("sample") or "").strip() else ""
    return (f"promoted {today} by esoi select --promote on the solution's own metric: {winner} beat {current} on the same cases "
            f"(cases_sha {rival.get('cases_sha', '')}{sample}); {winner} {rival.get('passed', '')}/{rival.get('cases', '')} "
            f"run {rival.get('date', '')} at {rival.get('git_sha', '')}; {current} {own.get('passed', '')}/{own.get('cases', '')} "
            f"run {own.get('date', '')} at {own.get('git_sha', '')}")


def switch_command(config: Config, command: str, current: str, winner: str) -> str:
    """``command`` with its first harness arm pointed at ``winner``."""
    match = next(iter(re.finditer(config.metric_command, command or "")), None)
    if match is None or match.group(2) != current:
        return ""
    return command[:match.start(2)] + winner + command[match.end(2):]


def propose(config: Config, registry: Registry, today: Optional[str] = None,
            stale: Callable = stale_reason) -> List[Proposal]:
    """A proposal for each evaluated solution a rival clearly beats, in record order."""
    today = today or datetime.date.today().isoformat()
    history = leaderboard.all_results(config.results_path)
    metrics = {m.get("metric_id", ""): m for m in registry.metrics}
    out: List[Proposal] = []
    try:
        table = load_table(config.selection_table, config.root) if config.selection_table else {}
    except Exception:
        table = {}
    for solution in registry.solutions:
        sid = solution["solution_id"]
        component, current = first_arm(config, solution.get("metric_command", ""))
        if not component:
            continue
        arms = history.get(component, {})
        rows = {impl: rs[-1] for impl, rs in arms.items()}
        beaten = leaderboard.challengers(rows, current, config.evaluation, arms)
        if not beaten:
            continue
        winner_row = leaderboard.rank({r["impl"]: r for r in beaten})[0]
        winner = winner_row["impl"]
        pair = next(((own, rival) for own, rival in leaderboard.rival_pairs(rows, current, config.evaluation, arms)[0]
                     if rival["impl"] == winner), None)
        proposal = Proposal(sid, "blocked", current, winner)
        out.append(proposal)
        if pair is None:
            proposal.reason = "no run of the two on the same cases and sample"
            continue
        own, rival = pair
        why = next((f"{name}: {text}" for name, row in ((current, own), (winner, rival))
                    if (text := "its row has no cases_sha" if leaderboard.unverified(row) else stale(config, component, row, True))),
                   "")
        if why:
            proposal.reason = f"a result does not count ({why}); re-run `esoi run --stale` on committed code"
            continue
        if (table.get(sid) or {}).get("default"):
            proposal.reason = ("its selection table entry holds its own default; delete that `default` so the records' "
                               "`selected` is the only copy, then promote")
            continue
        selected = new_selected(config, registry, solution, component, current, winner)
        if not selected:
            proposal.reason = f"no implementation record or impls file of {winner} to point `selected` at"
            continue
        linked = [metrics[m] for m in ids(solution.get("metric_ids", "")) if m in metrics]
        target = next((m for m in linked if switch_command(config, m.get("command", ""), current, winner)), None)
        proposal.selected, proposal.selected_by = selected, evidence(own, rival, current, winner, today)
        proposal.edits = [f"solutions.csv {sid}: selected {solution.get('selected', '')!r} -> {selected!r}",
                          f"evidence: {proposal.selected_by}"]
        if target is not None:
            proposal.metric_id = target["metric_id"]
            proposal.command = switch_command(config, target["command"], current, winner)
            proposal.edits.append(f"metrics.csv {target['metric_id']}: command {target['command']!r} -> {proposal.command!r}")
        proposal.status = "promote" if (solution.get("promotion") or "").strip().lower() == AUTOMATIC else "propose"
        proposal.reason = ("the solution's `promotion` is automatic" if proposal.status == "promote"
                           else "the solution's `promotion` is not automatic: a person applies this")
    return out


def edit_row(folder: Path, name: str, key: str, ident: str, changes: Dict[str, str]) -> None:
    path = folder / name
    header, rows = read_header(path), read_csv(path)
    columns = header + [c for c in changes if c not in header]
    for row in rows:
        if row.get(key) == ident:
            row.update(changes)
    write_csv(path, columns, rows)


def apply(config: Config, registry: Registry, proposal: Proposal) -> None:
    """Write a proposal's edits to the records of the intent folders that hold the rows."""
    solution = next(r for r in registry.solutions if r["solution_id"] == proposal.solution_id)
    folder = intent_folder(config, solution.get("intent_id") or None)
    changes = {"selected": proposal.selected}
    if "selected_by" in read_header(folder / "solutions.csv"):   # the evidence is stored only where the project approved that column
        changes["selected_by"] = proposal.selected_by
    edit_row(folder, "solutions.csv", "solution_id", proposal.solution_id, changes)
    if proposal.metric_id:
        metric = next(m for m in registry.metrics if m.get("metric_id") == proposal.metric_id)
        edit_row(intent_folder(config, metric.get("intent_id") or None), "metrics.csv", "metric_id", proposal.metric_id,
                 {"command": proposal.command})


def run_cli(config: Config, solution_id: str = "", dry_run: bool = False, say: Callable[[str], None] = print) -> int:
    """Print each proposal; apply those the policy allows. Exit 1 when a rival wins and nothing could be applied."""
    from . import registry as registry_module, tracker
    registry = registry_module.load(config)
    proposals = [p for p in propose(config, registry) if not solution_id or p.solution_id == solution_id]
    if not proposals:
        say("no rival clearly beats a selected implementation: nothing to promote")
        return 0
    applied = 0
    for p in proposals:
        say(f"{p.solution_id}: {p.winner} beats the selected {p.current}")
        if p.status == "blocked":
            say(f"  not promoted: {p.reason}")
            continue
        for edit in p.edits:
            say(f"  {edit}")
        if p.status == "promote" and not dry_run:
            apply(config, registry, p)
            applied += 1
            say(f"  promoted ({p.reason})")
        else:
            say(f"  proposal only ({'dry run' if dry_run and p.status == 'promote' else p.reason})")
    if applied:
        loaded = registry_module.load(config)
        tracker.write(config, loaded, say=lambda text: None)
        say("rebuilt the review tracker; commit the records, then `esoi run --stale` so the new selection has a current row")
    return 0 if applied == len(proposals) else 1
