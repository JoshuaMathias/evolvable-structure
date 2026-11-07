"""A declarative check for case-driven evaluations: a case names a ``kind`` and its ``args``; the solution
returns a dict; the case's ``expect`` is a small set of checks on that dict, so no scorer holds a per-case
branch and a new case is data only.

``expect`` keys (all optional):
  eq            {key: value}   output[key] must equal value exactly
  has           {key: [item]}  output[key] (a list) must contain every item
  any_of        {key: [[item]]} output[key] (a list) must hold at least one item of every group (several records are
                               equally right for one need, e.g. a problem and its ideal)
  contains      [str]          output["text"] must contain every string
  not_contains  [str]          output["text"] must contain none of them
  max_len       int            len(output["text"]) must not exceed it
  min_len       int            len(output["text"]) must reach it
  approx        {key: [value, tolerance]}   numeric output[key] within tolerance of value
  at_most       {key: number}  numeric output[key] must not exceed the number (a time or size budget)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List


def collection_problems(out: Dict[str, Any], expect: Dict[str, Any]) -> List[str]:
    """Problems with the output's values and lists: ``eq``, ``has`` and ``any_of``."""
    problems: List[str] = []
    for key, want in (expect.get("eq") or {}).items():
        if out.get(key) != want:
            problems.append(f"{key}: expected {want!r}, got {out.get(key)!r}")
    for key, wanted in (expect.get("has") or {}).items():
        have = out.get(key) or []
        problems.extend(f"{key} lacks {item!r}" for item in wanted if item not in have)
    for key, groups in (expect.get("any_of") or {}).items():
        have = out.get(key) or []
        problems.extend(f"{key} holds none of {group!r}" for group in groups if not any(item in have for item in group))
    return problems


def text_problems(text: str, expect: Dict[str, Any]) -> List[str]:
    """Problems with the output's text: ``contains``, ``not_contains``, ``max_len`` and ``min_len``."""
    problems = [f"text lacks {sub!r}" for sub in expect.get("contains") or [] if sub not in text]
    problems += [f"text must not contain {sub!r}" for sub in expect.get("not_contains") or [] if sub in text]
    if "max_len" in expect and len(text) > expect["max_len"]:
        problems.append(f"text is {len(text)} chars, ceiling {expect['max_len']}")
    if "min_len" in expect and len(text) < expect["min_len"]:
        problems.append(f"text is {len(text)} chars, floor {expect['min_len']}")
    return problems


def number_problems(out: Dict[str, Any], expect: Dict[str, Any]) -> List[str]:
    """Problems with the output's numbers: ``approx`` and ``at_most``."""
    problems: List[str] = []
    for key, (want, tol) in (expect.get("approx") or {}).items():
        got = out.get(key)
        if not isinstance(got, (int, float)) or abs(got - want) > tol:
            problems.append(f"{key}: expected {want} within {tol}, got {got!r}")
    for key, ceiling in (expect.get("at_most") or {}).items():
        got = out.get(key)
        if not isinstance(got, (int, float)) or got > ceiling:
            problems.append(f"{key}: {got!r} is over the ceiling {ceiling}")
    return problems


def check(out: Any, expect: Dict[str, Any]) -> List[str]:
    """The list of problems (empty means the case passed)."""
    out = out if isinstance(out, dict) else {"text": str(out)}
    return collection_problems(out, expect) + text_problems(str(out.get("text", "")), expect) + number_problems(out, expect)


def score_kind_case(fn: Callable[[str, dict], Any], case: Dict[str, Any]) -> Dict[str, Any]:
    """Run ``fn(kind, args)`` for one case and compare to ``expect``. Used by every case-driven scorer."""
    try:
        out = fn(case["kind"], case["args"])
    except Exception as exc:  # a solution that raises where the contract says "degrade" fails the case
        if type(exc).__name__ == "BudgetExceeded":  # the call budget aborts the run; it is not a failed case
            raise
        return dict(ok=False, got=case["kind"], note=f"raised {type(exc).__name__}: {exc}")
    problems = check(out, case["expect"])
    return dict(ok=not problems, got=case["kind"], note="ok" if not problems else "; ".join(problems))


def aggregate_by_kind(rows: List[Dict[str, Any]]) -> str:
    """``kind: passed/total`` per case kind, so a weak area shows in the headline."""
    kinds: Dict[str, tuple] = {}
    for r in rows:
        k = r.get("got") or "?"
        p, t = kinds.get(k, (0, 0))
        kinds[k] = (p + bool(r.get("ok")), t + 1)
    return ", ".join(f"{k} {p}/{t}" for k, (p, t) in sorted(kinds.items()))
