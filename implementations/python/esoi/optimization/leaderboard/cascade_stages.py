"""Cascading conditionals: the ordered stages a costly metric is run in, and the selection rule they define.

A metric record may carry a ``cascading_conditionals`` cell (the skill's field of that name). The cell is an ordered list of
stages, cheapest first, joined by `` > ``. A stage is a name and, in brackets, the parameters that identify its results and
the condition for moving on, joined by `` | ``::

    offline [sample=full | real=no | gate=all-pass] > staged [sample=sample | real=yes | gate=competitive | max-age-days=90 | when=a person approved the spend] > whole [sample=full | real=yes]

* ``sample``: which results log rows are this stage: ``full`` (the whole set), ``sample`` (any ``--sample N`` run), an
  exact label such as ``sample:10``, or omitted for any. ``real``: ``yes`` when the stage runs a model, ``no`` when it is the free
  stage (a simulated model counts as no). The case set and the sample place a row, not whether its arm called a model: a row that
  called a model belongs to the first stage that takes it, and a row that called none is a result of every stage that takes its
  cases (it is free, so it has done what each of them asks), so a free arm and a model arm on the same cases are at the same stage.
* ``gate``: what a result must show before the next stage is worth running: ``all-pass`` (every case passed) or
  ``competitive`` (the selected implementation does not have a strictly better result at this stage). ``min-pass-rate`` (a fraction)
  adds a floor. Every stage but the last needs a gate or a floor, since nothing else says when to move on (a stage with ``inherits`` takes the
  foundation's gate and needs none).
* ``inherits``: the name of a stage of the foundation metric this one builds on (``[builds_on]``, ``esoi.runtime.consumer_check.foundation``). The stage is passed only
  when the foundation's stage of that name passed for the foundation arm the consumer's arm names, by the foundation's own gate, so the consumer
  inherits the gate instead of re-proving it. A gate or floor written beside ``inherits`` tightens the inherited one and never loosens it (S47).
* A stage named ``public`` (with ``real=no``; ``when`` is free text) stands for public evidence others measured
  (``esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading``). It claims no results row, is never the stage a choice rests on, needs no gate, and is satisfied for an
  implementation when evidence rows exist for it and grade at least C. It never replaces our own first-stage result.
* ``max-age-days``: a result older than this has expired. ``when``: any other condition, for a person or an AI to judge;
  it is reported, never evaluated. Its text cannot contain ` > `, ` | ` or ``]``.
* ``kind=idea`` (with ``scale``): a stage that needs no implementation. Qualitative questions about an idea are answered and
  converted to a number by ratings or weights, and ``scale`` says where the meaning of every rating value is written (a path or
  a sentence). It evaluates ideas before anything is built, claims no results row, is never the stage a choice rests on and needs
  no gate, like ``public``.

Expiration (the metric's optional ``expiration`` field, the skill's "when do metrics need to be rerun?") is ``never`` or a number
of days (``90 days``). Precedence, most specific first: a stage's ``max-age-days``, the metric's ``expiration``, the project's
``[expiration] default`` in the configuration, and with none of them a result never expires by age. ``load_stages`` applies it.
It is separate from staleness: a result whose implementation, cases or measured code changed is stale and counts as not run
whatever the expiration says (the re-record after an implementation change).

The rules this module carries out, from the skill:

* A stage that was not run has no result (``None``), never an estimate.
* A result expires when the measured implementation or the cases changed since it was recorded (the harness's staleness
  test), or when it is older than the stage's ``max-age-days``. An expired result counts as not run.
* A stage that was run for an implementation version is not run again for a later stage: ``esoi run`` reuses the cases already run
  for the same implementation and cases (``esoi.optimization.measurement_harness.run_log.reusable``), and runs them again only when the implementation changed.
  ``expectation_notes`` says when a list departs from the expected order (a free first stage, cases growing among the stages that call a model, the last stage no narrower than they are).
* Downstream users take the implementation with the highest result at the latest stage that has ever been run, unless
  another implementation scored higher at an earlier stage the two share and has not yet been run at the latest one: that
  implementation stays chosen until it is run there. The first implementation is compared with the others only on rows
  scored on the same cases and sample (``leaderboard.comparable``).

``esoi cascade`` reports all of it; rules S32 and S33 keep the records honest. The functions here take plain rows and a
staleness callable, so they need neither git nor the file system.

This module reads the stages: the ``cascading_conditionals`` parser, the expiration cells and the notes on a list's order."""
from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from esoi.optimization.leaderboard.results_log import Row


