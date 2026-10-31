"""Cascading conditionals: the ordered stages a costly metric is run in, and the selection rule they define.

A metric record may carry a ``cascading_conditionals`` cell (the skill's field of that name). The cell is an ordered list of
stages, cheapest first, joined by `` > ``. A stage is a name and, in brackets, the parameters that identify its results and
the condition for moving on, joined by `` | ``::

    offline [sample=full | real=no | gate=all-pass] > staged [sample=sample | real=yes | gate=competitive | max-age-days=90 | when=a person approved the spend] > whole [sample=full | real=yes]

* ``sample``: which results log rows are this stage: ``full`` (the whole set), ``sample`` (any ``--sample N`` run), an
  exact label such as ``sample:10``, or omitted for any. ``real``: ``yes`` when the run calls a model, ``no`` when it does
  not (a simulated model counts as no). A row belongs to the first stage it matches.
* ``gate``: what a result must show before the next stage is worth running: ``all-pass`` (every case passed) or
  ``competitive`` (the selected implementation does not clearly beat it at this stage). ``min-pass-rate`` (a fraction)
  adds a floor. Every stage but the last needs a gate or a floor, since nothing else says when to move on.
* A stage named ``public`` (with ``real=no``; ``when`` is free text) stands for public evidence others measured
  (``esoi.evidence``). It claims no results row, is never the stage a choice rests on, needs no gate, and is satisfied for an
  implementation when evidence rows exist for it and grade at least C. It never replaces our own first-stage result.
* ``max-age-days``: a result older than this has expired. ``when``: any other condition, for a person or an AI to judge;
  it is reported, never evaluated. Its text cannot contain ` > `, ` | ` or ``]``.

The rules this module carries out, from the skill:

* A stage that was not run has no result (``None``), never an estimate.
* A result expires when the measured implementation or the cases changed since it was recorded (the harness's staleness
  test), or when it is older than the stage's ``max-age-days``. An expired result counts as not run.
* Downstream users take the implementation with the highest result at the latest stage that has ever been run, unless
  another implementation scored higher at an earlier stage the two share and has not yet been run at the latest one: that
  implementation stays chosen until it is run there. The first implementation is compared with the others only on rows
  scored on the same cases and sample (``leaderboard.comparable``).

``esoi cascade`` reports all of it; rules S32 and S33 keep the records honest. The functions here take plain rows and a
staleness callable, so they need neither git nor the file system.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import leaderboard
from .leaderboard import Row

SEPARATOR, PAIR_SEPARATOR = " > ", " | "
PUBLIC_STAGE = "public"
KEYS = ("sample", "real", "gate", "min-pass-rate", "max-age-days", "when")
GATES = ("all-pass", "competitive")
SAMPLE_LABEL = re.compile(r"^(full|sample|sample:\d+|only:\S+)$")
ITEM = re.compile(r"^\s*([a-z][a-z0-9-]*)\s*(?:\[(.*)\])?\s*$", re.S)
# The convention for prose an AI wrote and a person has not confirmed yet; it is not part of the list.
UNCONFIRMED = re.compile(r"^\s*unconfirmed:[^.]*?\bto confirm\.\s*", re.I)


@dataclass(frozen=True)
class Stage:
    name: str
    sample: str = ""
    real: Optional[bool] = None
    gate: str = ""
    min_pass_rate: Optional[float] = None
    max_age_days: Optional[int] = None
    when: str = ""

    @property
    def gated(self) -> bool:
        return bool(self.gate) or self.min_pass_rate is not None

    @property
    def public(self) -> bool:
        """The stage that stands for public evidence (see the module docstring); it is not run, so it holds no results."""
        return self.name == PUBLIC_STAGE


def parse(text: str) -> Tuple[List[Stage], List[str]]:
    """The stages in a ``cascading_conditionals`` cell and what is wrong with it. An empty cell is no cascade."""
    text = UNCONFIRMED.sub("", text or "")
    if not text.strip():
        return [], []
    stages: List[Stage] = []
    errors: List[str] = []
    for position, part in enumerate(text.split(SEPARATOR), 1):
        found = ITEM.match(part)
        if not found:
            errors.append(f"stage {position} ({part.strip()[:40]!r}) is not `name` or `name [key=value | key=value]`")
            continue
        name, body = found.group(1), found.group(2) or ""
        values: Dict[str, str] = {}
        for chunk in (c for c in body.split(PAIR_SEPARATOR) if c.strip()):
            key, equals, value = (piece.strip() for piece in chunk.partition("="))
            if not equals or key not in KEYS or not value:
                errors.append(f"stage {name}: `{chunk.strip()[:40]}` is not key=value with a key from {', '.join(KEYS)}")
            else:
                values[key] = value
        stage, problems = build(name, values)
        errors.extend(f"stage {name}: {p}" for p in problems)
        if stage.public and stage.real is not False:
            errors.append(f"stage {name} stands for public evidence, so it needs real=no (it runs nothing)")
        stages.append(stage)
    names = [s.name for s in stages]
    errors.extend(f"stage name {n!r} is used twice" for n in sorted({n for n in names if names.count(n) > 1}))
    errors.extend(f"stage {s.name} has no gate or min-pass-rate, so nothing says when to move on to {stages[i + 1].name}"
                  for i, s in enumerate(stages[:-1]) if not s.gated and not s.public)
    return stages, errors


def build(name: str, values: Dict[str, str]) -> Tuple[Stage, List[str]]:
    problems: List[str] = []
    sample = values.get("sample", "")
    if sample and not SAMPLE_LABEL.match(sample):
        problems.append(f"sample={sample} is not full, sample, sample:N or only:ids")
        sample = ""
    real = {"yes": True, "no": False}.get(values.get("real", ""))
    if "real" in values and real is None:
        problems.append(f"real={values['real']} is not yes or no")
    gate = values.get("gate", "")
    if gate and gate not in GATES:
        problems.append(f"gate={gate} is not one of {', '.join(GATES)}")
        gate = ""
    floor = age = None
    if "min-pass-rate" in values:
        try:
            floor = float(values["min-pass-rate"])
            if not 0 <= floor <= 1:
                raise ValueError
        except ValueError:
            problems.append(f"min-pass-rate={values['min-pass-rate']} is not a fraction between 0 and 1")
            floor = None
    if "max-age-days" in values:
        if values["max-age-days"].isdigit() and int(values["max-age-days"]) > 0:
            age = int(values["max-age-days"])
        else:
            problems.append(f"max-age-days={values['max-age-days']} is not a positive whole number")
    return Stage(name, sample, real, gate, floor, age, values.get("when", "")), problems


def matches(stage: Stage, row: Row) -> bool:
    """Whether a results row is a result of this stage."""
    label = (row.get("sample") or "").strip()
    if stage.public:
        return False
    if stage.sample == "full" and label:
        return False
    if stage.sample == "sample" and not label.startswith("sample:"):
        return False
    if stage.sample.startswith(("sample:", "only:")) and label != stage.sample:
        return False
    return stage.real is None or leaderboard.is_sampled(row) == stage.real


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
        if not rows or leaderboard.is_ablation(rows[-1], eval_dir):
            continue
        newest: Dict[int, Row] = {}
        for row in rows:
            if (index := stage_index(stages, row)) is not None:
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
             "so it is not compared" for impl, r in sorted(at_latest.items()) if not leaderboard.comparable(r, reference)]
    ranked = leaderboard.rank({impl: r for impl, r in at_latest.items() if leaderboard.comparable(r, reference)})
    leader = ranked[0]["impl"]
    held: Dict[str, Row] = {}
    for impl, s in counting.items():
        if latest in s.rows:
            continue
        shared = [i for i in s.rows if i < latest and i in counting[leader].rows
                  and leaderboard.comparable(s.rows[i], counting[leader].rows[i])]
        if shared and leaderboard.clearly_higher(s.rows[max(shared)], counting[leader].rows[max(shared)], eval_dir):
            held[impl] = s.rows[max(shared)]
    winner = leaderboard.rank(held)[0]["impl"] if held else leader
    if held:
        notes.append(f"{', '.join(sorted(held))} scored higher than {leader} at an earlier stage and has not been run at "
                     f"{stages[latest].name}; run it there to settle which is better")
    return Decision(winner, latest, leader, sorted(held), notes)


def gate_met(stage: Stage, row: Row, selected_row: Optional[Row], eval_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """Whether a result at this stage earns the next stage, and if not, why."""
    if stage.gate == "all-pass" and leaderboard.pass_rate(row) < 1:
        return False, "not every case passed"
    if stage.gate == "competitive" and selected_row is not None and leaderboard.clearly_higher(selected_row, row, eval_dir):
        return False, f"{selected_row['impl']} clearly beats it at this stage"
    if stage.min_pass_rate is not None and leaderboard.pass_rate(row) < stage.min_pass_rate:
        return False, f"its pass rate is below the stage's minimum of {stage.min_pass_rate:g}"
    return True, ""


def next_stage(stages: List[Stage], mine: Standing, selected: Optional[Standing] = None,
               eval_dir: Optional[Path] = None) -> Tuple[Optional[int], str]:
    """``(stage index, why)`` for the first stage with no counting result, once every earlier stage's gate is met; else
    ``(None, why nothing is next)``. A stage never run is ``not run``, never an estimate."""
    for index, stage in enumerate(stages):
        if stage.public:
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
    common = [i for i in a.rows if i in b.rows and leaderboard.comparable(a.rows[i], b.rows[i])]
    return (a.rows[max(common)], b.rows[max(common)]) if common else None


def solution_choice(config, registry, solution: Row, component: str, current: str, history: Dict[str, List[Row]],
                    stale: Callable, today: Optional[datetime.date] = None) -> Optional[Tuple[Optional[str], Optional[Tuple[Row, Row]]]]:
    """What the cascade says about a solution's selected arm ``current``, or ``None`` when no linked metric has a readable
    cascade with counting results (the plain comparison then applies). ``(None, None)`` means the selected arm stays;
    otherwise ``(winner, (current's row, winner's row) at their latest shared stage or None)``. ``stale`` is
    ``harness.stale_reason``."""
    from .tables import ids
    by_id = {m.get("metric_id", ""): m for m in registry.metrics}
    stages: List[Stage] = []
    for metric_id in ids(solution.get("metric_ids", "")):
        found, errors = parse(by_id.get(metric_id, {}).get("cascading_conditionals", ""))
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


def run_command(component: str, impl: str, stage: Stage) -> str:
    """The ``esoi run`` line that records a result for this stage. It is a suggestion: a stage with ``real=yes`` calls a
    model, so it needs the metric run policy's estimate, budget and approval first."""
    flag = f" --sample {stage.sample[len('sample:'):]}" if stage.sample.startswith("sample:") else ""
    pick = " (choose the sample size)" if stage.sample == "sample" else ""
    return f"esoi run {component} --impl {impl}{flag} --record{pick}"


