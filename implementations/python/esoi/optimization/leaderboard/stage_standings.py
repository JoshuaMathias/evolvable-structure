"""Where each implementation stands in a cascade: the stage a result belongs to, which results still count, the implementation the cascade chooses, and the next stage worth running."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import arm_kinds, case_identity, ranking
from esoi.optimization.leaderboard import results_log
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
    """Where one implementation stands: its counting result per stage index (the pool of its repeated runs), and the results that expired."""
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
    validity arms are not candidates. Repeated runs of one arm at one stage are pooled (``pooled_row``): the stage's result is
    the arm's repeats on the same cases that still count, so noise between runs does not decide a ranking."""
    today = today or datetime.date.today()
    out: Dict[str, Standing] = {}
    for impl, rows in history.items():
        if not rows or arm_kinds.is_ablation(rows[-1], eval_dir):
            continue
        standing = Standing(impl)
        for index, group in rows_per_stage(stages, rows).items():
            if why := expiry(stages[index], group[-1], today, stale):
                standing.expired[index] = (group[-1], why)
            else:
                counting = [r for r in group if same_version(r, group[-1]) and not expiry(stages[index], r, today, stale)]
                standing.rows[index] = pooled_row(counting)
        out[impl] = standing
    return out


def rows_per_stage(stages: List[Stage], rows: List[Row]) -> Dict[int, List[Row]]:
    """Every row of an arm at each stage it is a result of, oldest first."""
    found: Dict[int, List[Row]] = {}
    for row in rows:
        if ranking.is_sampled(row) or ranking.is_simulated(row):   # a row that called a model, or a simulated one, is a result of the first stage that takes it
            if (index := stage_index(stages, row)) is not None:
                found.setdefault(index, []).append(row)
        else:                             # an arm that calls none is a result of every stage that takes its cases, so it meets the
            for index, stage in enumerate(stages):   # model arms at their stage and the comparison is on the same case set
                if matches(stage, row):
                    found.setdefault(index, []).append(row)
    return found


def same_version(row: Row, other: Row) -> bool:
    """Whether two rows are repeats of one arm: scored on the same cases and sample, on the same commit, and not on uncommitted code
    (a dirty tree names no one version of the code, so its rows are never pooled)."""
    sha = (row.get("git_sha") or "").strip()
    return row is other or (bool(sha) and not sha.endswith("-dirty") and sha == (other.get("git_sha") or "").strip()
                            and case_identity.comparable(row, other))


POOLED_MEANS = ("model_calls", "tokens_in", "tokens_out", "cost_usd", "seconds")


def mean_of(rows: List[Row], key: str) -> str:
    """The mean of a numeric column over the rows, blank when a row does not record it (a blank cost stays unknown, never free)."""
    values = [float(r[key]) for r in rows if str(r.get(key) or "").strip()]
    return "" if len(values) < len(rows) else f"{sum(values) / len(values):.6g}"


def pooled_history(history: Dict[str, List[Row]], stale: Callable[[Row], str]) -> Dict[str, List[Row]]:
    """A results history (``{impl: rows, oldest first}``) with each arm's repeated runs on the same cases and sample read as one result: the
    rows that still count (``stale`` says why a row does not) and share a ``cases_key`` and a commit (``same_version``) become one ``pooled_row``
    placed where the newest of them stood; a row that no longer counts stays as it is, so an old run of other code never joins a pool.
    Named cases and slices are not pooled."""
    out: Dict[str, List[Row]] = {}
    for impl, rows in history.items():
        groups: Dict[tuple, List[int]] = {}
        for position, row in enumerate(rows):
            sha = (row.get("git_sha") or "").strip()
            if sha and not sha.endswith("-dirty") and not results_log.is_partial(row) and not stale(row):
                groups.setdefault((case_identity.cases_key(row), sha), []).append(position)
        merged = {members[-1]: pooled_row([rows[i] for i in members]) for members in groups.values() if len(members) > 1}
        dropped = {i for members in groups.values() if len(members) > 1 for i in members[:-1]}
        out[impl] = [merged.get(i, row) for i, row in enumerate(rows) if i not in dropped]
    return out