SEPARATOR, PAIR_SEPARATOR = " > ", " | "
PUBLIC_STAGE = "public"
KEYS = ("sample", "real", "gate", "min-pass-rate", "max-age-days", "when", "kind", "scale", "inherits")
IDEA_KIND = "idea"
KINDS = (IDEA_KIND,)
EXPIRATION = re.compile(r"^\s*(?:(never)|(\d+)\s*days?)\s*\.?\s*$", re.I)
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
    kind: str = ""
    scale: str = ""
    inherits: str = ""

    @property
    def inherited(self) -> bool:
        """A stage that takes its gate from the foundation metric's stage of that name (``esoi.runtime.consumer_check.foundation``): it is passed only when the
        foundation's stage passed. With no gate of its own and no sample or model of its own it is a pure inheritance and holds no results
        row; with a gate of its own the gate TIGHTENS the inherited one (it can never loosen it: rule S47)."""
        return bool(self.inherits)

    @property
    def idea(self) -> bool:
        """The stage that evaluates ideas before any implementation exists (see the module docstring); it holds no results row."""
        return self.kind == IDEA_KIND

    @property
    def unrun(self) -> bool:
        """A stage ``esoi run`` does not run and no results row belongs to: public evidence, an idea stage, or a pure inheritance."""
        return self.public or self.idea or (self.inherited and not self.gated and not self.sample and self.real is None)

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
                  for i, s in enumerate(stages[:-1]) if not s.gated and not s.unrun and not s.inherited)
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
    kind = values.get("kind", "")
    if kind and kind not in KINDS:
        problems.append(f"kind={kind} is not one of {', '.join(KINDS)}")
        kind = ""
    if kind == IDEA_KIND and not values.get("scale"):
        problems.append("kind=idea needs scale=, where the meaning of every rating value is specified")
    if values.get("inherits") and not ITEM.match(values["inherits"]):
        problems.append(f"inherits={values['inherits']} is not the name of a foundation stage")
    return Stage(name, sample, real, gate, floor, age, values.get("when", ""), kind, values.get("scale", ""), values.get("inherits", "")), problems


def parse_expiration(text: str) -> Tuple[Optional[int], str]:
    """``(days, problem)`` for an ``expiration`` cell: ``never`` or blank is ``None`` days, ``N days`` is N. Anything else is a problem
    (the cell is read by a program, so it is ``never`` or a number of days). The unconfirmed marker is ignored, as in a cascade."""
    text = UNCONFIRMED.sub("", text or "")
    if not text.strip():
        return None, ""
    found = EXPIRATION.match(text)
    if not found:
        return None, f"expiration {text.strip()[:40]!r} is not `never` or a number of days such as `90 days`"
    return (int(found.group(2)) if found.group(2) else None), ("expiration of 0 days would expire every result at once" if found.group(2) == "0" else "")


def default_days(config) -> Tuple[Optional[int], str]:
    """The project's ``[expiration] default`` in days (``None`` for never or unset) and what is wrong with it."""
    return parse_expiration(str((getattr(config, "expiration", None) or {}).get("default", "")))


def load_stages(config, metric: Row) -> Tuple[List[Stage], List[str]]:
    """The stages of a metric's cascade with their expiry settled: a stage's own ``max-age-days``, else the metric's ``expiration``,
    else the project's default, else none (see the module docstring). Also the problems with the list and with the expiration cells."""
    stages, errors = parse(metric.get("cascading_conditionals", ""))
    days, problem = parse_expiration(metric.get("expiration", ""))
    errors = errors + ([problem] if problem else [])
    if not metric.get("expiration", "").strip():
        days, problem = default_days(config)
        errors += [f"[expiration] default: {problem}"] if problem else []
    if days is not None and not problem:
        stages = [s if s.max_age_days is not None or s.unrun else dataclasses.replace(s, max_age_days=days) for s in stages]
    return stages, errors


