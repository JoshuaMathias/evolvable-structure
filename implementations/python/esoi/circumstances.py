"""Circumstances: the situations in which an implementation may do better or worse, defined on something observable.

A circumstance is a row of ``circumstances.csv`` (in any intent folder; every cell is an id, a link or an expression a machine
reads, so no prose field is added)::

    circumstance_id,case_filter,run_filter,problem_ids,solution_ids
    large-file,max_target_lines>400,,use-case-problem,edit-files
    small-model,,model in claude-haiku-5-5|claude-mini-5,use-case-problem,edit-files

* ``case_filter`` is a condition on the fields of a case. It slices the cases of a run: the harness records one derived row per
  circumstance beside the run's own row (``sample`` is ``slice:<id>``), so a slice costs no extra run.
* ``run_filter`` is a condition on the run: the exact ``model`` it recorded and the parameters of its variant name
  (``guard@harness=native,model=haiku``). It holds the run conditions an add-on is justified in, such as the model and the
  harness, so "no add-on, the harness as it is" is an ordinary arm of the same solution measured under the same condition.
* A circumstance with neither is invalid. The id is a name (``esoi.assemble``: lower case letters, digits, ``_`` and ``-``), because
  it becomes the tail of a ``sample`` label and a ``/`` or ``;`` in it would be read as something else.

A condition is terms joined by `` and `` (any case); a term is ``field op value`` with op one of ``= == != < <= > >=``, or
``field in a|b|c`` (an exact match against one of the values, ignoring case). A value has no spaces, and a condition it
cannot read is an error when the table is loaded, never a term that silently matches nothing. A number compares as a number.
A field a case does not carry never matches, but a field no case of the component carries is an error (``check_fields``).
Nothing is selected by a circumstance: slices and verdicts only propose (see the guide). Standard library only.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from . import variants
from .assemble import check_name
from .config import Config
from .intents import read_rows
from .tables import ids

FILE = "circumstances.csv"
IN_TERM = re.compile(r"^([A-Za-z_][\w.]*)\s+in\s+(\S+)$")
OP_TERM = re.compile(r"^([A-Za-z_][\w.]*)\s*(<=|>=|!=|==|=|<|>)\s*(\S+)$")
Term = Tuple[str, str, List[str]]


@dataclass(frozen=True)
class Circumstance:
    circumstance_id: str
    case_filter: str = ""
    run_filter: str = ""
    problem_ids: Tuple[str, ...] = ()
    solution_ids: Tuple[str, ...] = ()


def parse(expression: str) -> List[Term]:
    """The terms of a condition; an empty condition has none. Raises ``ValueError`` naming the term that cannot be read."""
    terms: List[Term] = []
    for text in (t.strip() for t in re.split(r"\s+and\s+", expression or "", flags=re.I) if t.strip()):
        found = IN_TERM.match(text)
        if found:
            terms.append((found.group(1), "in", [v.strip() for v in found.group(2).split("|") if v.strip()]))
            continue
        found = OP_TERM.match(text)
        if not found:
            raise ValueError(f"{text!r} is not `field op value` (op: = == != < <= > >=, no spaces in a value) or `field in a|b`; "
                             "terms are joined by ` and `")
        terms.append((found.group(1), "=" if found.group(2) == "==" else found.group(2), [found.group(3)]))
    return terms


def number(value: Any) -> Optional[float]:
    try:
        return None if isinstance(value, bool) else float(value)
    except (TypeError, ValueError):
        return None


def holds(term: Term, facts: Mapping[str, Any]) -> bool:
    field, op, wanted = term
    if field not in facts:
        return False
    have = facts[field]
    if op in ("=", "!=", "in"):
        same = [number(have) == number(w) if number(have) is not None and number(w) is not None
                else str(have).strip().lower() == w.lower() for w in wanted]
        return (not any(same)) if op == "!=" else any(same)
    left, right = number(have), number(wanted[0])
    if left is None or right is None:
        return False
    return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right}[op]


def matches(expression: str, facts: Mapping[str, Any]) -> bool:
    """Whether every term of the condition holds for these fields; an empty condition holds for everything."""
    return all(holds(term, facts) for term in parse(expression))


def load(config: Config) -> List[Circumstance]:
    """Every circumstance of the repository, in file order. Raises ``ValueError`` naming the row for an id that is not a name
    or is used twice, a row with no condition, or a condition that cannot be read."""
    out: List[Circumstance] = []
    for position, r in enumerate(read_rows(config, FILE), 2):
        c = Circumstance(r.get("circumstance_id", "").strip(), r.get("case_filter", "").strip(), r.get("run_filter", "").strip(),
                         tuple(ids(r.get("problem_ids", ""))), tuple(ids(r.get("solution_ids", ""))))
        try:
            check_name(c.circumstance_id, "circumstance_id")
            if any(c.circumstance_id == o.circumstance_id for o in out):
                raise ValueError(f"the id {c.circumstance_id!r} is used twice")
            if not (c.case_filter or c.run_filter):
                raise ValueError(f"{c.circumstance_id} has neither a case_filter nor a run_filter, so it names no situation")
            parse(c.case_filter), parse(c.run_filter)
        except ValueError as exc:   # AssemblyError is a ValueError
            raise ValueError(f"{FILE} row {position}: {exc}") from exc
        out.append(c)
    return out


def for_component(config: Config, component: str) -> List[Circumstance]:
    """The circumstances of the solutions that a harness command of ``component`` measures (none when there is no table)."""
    found = load(config)
    if not found:
        return []
    from .registry import harness_arms, load as load_registry
    wanted = {s["solution_id"] for s in load_registry(config).solutions
              if any(c == component for c, _ in harness_arms(config, s.get("metric_command", "")))}
    return [c for c in found if wanted & set(c.solution_ids)]


def digest(circs: List[Circumstance]) -> str:
    """Short hash of what defines the slices: a recorded slice row is stale when this changed since it was derived."""
    return hashlib.sha256(repr([(c.circumstance_id, c.case_filter, c.run_filter) for c in circs]).encode()).hexdigest()[:8]


def check_fields(circs: List[Circumstance], cases: List[Mapping[str, Any]]) -> None:
    """Raise ``ValueError`` for a ``case_filter`` field that no case carries: a typo would otherwise match nothing, silently."""
    known = {key for case in cases for key in case}
    for c in circs:
        for field, _, _ in parse(c.case_filter):
            if field not in known:
                raise ValueError(f"{FILE} {c.circumstance_id}: case_filter names {field!r}, which no case of the component has "
                                 f"(fields: {', '.join(sorted(map(str, known)))})")


def run_context(model: Optional[str], impl: str) -> Dict[str, Any]:
    """What a run's ``run_filter`` is read against: its recorded model, then the parameters of its variant name."""
    return {**({"model": model} if model else {}), **variants.split(impl)[1]}


def case_circumstances(circs: List[Circumstance], case: Mapping[str, Any]) -> List[str]:
    """Ids, in file order, of the circumstances whose ``case_filter`` this case satisfies (those without one are run-only)."""
    return [c.circumstance_id for c in circs if c.case_filter and matches(c.case_filter, case)]


def slices(circs: List[Circumstance], cases: List[Mapping[str, Any]], context: Mapping[str, Any]) -> Dict[str, List[int]]:
    """``{circumstance id: positions of the cases in it}`` for a run under ``context``: the circumstances whose run filter the
    run satisfies, and the cases satisfying their case filter (all of them when it is empty). Empty slices are left out."""
    out: Dict[str, List[int]] = {}
    for c in circs:
        if matches(c.run_filter, context):
            found = [i for i, case in enumerate(cases) if matches(c.case_filter, case)]
            if found:
                out[c.circumstance_id] = found
    return out
