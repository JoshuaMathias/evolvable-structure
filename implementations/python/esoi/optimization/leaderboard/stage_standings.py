"""Where each implementation stands in a cascade: the stage a result belongs to, which results still count, the implementation the cascade chooses, and the next stage worth running."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import arm_kinds, case_identity, ranking
from esoi.optimization.leaderboard.results_log import Row
from esoi.optimization.leaderboard.cascade_stages import Stage, load_stages


def matches(stage: Stage, row: Row) -> bool:
    """Whether a results row is a result of this stage. The case set and the sample decide it, never whether the arm happened to call a
    model: a ``real=no`` stage takes only rows that called no model (it is the free stage), while a stage that allows a model also takes a
    row that called none, since an arm that needs no model has done everything that stage asks."""
    label = (row.get("sample") or "").strip()
    if stage.unrun:
        return False
    if stage.sample == "full" and label:
        return False
    if stage.sample == "sample" and not label.startswith("sample:"):
        return False
    if stage.sample.startswith(("sample:", "only:")) and label != stage.sample:
        return False
    return stage.real is not False or not ranking.is_sampled(row)   # a stage that allows a model also takes an arm that calls none


def stage_index(stages: List[Stage], row: Row) -> Optional[int]:
    """The first stage a row is a result of, or ``None`` when no stage claims it."""
    return next((i for i, stage in enumerate(stages) if matches(stage, row)), None)


def expiry(stage: Stage, row: Row, today: datetime.date, stale: Callable[[Row], str]) -> str:
    """Why a result no longer counts, or an empty string when it does."""
    if why := stale(row):
        return why
    if stage.max_age_days is not None:
        try:
            age = (today - datetime.date.fromisoformat((row.get("date") or "")[:10])).days
        except ValueError:
            return "its date is unreadable, so its age is unknown"
        if age > stage.max_age_days:
            return f"it is {age} days old, past the {stage.name} stage's maximum age"
    return ""


@dataclass
class Standing:
    """Where one implementation stands: the newest counting result per stage index, and the results that expired."""
    impl: str
    rows: Dict[int, Row] = field(default_factory=dict)
    expired: Dict[int, Tuple[Row, str]] = field(default_factory=dict)

    @property
    def reached(self) -> int:
        """The latest stage with a counting result, or -1 when it has none."""
        return max(self.rows, default=-1)


def standings(stages: List[Stage], history: Dict[str, List[Row]], today: Optional[datetime.date],
              stale: Callable[[Row], str], eval_dir: Optional[Path] = None) -> Dict[str, Standing]:
    """A ``Standing`` per implementation from the results log history (``{impl: rows, oldest first}``). Ablation and
    validity arms are not candidates."""
    today = today or datetime.date.today()
    out: Dict[str, Standing] = {}
    for impl, rows in history.items():
        if not rows or arm_kinds.is_ablation(rows[-1], eval_dir):
            continue
        newest: Dict[int, Row] = {}
        for row in rows:
            if ranking.is_sampled(row) or ranking.is_simulated(row):   # a row that called a model, or a simulated one, is a result of the first stage that takes it
                if (index := stage_index(stages, row)) is not None:
                    newest[index] = row
            else:                             # an arm that calls none is a result of every stage that takes its cases, so it meets the
                for index, stage in enumerate(stages):   # model arms at their stage and the comparison is on the same case set
                    if matches(stage, row):
                        newest[index] = row
        standing = Standing(impl)
        for index, row in newest.items():
            if why := expiry(stages[index], row, today, stale):
                standing.expired[index] = (row, why)
            else:
                standing.rows[index] = row
        out[impl] = standing
    return out


@dataclass
class Decision:
    winner: str = ""
    stage: int = -1                  # the latest stage any counting result exists for
    leader: str = ""                 # the best result at that stage
    pending: List[str] = field(default_factory=list)   # held in place until run at `stage`
    notes: List[str] = field(default_factory=list)


def decide(stages: List[Stage], standing: Dict[str, Standing], eval_dir: Optional[Path] = None) -> Decision:
    """The implementation downstream users take (see the module docstring)."""
    counting = {impl: s for impl, s in standing.items() if s.rows}
    if not counting:
        return Decision(notes=["no stage has a counting result, so nothing is chosen by the metric"])
    latest = max(s.reached for s in counting.values())
    at_latest = {impl: s.rows[latest] for impl, s in counting.items() if latest in s.rows}
    reference = max(at_latest.values(), key=lambda r: (int(float(r.get("cases") or 0)), r.get("date") or "", r["impl"]))
    notes = [f"{impl} was scored at {stages[latest].name} on other cases or a different sample than {reference['impl']}, "
             "so it is not compared" for impl, r in sorted(at_latest.items()) if not case_identity.comparable(r, reference)]
    ranked = ranking.rank({impl: r for impl, r in at_latest.items() if case_identity.comparable(r, reference)})
    leader = ranked[0]["impl"]
    held: Dict[str, Row] = {}
    for impl, s in counting.items():
        if latest in s.rows:
            continue
        shared = [i for i in s.rows if i < latest and i in counting[leader].rows
                  and case_identity.comparable(s.rows[i], counting[leader].rows[i])]
        if shared and ranking.higher(s.rows[max(shared)], counting[leader].rows[max(shared)]):
            held[impl] = s.rows[max(shared)]
    winner = ranking.rank(held)[0]["impl"] if held else leader
    if held:
        notes.append(f"{', '.join(sorted(held))} scored higher than {leader} at an earlier stage and has not been run at "
                     f"{stages[latest].name}; run it there to settle which is better")
    return Decision(winner, latest, leader, sorted(held), notes)


def gate_met(stage: Stage, row: Row, selected_row: Optional[Row], eval_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """Whether a result at this stage earns the next stage, and if not, why."""
    if stage.gate == "all-pass" and ranking.pass_rate(row) < 1:
        return False, "not every case passed"
    if stage.gate == "competitive" and selected_row is not None and ranking.higher(selected_row, row):
        return False, f"{selected_row['impl']} has a better result at this stage"
    if stage.min_pass_rate is not None and ranking.pass_rate(row) < stage.min_pass_rate:
        return False, f"its pass rate is below the stage's minimum of {stage.min_pass_rate:g}"
    return True, ""


def next_stage(stages: List[Stage], mine: Standing, selected: Optional[Standing] = None,
               eval_dir: Optional[Path] = None,
               inherited: Optional[Callable[[Stage], Tuple[bool, str]]] = None) -> Tuple[Optional[int], str]:
    """``(stage index, why)`` for the first stage with no counting result, once every earlier stage's gate is met; else
    ``(None, why nothing is next)``. A stage never run is ``not run``, never an estimate."""
    for index, stage in enumerate(stages):
        if stage.inherited and inherited is not None:
            met, why = inherited(stage)   # the foundation's gate, checked first and never re-proved here
            if not met:
                return None, f"stopped before {stage.name}: the foundation's {stage.inherits} stage has not passed ({why})"
        if stage.unrun:
            continue
        row = mine.rows.get(index)
        if row is None:
            return index, f"expired: {mine.expired[index][1]}" if index in mine.expired else "not run"
        met, why = gate_met(stage, row, selected.rows.get(index) if selected and selected.impl != mine.impl else None, eval_dir)
        if not met:
            return None, f"stopped after {stage.name}: {why}"
    return None, "every stage has a counting result"


def shared_pair(stages: List[Stage], standing: Dict[str, Standing], first: str, second: str) -> Optional[Tuple[Row, Row]]:
    """The two implementations' rows at the latest stage both have a counting result for, scored on the same cases and
    sample, or ``None`` when they share none."""
    a, b = standing.get(first), standing.get(second)
    if a is None or b is None:
        return None
    common = [i for i in a.rows if i in b.rows and case_identity.comparable(a.rows[i], b.rows[i])]
    return (a.rows[max(common)], b.rows[max(common)]) if common else None


def solution_choice(config, registry, solution: Row, component: str, current: str, history: Dict[str, List[Row]],
                    stale: Callable, today: Optional[datetime.date] = None) -> Optional[Tuple[Optional[str], Optional[Tuple[Row, Row]]]]:
    """What the cascade says about a solution's selected arm ``current``, or ``None`` when no linked metric has a readable
    cascade with counting results (the plain comparison then applies). ``(None, None)`` means the selected arm stays;
    otherwise ``(winner, (current's row, winner's row) at their latest shared stage or None)``. ``stale`` is
    ``stale_reasons.stale_reason``."""
    from esoi.structure.intent_registry.tables import ids
    by_id = {m.get("metric_id", ""): m for m in registry.metrics}
    stages: List[Stage] = []
    for metric_id in ids(solution.get("metric_ids", "")):
        found, errors = load_stages(config, by_id.get(metric_id, {}))
        if found and not errors:
            stages = found
            break
    if not stages:
        return None
    standing = standings(stages, history, today, lambda row: stale(config, component, row, True), config.evaluation)
    decision = decide(stages, standing, config.evaluation)
    if not decision.winner:
        return None
    if decision.winner == current:
        return None, None
    return decision.winner, shared_pair(stages, standing, current, decision.winner)
