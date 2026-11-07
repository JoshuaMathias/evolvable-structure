"""Promote the implementation that the solution's own metric says is best.

``esoi select --promote`` reads the leaderboard's verdict for every evaluated solution. Where a rival clearly beats the
selected implementation (the same cases, the same sample, by the rule of ``leaderboard.decisions``: a significant one-sided paired
test where per-case rows exist for both arms, else a best guess where the solution allows it), it either

* switches the solution's ``selected`` in the records to the winner (the metric's command lists the arms to measure and is never
  rewritten: the choice lives in ``selected``), and writes the
  evidence into ``selected_by`` where the project has that approved column, else prints it (the date of each results row,
  the commit, the cases hash, the pass counts), when the
  solution's ``promotion`` cell says ``automatic``; or
* (a solution with no `selected` yet gets its first choice the same way: the arm with the highest result on the latest stage
  that has one, or a blocked proposal naming the arms when the best are tied)
* prints the exact proposal (the same edits) for a person to apply, when the cell is empty or says anything else.

Humans need only review metrics: the proposal and the evidence are the metric's, not an implementation to read. It never
promotes on a row without a ``cases_sha``, on rows of different cases, on a result that is stale (uncommitted code, or
code that changed since the commit), on a selection table that still holds its own default (two copies would
disagree), or on a solution that is not an evaluated one.
"""
from __future__ import annotations

import datetime
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from esoi.optimization.leaderboard import arm_selection, case_identity, ranking, results_log, rival_decisions, switching_policy, cascade_stages
from esoi.optimization.leaderboard.interface import held_out_parts, rival_pairing, stage_standings
from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.specify_from_code.declarations import intent_folder
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reason
from esoi.structure.intent_registry.registry import Registry
from esoi.runtime.implementation_selection.select import load_table
from esoi.structure.intent_registry.tables import ids, read_csv, read_header, write_csv

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
    edits: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Subject:
    """The solution being promoted and everything its proposal reads: records, the component's arms and rows, the incumbent."""
    config: Config
    registry: Registry
    solution: Row
    component: str
    current: str
    arms: Dict[str, List[Row]]
    per_case: Dict
    stale: Callable
    today: str
    table: Dict

    def stale_reason(self, row: Row) -> str:
        """Why a result row does not count (uncommitted or changed code), else ``""``."""
        return self.stale(self.config, self.component, row, True)


def new_selected(subject: Subject, winner: str) -> str:
    """The ``selected`` cell for the winner, in the style the old one is written in (a path, ``solution:name``, a name)."""
    config, registry, component = subject.config, subject.registry, subject.component
    old = (subject.solution.get("selected") or "").strip()
    sid = subject.solution["solution_id"]
    if "/" in old.split("::")[0]:
        record = next((r for r in registry.implementations if r.get("implementation_id") == f"{sid}:{winner}"), {})
        path = (record.get("filepath") or "").strip()
        guess = f"{config.evaluation_dir}/{component}/impls/{winner}.py"
        return path or (guess if (config.root / guess).is_file() else "")
    return f"{sid}:{winner}" if old.startswith(f"{sid}:") else winner


def evidence(own: Row, rival: Row, current: str, winner: str, today: str, why: str = "") -> str:
    sample = f", sample {rival['sample']}" if (rival.get("sample") or "").strip() else ""
    return (f"promoted {today} by esoi select --promote on the solution's own metric: {winner} beat {current} on the same cases "
            f"(cases_sha {rival.get('cases_sha', '')}{sample}); {winner} {rival.get('passed', '')}/{rival.get('cases', '')} "
            f"run {rival.get('date', '')} at {rival.get('git_sha', '')}; {current} {own.get('passed', '')}/{own.get('cases', '')} "
            f"run {own.get('date', '')} at {own.get('git_sha', '')}" + (f"; rule: {why}" if why else ""))