GATE_STRENGTH = {"": 0, "competitive": 1, "all-pass": 2}


def loosens(own: Stage, theirs: Stage) -> str:
    """Why an inheriting stage's own gate is looser than the foundation stage's it inherits, or an empty string. A consumer may tighten an
    inherited gate (``all-pass`` where the foundation says ``competitive``, a higher ``min-pass-rate``) and never loosen it. A stage with no
    gate of its own inherits the foundation's unchanged, which is not looser."""
    if own.gate and GATE_STRENGTH[own.gate] < GATE_STRENGTH[theirs.gate]:
        return f"gate={own.gate} is looser than the foundation's gate={theirs.gate}"
    if own.min_pass_rate is not None and theirs.min_pass_rate is not None and own.min_pass_rate < theirs.min_pass_rate:
        return f"min-pass-rate={own.min_pass_rate:g} is below the foundation's {theirs.min_pass_rate:g}"
    return ""


def breadth(stage: Stage) -> Optional[float]:
    """How many cases a stage's ``sample`` says it runs: ``full`` or a blank sample is the whole set (infinite here), ``sample:N`` is N,
    and ``sample`` or ``only:`` says nothing comparable (``None``)."""
    if stage.sample in ("", "full"):
        return float("inf")
    return float(stage.sample.split(":")[1]) if re.fullmatch(r"sample:\d+", stage.sample) else None


def expectation_notes(stages: List[Stage]) -> List[str]:
    """What a list does not do of the skill's expectations for cascading conditionals, as notes (never errors: a cascade that
    differs may have a reason, and no stage is required). The expected order:

      1. a stage that needs no implementation (``kind=idea``, qualitative questions turned into a number by ratings, with the
         meaning of every rating value in ``scale``), to evaluate ideas before building;
      2. a free stage on the implementation (``real=no``: a unit test, a syntax check);
      3. a real single case or end-to-end run (``real=yes``, ``sample=sample:1``; a simulated user counts as real);
      4. diverse representative cases, growing (3, 10, 30);
      last: as comprehensive and objective as possible, read as covering no fewer cases than any earlier model-calling stage (it
      need not be the whole set: it may be a real-use or public measure).

    Cases only need to grow among stages of the same cost kind, so a free full-set stage may be followed by one real case. A list
    with fewer than two stages that run, and a stage named ``public``, are not judged."""
    own = [s for s in stages if not s.unrun]
    notes: List[str] = []
    if len(own) < 2:
        return notes
    ideas = [s for s in stages if s.idea]
    if not ideas:
        notes.append("no stage evaluates ideas before implementation; consider a first stage with kind=idea and a scale= that says what every "
                     "rating value means (qualitative questions converted to a number)")
    elif not stages[0].idea:
        notes.append(f"the idea stage {ideas[0].name} should come first, before any stage that needs the implementation")
    if own[0].real is not False:
        notes.append(f"the first stage on the implementation, {own[0].name}, should cost nothing (a unit test or syntax check): "
                     "add real=no, or put a stage that needs no model first (see docs/explanation/first-stage-needs-no-model.md)")
    paid = [s for s in own if s.real is not False]   # a free stage is cheap whatever it covers, so it is not compared for breadth
    if paid and breadth(paid[0]) not in (None, 1.0) and len(paid) > 1:
        notes.append(f"the first stage that calls a model, {paid[0].name}, should be a real single case or end-to-end run (sample=sample:1), "
                     "simulated if needed, before more cases")
    for before, after in zip(paid, paid[1:]):
        low, high = breadth(before), breadth(after)
        if low is not None and high is not None and high < low:
            notes.append(f"stage {after.name} runs fewer cases than {before.name} before it; later stages should be progressively more comprehensive")
    widest = max((b for b in (breadth(s) for s in paid[:-1]) if b is not None), default=None)
    last = breadth(own[-1])
    if own[-1].real is not False and widest is not None and last is not None and last < widest:
        notes.append(f"the last stage, {own[-1].name}, should be the most comprehensive and as objective as possible, "
                     "yet an earlier stage that calls a model covers more cases")
    return notes
