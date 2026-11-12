"""What lead a challenger needs to replace the selected arm: the requirement a cascade stage declares, and the one function that applies it.

A stage of a metric's cascade (``cascade_stages``) may carry three keys. They live in the existing ``stage [key=value | key=value]`` grammar, so no
record field is added::

    whole [sample=full | real=yes | lead=significant:0.05 | lead-on=code:margin:0.1 | tie-break=cost_usd:low,seconds:low]

* ``lead=<requirement>``: the lead the arm ranked highest at the stage needs over another arm for the other arm to be beaten. ``any`` (the default,
  and what every record without the key means) is today's behaviour: the highest result wins. ``margin:<x>`` needs the stage's score (the balanced
  score, else the pass rate) to be at least ``x`` higher. ``significant:<alpha>`` needs a higher pass rate that a two-sided exact Fisher test
  on the pooled pass counts calls significant at ``alpha`` (``stats.fisher_exact_two_sided``; the counts are the sums over the arm's repeated
  runs of the same cases, ``stage_standings.pooled_row``). Requirements joined by ``+`` must all hold (``margin:0.05+significant:0.05``).
* ``lead-on=<part>:<requirement>[,<part>:<requirement>]``: the same requirement scoped to a part of the cases, so the lead must also show there. A
  part is a circumstance of the project (``circumstances.csv``: a filter on the fields of a case, such as its kind or a tag), which the harness already
  records as derived rows of every run (``sample`` is ``slice:<id>``), so a part's pooled counts come from the same repeated runs. An arm with no recorded
  rows for the part has not shown its lead there.
* ``tie-break=<field>:<low|high>[,<field>:<low|high>]``: when the leader's lead is not shown over some arms, those arms and the leader are
  contenders, and the one best on the first field per case (then the next field) wins. ``field`` is a recorded figure (``TIE_FIELDS``), divided by the
  cases of a run. Without a tie-break the selected arm stays when it is a contender (the conservative choice), else the leader is chosen.

``choose`` is the one function the check (S10, S33), ``esoi cascade``, ``esoi leaderboard`` and ``esoi select`` all reach through
``stage_standings.decide``. It reads plain rows and returns ``Choice``, whose ``why`` is the short phrase that says why the winner stands. Standard library only."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import ranking, stats
from esoi.optimization.leaderboard.results_log import Row

MARGIN, SIGNIFICANT = "margin", "significant"
TIE_FIELDS = ("cost_usd", "seconds", "model_calls", "tokens_in", "tokens_out")
DIRECTIONS = ("low", "high")
PART_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
NO_LEAD = 1e-9   # a margin is met when the difference is at least the margin, within rounding


@dataclass(frozen=True)
class Lead:
    """One requirement: ``margin`` (an absolute difference in the stage's score) or ``significant`` (a test at alpha ``value``)."""
    kind: str
    value: float

    def text(self) -> str:
        return f"{self.kind}:{self.value:g}"


@dataclass(frozen=True)
class Requirement:
    """What a stage declares: the whole-metric requirement, a requirement per named part, and the tie-break. Empty when the stage declares none."""
    whole: Tuple[Lead, ...] = ()
    parts: Tuple[Tuple[str, Tuple[Lead, ...]], ...] = ()
    tie_break: Tuple[Tuple[str, str], ...] = ()
    requires: Tuple[Tuple[str, Optional[float], int], ...] = ()   # (component, pass-rate floor or None, minimum runs)

    @property
    def declared(self) -> bool:
        return bool(self.whole or self.parts or self.requires)

    @property
    def required_components(self) -> List[str]:
        return [name for name, _, _ in self.requires]

    @property
    def part_names(self) -> List[str]:
        return [name for name, _ in self.parts]

    def text(self) -> str:
        pieces = [f"lead={'+'.join(l.text() for l in self.whole)}"] if self.whole else []
        pieces += [f"lead-on={name}:{'+'.join(l.text() for l in leads)}" for name, leads in self.parts]
        return " ".join(pieces)


def parse_leads(text: str) -> Tuple[Tuple[Lead, ...], List[str]]:
    """The requirements of one ``lead`` value (``any``, or ``margin:<x>`` and ``significant:<alpha>`` joined by ``+``) and what is wrong with it."""
    problems: List[str] = []
    leads: List[Lead] = []
    items = [i.strip() for i in text.split("+")]
    if items == ["any"]:
        return (), []
    for item in items:
        kind, _, number = item.partition(":")
        try:
            value = float(number)
        except ValueError:
            value = -1.0
        if kind == MARGIN and value > 0:
            leads.append(Lead(MARGIN, value))
        elif kind == SIGNIFICANT and 0 < value < 1:
            leads.append(Lead(SIGNIFICANT, value))
        else:
            problems.append(f"lead `{item[:30]}` is not any, margin:<positive number> or significant:<alpha between 0 and 1>")
    return tuple(leads), problems


def parse_lead_on(text: str) -> Tuple[Tuple[Tuple[str, Tuple[Lead, ...]], ...], List[str]]:
    """The ``(part, requirements)`` pairs of a ``lead-on`` value (``part:requirement`` joined by commas) and what is wrong with it."""
    out: List[Tuple[str, Tuple[Lead, ...]]] = []
    problems: List[str] = []
    for item in (i.strip() for i in text.split(",") if i.strip()):
        name, _, rest = item.partition(":")
        leads, bad = parse_leads(rest) if rest else ((), [f"lead-on `{item[:30]}` is not part:requirement"])
        if not PART_NAME.match(name):
            bad.append(f"lead-on part `{name[:30]}` is not a circumstance id (lower case letters, digits, - and _)")
        if rest == "any":
            bad.append(f"lead-on {name}:any asks for nothing; name a requirement")
        if name in [n for n, _ in out]:
            bad.append(f"lead-on names part {name} twice")
        problems.extend(bad)
        if not bad:
            out.append((name, leads))
    return tuple(out), problems


def parse_tie_break(text: str) -> Tuple[Tuple[Tuple[str, str], ...], List[str]]:
    """The ``(field, direction)`` pairs of a ``tie-break`` value (``field:low|high`` joined by commas) and what is wrong with it."""
    out: List[Tuple[str, str]] = []
    problems: List[str] = []
    for item in (i.strip() for i in text.split(",") if i.strip()):
        name, _, direction = item.partition(":")
        if name in TIE_FIELDS and direction in DIRECTIONS:
            out.append((name, direction))
        else:
            problems.append(f"tie-break `{item[:30]}` is not <field>:<low|high> with a field from {', '.join(TIE_FIELDS)}")
    return tuple(out), problems


def parse_requires(text: str) -> Tuple[Tuple[Tuple[str, Optional[float], int], ...], List[str]]:
    """The ``(component, floor, minimum runs)`` entries of a ``requires`` value: ``<component>[:<floor>[:<runs>]]`` joined by commas (a blank floor, as in
    ``component::3``, asks only for runs)."""
    out: List[Tuple[str, Optional[float], int]] = []
    problems: List[str] = []
    for item in (i.strip() for i in text.split(",") if i.strip()):
        name, _, rest = item.partition(":")
        floor_text, _, runs_text = rest.partition(":")
        try:
            floor = float(floor_text) if floor_text else None
            runs = int(runs_text) if runs_text else 1
            valid = PART_NAME.match(name) and (floor is None or 0 <= floor <= 1) and runs >= 1
        except ValueError:
            valid = False
        if valid:
            out.append((name, floor, runs))
        else:
            problems.append(f"requires `{item[:30]}` is not <component>[:<floor between 0 and 1>[:<minimum runs>]]")
    return tuple(out), problems


def build_requirement(values: Dict[str, str]) -> Tuple[Requirement, List[str]]:
    """The requirement a stage's ``lead``, ``lead-on``, ``tie-break`` and ``requires`` values declare, and what is wrong with them."""
    whole, p1 = parse_leads(values["lead"]) if "lead" in values else ((), [])
    parts, p2 = parse_lead_on(values["lead-on"]) if "lead-on" in values else ((), [])
    ties, p3 = parse_tie_break(values["tie-break"]) if "tie-break" in values else ((), [])
    needs, p4 = parse_requires(values["requires"]) if "requires" in values else ((), [])
    problems = p1 + p2 + p3 + p4
    if ties and not (whole or parts) and not problems:
        problems.append("tie-break has no effect without a lead or lead-on requirement (it breaks the tie of arms whose lead is not shown)")
    return Requirement(whole, parts, ties, needs), problems


def unmet(req: Requirement, impl: str, rows: Dict[str, Dict[str, Row]]) -> str:
    """Why ``impl`` is not selectable at a stage that ``requires`` other components' results, or an empty string. ``rows`` is ``{component: {impl:
    its pooled row}}``. A requirement applies once some arm has the runs it asks for (while none has, the requirement is skipped, so a measurement
    nobody has made yet blocks nobody); then an arm needs that many runs and, when a floor is given, a pooled pass rate at or above it."""
    for name, floor, runs in req.requires:
        have = rows.get(name, {})
        if not any(int(float(r.get("runs") or 1)) >= runs for r in have.values()):
            continue
        row = have.get(impl)
        found = counts(row) if row is not None else None
        if row is None or found is None:
            return f"no counting {name} result"
        if int(float(row.get("runs") or 1)) < runs:
            return f"{int(float(row.get('runs') or 1))} counting {name} run(s), {runs} needed"
        if floor is not None and found[0] / found[1] < floor:
            return f"{name} pass rate {found[0] / found[1]:.3g} is below the floor {floor:g}"
    return ""


def counts(row: Row) -> Optional[Tuple[int, int]]:
    """``(passed, cases)`` of a row, a pool of repeated runs counting every run's cases; ``None`` when the row has no usable counts."""
    try:
        if int(float(row.get("runs") or 0)) > 1:
            found = int(float(row["passed_total"])), int(float(row["cases_total"]))
        else:
            found = int(float(row["passed"])), int(float(row["cases"]))
    except (KeyError, ValueError):
        return None
    return found if found[1] > 0 and 0 <= found[0] <= found[1] else None


def lead_over(lead: Lead, ahead: Row, behind: Row) -> Tuple[bool, str]:
    """``(shown, phrase)``: whether ``ahead`` has the lead over ``behind`` that one requirement asks for, in a short phrase."""
    if lead.kind == MARGIN:
        gap = ranking.pass_rate(ahead) - ranking.pass_rate(behind)
        shown = gap >= lead.value - NO_LEAD
        return shown, f"lead {gap:.3g} {'meets' if shown else 'is below'} the margin {lead.value:g}"
    a, b = counts(ahead), counts(behind)
    if a is None or b is None:
        return False, "no pass counts to test the lead"
    figures = f"lead {a[0]}/{a[1]} vs {b[0]}/{b[1]}"
    if a[0] * b[1] <= b[0] * a[1]:
        return False, f"{figures} is not a higher pass rate"
    shown = stats.fisher_exact_two_sided(a[0], a[1], b[0], b[1]) < lead.value
    return shown, f"{figures} {'significant' if shown else 'not significant'} at {lead.value:g}"


def shown_over(req: Requirement, ahead: str, behind: str, rows: Dict[str, Row], parts: Dict[str, Dict[str, Row]]) -> Tuple[bool, str]:
    """``(shown, phrase)``: whether ``ahead`` has every lead the requirement asks for over ``behind`` (the whole metric, then each part), and the
    phrase of the first lead that is not shown (of the last one that is, when all are)."""
    phrase = ""
    for lead in req.whole:
        shown, phrase = lead_over(lead, rows[ahead], rows[behind])
        if not shown:
            return False, phrase
    for name, leads in req.parts:
        found = parts.get(name, {})
        if ahead not in found or behind not in found:
            return False, f"on {name}: no recorded rows for {ahead if ahead not in found else behind}"
        for lead in leads:
            shown, phrase = lead_over(lead, found[ahead], found[behind])
            phrase = f"on {name}: {phrase}"
            if not shown:
                return False, phrase
    return True, phrase


def per_case(row: Row, name: str) -> Optional[float]:
    """A recorded figure of a run (a pool's mean per run) per case, or ``None`` when the row does not record it (an unknown figure is never read as zero)."""
    text = str(row.get(name) or "").strip()
    try:
        cases = float(row.get("cases") or 0)
        return float(text) / cases if text and cases > 0 else None
    except ValueError:
        return None


def tie_key(req: Requirement, row: Row, impl: str, incumbent: str) -> tuple:
    """The sort key of the tie-break: each field per case in the declared direction (an unknown figure last), then the selected arm, then the name."""
    key: list = []
    for name, direction in req.tie_break:
        value = per_case(row, name)
        key += [value is None, 0.0 if value is None else (value if direction == "low" else -value)]
    return tuple(key) + (impl != incumbent, impl)


def tie_phrase(req: Requirement, winner: str, leader: str) -> str:
    """The short phrase for the tie-break that chose ``winner``."""
    name, direction = req.tie_break[0]
    adjective = {("cost_usd", "low"): "cheaper", ("seconds", "low"): "faster"}.get((name, direction), f"{'lower' if direction == 'low' else 'higher'} {name}")
    return f"{winner} {'is also ' if winner == leader else ''}{adjective} per case"


@dataclass
class Choice:
    """The arm a requirement lets stand and why. ``contenders`` are the arms (leader included) whose lead was not shown, best first; empty when the leader's lead was shown over every arm."""
    winner: str
    why: str = ""
    contenders: List[str] = field(default_factory=list)


def choose(req: Requirement, rows: Dict[str, Row], leader: str, incumbent: str = "", parts: Optional[Dict[str, Dict[str, Row]]] = None) -> Choice:
    """The arm a stage's requirement picks among ``rows`` (each arm's result at the stage, scored on the same cases), where ``leader`` is the arm with
    the highest result. The leader wins when its lead is shown over every other arm. Otherwise the arms it has no shown lead over, and it, are
    contenders: the tie-break picks among them, and with none the selected arm (``incumbent``) stays when it is one of them, else the leader wins."""
    parts = parts or {}
    others = [i for i in (r["impl"] for r in ranking.rank(rows)) if i != leader]
    unshown = [(i, why) for i in others if not (found := shown_over(req, leader, i, rows, parts))[0] for why in [found[1]]]
    if not unshown:
        if not others:
            return Choice(leader)
        last = shown_over(req, leader, others[-1], rows, parts)[1]
        return Choice(leader, f"{leader} has the required lead ({req.text()}) over every other arm; weakest: {last}")
    pool = [leader] + [i for i, _ in unshown]
    reason = unshown[0][1]
    if req.tie_break:
        winner = min(pool, key=lambda i: tie_key(req, rows[i], i, incumbent))
        return Choice(winner, f"{reason}; {tie_phrase(req, winner, leader)}", pool)
    if incumbent in pool:
        return Choice(incumbent, f"{reason}; {incumbent} stays as the selected arm", pool)
    return Choice(leader, f"{reason}; {leader} leads and none of them is selected", pool)