def cascade_evidence(own: Row, rival: Row, current: str, winner: str, today: str, why: str = "") -> str:
    return (f"promoted {today} by esoi select --promote on the solution's metric cascade: {winner} is chosen over {current} by the "
            f"latest stage run; at their latest shared stage (cases_sha {rival.get('cases_sha', '')}) {winner} "
            f"{rival.get('passed', '')}/{rival.get('cases', '')} run {rival.get('date', '')} at {rival.get('git_sha', '')}; "
            f"{current} {own.get('passed', '')}/{own.get('cases', '')} run {own.get('date', '')} at {own.get('git_sha', '')}" + (f"; rule: {why}" if why else ""))


def solution_stages(config: Config, registry: Registry, solution: Row) -> List[cascade_stages.Stage]:
    """The cascade stages of the first of the solution's metrics that has a readable cascade, else none."""
    by_id = {m.get("metric_id", ""): m for m in registry.metrics}
    for metric_id in ids(solution.get("metric_ids", "")):
        found, errors = cascade_stages.load_stages(config, by_id.get(metric_id, {}))
        if found and not errors:
            return found
    return []


def latest_rows(subject: Subject, stages: List[cascade_stages.Stage]):
    """``(rows per arm at the latest counting stage, that stage or None, why there are none)``."""
    config, arms = subject.config, subject.arms
    if not stages:
        rows = {impl: rs[-1] for impl, rs in arms.items() if rs and not subject.stale_reason(rs[-1])}
        return rows, None, ("" if rows else "no counting result yet (run `esoi run` on committed code)")
    standing = stage_standings.standings(stages, arms, None, subject.stale_reason, config.evaluation)
    counting = {impl: st for impl, st in standing.items() if st.rows}
    if not counting:
        return {}, None, "no stage has a counting result yet (run `esoi run` on committed code, or `esoi run --stale`)"
    latest = max(st.reached for st in counting.values())
    return {impl: st.rows[latest] for impl, st in counting.items() if latest in st.rows}, stages[latest], ""


def first_choice(subject: Subject) -> Proposal:
    """The proposal for a solution whose ``selected`` is empty: the arm with the highest result on the latest cascade stage
    that has a counting result, when it is the only such arm or no other arm there is within the noise of it. Equal results are a
    tie, which the metric cannot break: the proposal is blocked and names the arms, so a person (or the project's tie rule)
    decides. The winning arm must also meet the gate of the stage it was chosen at."""
    config = subject.config
    proposal = Proposal(subject.solution["solution_id"], "blocked", "", "")
    rows, stage, none_reason = latest_rows(subject, solution_stages(config, subject.registry, subject.solution))
    if none_reason:
        proposal.reason = none_reason
        return proposal
    winner_name, why_guess = rival_decisions.best_guess(rows, config.evaluation)
    reference = max(rows.values(), key=lambda r: (int(float(r.get("cases") or 0)), r.get("date") or "", r["impl"]))
    ranked = ranking.rank({impl: r for impl, r in rows.items() if case_identity.comparable(r, reference)})
    where = stage.name if stage else "the results log"
    if winner_name is None:   # exactly equal estimates, or nothing to choose from: the metric cannot break it
        proposal.reason = (f"a tie at {where}: " + ", ".join(f"{r['impl']} {r.get('passed', '')}/{r.get('cases', '')}" for r in ranked)
                           + "; the metric cannot break it (best guess on the point estimate), so no arm is selected")
        return proposal
    leader = rows[winner_name]
    if stage is not None and not stage_standings.gate_met(stage, leader, None, config.evaluation)[0]:
        proposal.reason = f"{leader['impl']} leads at {where} but does not meet that stage's gate"
        return proposal
    return first_selection(subject, proposal, leader, ranked, where)