def pooled_row(rows: List[Row]) -> Row:
    """One result for an arm from its repeated runs on the same cases: the newest row, with ``runs`` the number pooled, the pass counts
    summed (``passed_total`` of ``cases_total``, which ranking reads when the rows carry no balanced score), the balanced score and
    the per-run figures (model calls, tokens, cost, seconds) averaged, so a pooled arm is ranked in the same units as an arm run once
    and ``cases`` still identifies the case set. One row is returned as it is: a single run is a pool of one."""
    if len(rows) < 2:
        return rows[-1]
    pooled = dict(rows[-1])
    pooled["runs"] = str(len(rows))
    pooled["passed_total"] = str(sum(ranking.passes(r) for r in rows))
    pooled["cases_total"] = str(sum(int(float(r.get("cases") or 0)) for r in rows))
    for key in POOLED_MEANS:
        pooled[key] = mean_of(rows, key)
    balanced = [r.get("balanced") for r in rows]
    pooled["balanced"] = f"{sum(float(b) for b in balanced) / len(rows):.6g}" if all(str(b or "").strip() for b in balanced) else ""
    return pooled


@dataclass
class Decision:
    winner: str = ""
    stage: int = -1                  # the latest stage any counting result exists for
    leader: str = ""                 # the best result at that stage
    pending: List[str] = field(default_factory=list)   # held in place until run at `stage`
    notes: List[str] = field(default_factory=list)


def held_in_place(counting: Dict[str, "Standing"], latest: int, leader: str) -> Dict[str, Row]:
    """The arms with no result at the latest stage whose earlier shared stage beat the leader's: held in place until run there."""
    held: Dict[str, Row] = {}
    for impl, s in counting.items():
        if latest in s.rows:
            continue
        shared = [i for i in s.rows if i < latest and i in counting[leader].rows
                  and case_identity.comparable(s.rows[i], counting[leader].rows[i])]
        if shared and ranking.higher(s.rows[max(shared)], counting[leader].rows[max(shared)]):
            held[impl] = s.rows[max(shared)]
    return held


def decide(stages: List[Stage], standing: Dict[str, Standing], eval_dir: Optional[Path] = None) -> Decision:
    """The implementation downstream users take (see the module docstring)."""
    counting = {impl: s for impl, s in standing.items() if s.rows}
    if not counting:
        return Decision(notes=["no stage has a counting result, so nothing is chosen by the metric"])
    latest = max(s.reached for s in counting.values())
    at_latest = {impl: s.rows[latest] for impl, s in counting.items() if latest in s.rows}
    reference = case_identity.largest_run(at_latest)
    notes = [f"{impl} was scored at {stages[latest].name} on other cases or a different sample than {reference['impl']}, "
             "so it is not compared" for impl, r in sorted(at_latest.items()) if not case_identity.comparable(r, reference)]
    ranked = ranking.rank(case_identity.comparable_with(at_latest, reference))
    leader = ranked[0]["impl"]
    held = held_in_place(counting, latest, leader)
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
        if stage.inherited and inherited is not None and not (foundation := inherited(stage))[0]:   # the foundation's gate, checked first and never re-proved here
            return None, f"stopped before {stage.name}: the foundation's {stage.inherits} stage has not passed ({foundation[1]})"
        if stage.unrun:
            continue
        row = mine.rows.get(index)
        if row is None:
            return index, f"expired: {mine.expired[index][1]}" if index in mine.expired else "not run"
        met, why = gate_met(stage, row, rival_row(selected, mine, index), eval_dir)
        if not met:
            return None, f"stopped after {stage.name}: {why}"
    return None, "every stage has a counting result"


def rival_row(selected: Optional["Standing"], mine: "Standing", index: int) -> Optional[Row]:
    """The selected arm's row at the stage, when the arm being asked about is another arm."""
    return selected.rows.get(index) if selected and selected.impl != mine.impl else None


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