def describe(row: Optional[Row]) -> str:
    return "not run" if row is None else f"{row.get('passed', '?')}/{row.get('cases', '?')} on {row.get('date', '?')}"


def public_lines(evidence_module, config, registry, solution_id: str, graded, stages: List[Stage], say: Callable[[str], None]) -> None:
    """The graded public evidence of each implementation of a solution, labelled as such. It is not a result: it is never in the
    standings, never chooses an implementation, and a ``public`` stage reads it only to say whether it is satisfied."""
    if not graded:
        return
    stage = next((s for s in stages if s.public), None)
    for impl, keys in evidence_module.implementation_candidates(config, registry, solution_id).items():
        found = evidence_module.lines_for_implementation(graded, keys)
        if not found:
            continue
        met, why = evidence_module.public_stage_met(found)
        gate = f" [public stage {'satisfied' if met else 'not satisfied'}: {why}]" if stage else ""
        say(f"  public evidence for {impl} (others' measurements, not our result){gate}")
        for estimate in found:
            say(f"    {estimate.line()}")
            if estimate.needs_own_run:
                say(f"      to settle it: {estimate.settle}")


def run_cli(config, solution: str = "", strict: bool = False, say: Callable[[str], None] = print,
            today: Optional[datetime.date] = None) -> int:
    """``esoi cascade [SOLUTION]``: each stage, every implementation's result per stage (a stage not run says so), which
    implementation the cascade chooses against the selected one, and the next stage worth running. With ``strict`` it
    exits 1 when the chosen implementation is not the selected one."""
    from . import evidence as evidence_module, harness, registry as registry_module
    from .tables import ids
    loaded = registry_module.load(config)
    history = leaderboard.all_results(config.results_path)
    evidence_rows = evidence_module.load_for(config)
    graded = evidence_module.estimates(evidence_rows, today) if evidence_rows else {}
    found, behind = 0, 0
    for metric in loaded.metrics:
        stages, errors = parse(metric.get("cascading_conditionals", ""))
        owners = ids(metric.get("solution_ids", ""))
        if not stages and not errors or (solution and solution not in owners):
            continue
        found += 1
        say(f"{metric.get('metric_id', '')}: {' > '.join(s.name for s in stages) or '(no valid stage)'}")
        for line in errors:
            say(f"  problem: {line}")
        for owner in owners:
            public_lines(evidence_module, config, loaded, owner, graded, stages, say)
        component, chosen = next(iter(registry_module.harness_arms(config, metric.get("command", ""))), ("", ""))
        if not stages or not component or component not in history:
            say("  no results yet: every stage is not run" if stages else "  fix the list to read it")
            continue
        standing = standings(stages, history[component], today, lambda row: harness.stale_reason(config, component, row, True),
                             config.evaluation)
        for impl, s in sorted(standing.items()):
            say(f"  {impl}: " + "; ".join(f"{stage.name} {describe(s.rows.get(i))}"
                                           + (f" (expired: {s.expired[i][1]})" if i in s.expired else "")
                                           for i, stage in enumerate(stages) if not stage.public))
        decision = decide(stages, standing, config.evaluation)
        for note in decision.notes:
            say(f"  note: {note}")
        if decision.winner:
            say(f"  chosen by the cascade: {decision.winner} (latest stage run: {stages[decision.stage].name}; "
                f"selected in the records: {chosen or 'none'})")
            behind += bool(chosen and chosen != decision.winner)
        selected = standing.get(chosen)
        for impl, s in sorted(standing.items()):
            index, why = next_stage(stages, s, selected, config.evaluation)
            if index is not None:
                extra = f"; also check: {stages[index].when}" if stages[index].when else ""
                say(f"  next for {impl}: {stages[index].name} ({why}): {run_command(component, impl, stages[index])}{extra}")
            else:
                say(f"  next for {impl}: nothing ({why})")
    if solution and not found:
        say(f"no cascading conditionals are recorded for {solution}")
    return 1 if strict and behind else 0