def first_selection(subject: Subject, proposal: Proposal, leader: Row, ranked: List[Row], where: str) -> Proposal:
    """Fill the proposal of a first selection: the winner, its evidence, the edits and whether a person must apply them."""
    solution, today = subject.solution, subject.today
    sid = solution["solution_id"]
    proposal.winner, proposal.status = leader["impl"], "propose"
    proposal.selected = new_selected(subject, proposal.winner)
    others = ", ".join(f"{r['impl']} {r.get('passed', '')}/{r.get('cases', '')}" for r in ranked[1:]) or "no other arm has a result"
    proposal.selected_by = (f"selected {today} by esoi select --promote as a best guess (no incumbent to test against) on the solution's metric: {proposal.winner} "
                            f"{leader.get('passed', '')}/{leader.get('cases', '')} at {where} (cases_sha {leader.get('cases_sha', '')}, "
                            f"run {leader.get('date', '')} at {leader.get('git_sha', '')}); {others}")
    proposal.edits = [f"solutions.csv {sid}: selected '' -> {proposal.selected!r}", f"evidence: {proposal.selected_by}"]
    automatic = (solution.get("promotion") or "").strip().lower() == AUTOMATIC
    proposal.reason = ("the solution's `promotion` is automatic" if automatic
                       else "the solution's `promotion` is not automatic: a person applies this (esoi select --promote --apply)")
    if automatic:
        proposal.status = "promote"
    return proposal


def stage_missing(subject: Subject, winner: str, need: str, origin: str) -> str:
    """Why a switch to ``winner`` waits for the cascade stage ``need`` that the project or solution requires, or ``""`` when the
    winner has a counting result at that stage or a later one."""
    found = solution_stages(subject.config, subject.registry, subject.solution)
    if not found:
        return f"the {origin} requires stage {need}, but the solution's metric has no cascading conditionals"
    names = [st.name for st in found]
    if need not in names:
        return f"the {origin} requires stage {need}, which the metric's cascading conditionals do not list"
    standing = stage_standings.standings(found, subject.arms, None, subject.stale_reason, subject.config.evaluation)
    if winner in standing and any(i >= names.index(need) for i in standing[winner].rows):
        return ""
    return f"the {origin} requires a result at stage {need} before switching, and {winner} has none yet; run it there"


@dataclass
class Choice:
    """A rival the metric picked over the selected implementation: the pair of rows to compare and how it was picked."""
    winner: str
    pair: Optional[tuple]
    via_cascade: bool
    claim_policy: switching_policy.Policy
    fraction: float


def pick_rows(arms: Dict[str, List[Row]], per_case: Dict, fraction: float) -> Dict[str, List[Row]]:
    """The arms' rows on the selection part (the held-out share kept out), only the arms that have any."""
    if not fraction:
        return {impl: rs for impl, rs in arms.items() if rs}
    parts = {impl: [part for r in rs if (part := held_out_parts.part_row(per_case, r, fraction, False)) is not None] for impl, rs in arms.items()}
    return {impl: rs for impl, rs in parts.items() if rs}


def cascade_choice(subject: Subject, via: tuple, pick_policy: switching_policy.Policy,
                   claim_policy: switching_policy.Policy) -> Optional[Choice]:
    """The cascade's leader as a choice, when switching to it takes a shown (or allowed guessed) gain."""
    winner, pair = via
    if winner is None:
        return None
    if pair is not None:   # a cascade names the leader at its latest stage; switching still takes a shown (or allowed guessed) gain
        current = subject.current
        shown = rival_decisions.decisions({current: pair[0], winner: pair[1]}, current, subject.config.evaluation, None, subject.per_case, pick_policy)
        if not any(d.outcome == "rival" and d.switch for d in shown):
            return None
    return Choice(winner, pair, True, claim_policy, claim_policy.holdout)


def pick_winner(subject: Subject, claim_policy: switching_policy.Policy) -> Optional[Choice]:
    """The rival that clearly beats ``current`` (by the cascade's latest stage, else the paired decision), or None."""
    config, current, per_case = subject.config, subject.current, subject.per_case
    fraction = claim_policy.holdout
    pick_policy = dataclasses.replace(claim_policy, holdout=0.0)   # the leader is chosen on the selection part; claims use the held-out part
    pick_arms = pick_rows(subject.arms, per_case, fraction)
    if current not in pick_arms:
        return None
    rows = {impl: rs[-1] for impl, rs in pick_arms.items()}
    via = stage_standings.solution_choice(config, subject.registry, subject.solution, subject.component, current, pick_arms, subject.stale)
    if via is not None:   # the metric has cascading conditionals: the latest stage run decides (esoi.optimization.leaderboard.stage_standings)
        return cascade_choice(subject, via, pick_policy, claim_policy)
    beaten = rival_decisions.challengers(rows, current, config.evaluation, pick_arms, per_case, pick_policy)
    if not beaten:
        return None
    winner = ranking.rank({r["impl"]: r for r in beaten})[0]["impl"]
    pair = next(((own, rival) for own, rival in rival_pairing.rival_pairs(rows, current, config.evaluation, pick_arms)[0]
                 if rival["impl"] == winner), None)
    return Choice(winner, pair, False, claim_policy, fraction)


def block_reason(subject: Subject, choice: Choice, own: Row, rival: Row) -> str:
    """Why the switch cannot be promoted now (a result does not count, a required stage is missing, a table default), else ``""``."""
    winner, policy = choice.winner, choice.claim_policy
    why = next((f"{name}: {text}" for name, row in ((subject.current, own), (winner, rival))
                if (text := "its row has no cases_sha" if case_identity.unverified(row) else subject.stale_reason(row))), "")
    if why:
        return f"a result does not count ({why}); re-run `esoi run --stale` on committed code"
    need = policy.require_stage
    waits = stage_missing(subject, winner, need, policy.source("require_stage")) if need else ""
    if waits:
        return waits
    if (subject.table.get(subject.solution["solution_id"]) or {}).get("default"):
        return ("its selection table entry holds its own default; delete that `default` so the records' "
                "`selected` is the only copy, then promote")
    return ""


def chosen_on_text(own: Row, rival: Row, current: str, winner: str, fraction: float) -> str:
    """The sentence naming the selection part a winner was chosen on, when a held-out share was kept out."""
    if not fraction:
        return ""
    return (f"chosen on the selection part ({own.get('cases')} cases, a held-out share of {fraction:g} kept out): {winner} "
            f"{rival.get('passed')}/{rival.get('cases')}, {current} {own.get('passed')}/{own.get('cases')}")


def claim_evidence(subject: Subject, choice: Choice, own: Row, rival: Row, chosen_on: str):
    """The pair of rows and the rule text the evidence rests on; with a held-out share, the held-out claim's rows."""
    arms = subject.arms
    decided = next((d for d in rival_decisions.decisions({impl: rs[-1] for impl, rs in arms.items()}, subject.current, subject.config.evaluation,
                                                         arms, subject.per_case, choice.claim_policy) if d.rival == choice.winner), None)
    if choice.fraction and decided is not None:   # the evidence names the held-out numbers the claim rests on
        own, rival = decided.own, decided.other
    reason = f"{decided.rule}: {decided.text}" if decided else ""
    if choice.fraction:
        reason = f"{chosen_on}; its claim is the held-out result, {reason}"
    return own, rival, reason


def judge_choice(subject: Subject, choice: Choice) -> Proposal:
    """The proposal for a chosen rival: blocked with a reason, or the edits and evidence of the switch."""
    solution, current, today = subject.solution, subject.current, subject.today
    sid, winner, fraction = solution["solution_id"], choice.winner, choice.fraction
    proposal = Proposal(sid, "blocked", current, winner)
    if choice.pair is None:
        proposal.reason = "no run of the two on the same cases and sample"
        return proposal
    own, rival = choice.pair
    chosen_on = chosen_on_text(own, rival, current, winner, fraction)
    own, rival = held_out_parts.whole_row(own), held_out_parts.whole_row(rival)
    blocked = block_reason(subject, choice, own, rival)
    if blocked:
        proposal.reason = blocked
        return proposal
    selected = new_selected(subject, winner)
    if not selected:
        proposal.reason = f"no implementation record or impls file of {winner} to point `selected` at"
        return proposal
    proposal.selected = selected
    own, rival, reason = claim_evidence(subject, choice, own, rival, chosen_on)
    proposal.selected_by = (cascade_evidence if choice.via_cascade else evidence)(own, rival, current, winner, today, reason)
    return finish_switch(proposal, solution, selected)


def finish_switch(proposal: Proposal, solution: Row, selected: str) -> Proposal:
    """The edits of a switch and whether the solution lets it be applied without a person."""
    sid = solution["solution_id"]
    proposal.edits = [f"solutions.csv {sid}: selected {solution.get('selected', '')!r} -> {selected!r}", f"evidence: {proposal.selected_by}"]
    proposal.status = "promote" if (solution.get("promotion") or "").strip().lower() == AUTOMATIC else "propose"
    proposal.reason = ("the solution's `promotion` is automatic" if proposal.status == "promote"
                       else "the solution's `promotion` is not automatic: a person applies this")
    return proposal


def propose(config: Config, registry: Registry, today: Optional[str] = None,
            stale: Callable = stale_reason) -> List[Proposal]:
    """A proposal for each evaluated solution a rival clearly beats, in record order."""
    today = today or datetime.date.today().isoformat()
    history = results_log.all_results(config.results_path)
    per_case = results_log.per_case_rows(config)
    chosen = switching_policy.policies(config, registry, per_case)
    out: List[Proposal] = []
    try:
        table = load_table(config.selection_table, config.root) if config.selection_table else {}
    except Exception:
        table = {}
    for solution in registry.solutions:
        component, current = arm_selection.selected_arm(config, solution, "", registry)
        if not component:
            continue
        arms = history.get(component, {})
        subject = Subject(config, registry, solution, component, current, arms, per_case, stale, today, table)
        if not (solution.get("selected") or "").strip():   # nothing selected yet: the metric makes the first choice, or names a tie
            out.append(first_choice(subject))
            continue
        policy = chosen.get(component) or switching_policy.Policy()
        choice = pick_winner(subject, policy)
        if choice is not None:
            out.append(judge_choice(subject, choice))
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
    folder = next((f for _, f in intents.folders(config) if any(r.get("solution_id") == proposal.solution_id
                                                                 for r in read_csv(f / "solutions.csv"))),
                  intent_folder(config, solution.get("intent_id") or None))
    changes = {"selected": proposal.selected}
    if "selected_by" in read_header(folder / "solutions.csv"):   # the evidence is stored only where the project approved that column
        changes["selected_by"] = proposal.selected_by
    edit_row(folder, "solutions.csv", "solution_id", proposal.solution_id, changes)


def show_and_apply(config: Config, registry: Registry, p: Proposal, dry_run: bool, apply_proposals: bool, say: Callable[[str], None]) -> int:
    """Print a proposal's edits and apply it when the policy (or ``--apply``) allows; returns 1 when applied, else 0."""
    for edit in p.edits:
        say(f"  {edit}")
    if (p.status == "promote" or (apply_proposals and p.status == "propose")) and not dry_run:
        apply(config, registry, p)
        say(f"  {'promoted' if p.status == 'promote' else 'applied'} ({p.reason})")
        return 1
    say(f"  proposal only ({'dry run' if dry_run else p.reason})")
    return 0


def run_cli(config: Config, solution_id: str = "", dry_run: bool = False, apply_proposals: bool = False, say: Callable[[str], None] = print) -> int:
    """Print each proposal; apply those the policy allows. Exit 1 when a rival wins and nothing could be applied."""
    from esoi.structure.intent_registry import registry as registry_module
    from esoi.understanding.review_tracker.interface import tracker
    registry = registry_module.load(config)
    proposals = [p for p in propose(config, registry) if not solution_id or p.solution_id == solution_id]
    if not proposals:
        say("no rival clearly beats a selected implementation: nothing to promote")
        return 0
    applied = 0
    for p in proposals:
        say(f"{p.solution_id}: {p.winner} beats the selected {p.current}" if p.current else
            f"{p.solution_id}: first selection" + (f" {p.winner}" if p.winner else ""))
        if p.status == "blocked":
            say(f"  not promoted: {p.reason}")
            continue
        applied += show_and_apply(config, registry, p, dry_run, apply_proposals, say)
    if applied:
        loaded = registry_module.load(config)
        tracker.write(config, loaded, say=lambda text: None)
        say("rebuilt the review tracker; commit the records, then `esoi run --stale` so the new selection has a current row")
    return 0 if applied == len(proposals) else 1
