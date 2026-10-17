"""Which implementation of each evaluated solution is best, from the committed results log.

``esoi leaderboard [--strict]`` reads ``results.csv`` (the latest row per component and implementation, written by
``esoi run --record``) and the registry (which implementation each solution selects). It prints a ranking per
component and flags every challenger that beats the selected implementation: a pass rate higher by more than the
stated margin, or a pass rate inside it at clearly lower spend. ``--strict`` exits 1 when one does, so a pipeline
can surface "a better implementation exists" without a human reading the implementations. The leaderboard only
ranks; switching the live implementation stays a deliberate decision.

A solution whose ``metric_kind`` is ``invariant`` (a rule that holds or does not, with an ``invariant_reason``
saying why "best" cannot vary) is listed apart, under "Invariant solutions", with its recorded run and never ranked.
So is a component that carries an ``invariant.txt`` (complementary arms of one evaluated solution).

Only rows with the same ``cases_sha`` as the selected row are compared: a score on a different case file is not
evidence. Rows recorded before ``cases_sha`` existed have it blank, are FLAGGED ``unverified`` and are shown but
never treated as evidence against a verified row (``comparable`` keeps them apart).

Verdicts: WIN (it beats every rival on the same cases), TIE (a rival is inside the noise, so the selection is kept
for a reason outside the number), LOSS (a rival beats it), UNMEASURED (no rival was compared). Noise: exact pass
counts and a spend tolerance when no model was called; a pass-rate margin and a wider spend tolerance when one
was, because sampled, model-judged runs move between re-runs. A component folder may carry ``noise.json`` such as
``{"pass_margin": 0.15, "spend_tolerance": 0.2}`` (its own measured re-run swing).

Functions that look at implementation files take ``eval_dir`` (the folder of component folders); without it they
rank rows only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .config import Config
from .registry import Registry, first_arm, harness_arms

Row = Dict[str, str]
Rows = Dict[str, Row]


def cases_files(component: str, eval_dir: Path) -> List[Path]:
    """The case files a component is scored on: ``cases.json`` (or ``cases.csv`` when the dataset is reviewed as a
    sheet), plus every ``datasets/*.json`` of a component whose cases live in a dataset folder."""
    folder = Path(eval_dir) / component
    main = next((folder / n for n in ("cases.json", "cases.csv") if (folder / n).is_file()), None)
    return ([main] if main else []) + sorted((folder / "datasets").glob("*.json"))


def cases_digest(component: str, eval_dir: Path) -> str:
    """Short hash of everything ``cases_files`` names: the ``cases_sha`` a recorded run is pinned to. Line endings
    are normalised first, because a dataset reviewed as a sheet comes back from the sheet with either kind."""
    files = cases_files(component, eval_dir)
    if not files:
        return ""
    return hashlib.sha256(b"".join(f.read_bytes().replace(b"\r\n", b"\n") for f in files)).hexdigest()[:8]


def invariant_components(config: Config, solutions: List[Row]) -> Dict[str, str]:
    """{component: invariant_reason} for every component named by the metric_command of an ``invariant`` solution."""
    out = {}
    for row in solutions:
        if (row.get("metric_kind") or "").strip() != "invariant":
            continue
        for comp, _ in harness_arms(config, row.get("metric_command", "")):
            out[comp] = row.get("invariant_reason", "").strip()
    return out


def invariant_reason(component: str, solution_invariants: Optional[Dict[str, str]] = None,
                     eval_dir: Optional[Path] = None) -> str:
    """Why the component is not ranked: the ``invariant_reason`` of its invariant solution, or the reason in
    ``<component>/invariant.txt`` when its implementations are complementary (not alternatives)."""
    if solution_invariants and component in solution_invariants:
        return solution_invariants[component]
    if eval_dir is not None:
        note = Path(eval_dir) / component / "invariant.txt"
        if note.is_file():
            return note.read_text(encoding="utf-8").strip()
    return ""


def latest_results(path: Path) -> Dict[str, Rows]:
    """{component: {impl: row}} keeping the newest row per implementation."""
    out: Dict[str, Rows] = {}
    if not Path(path).exists():
        return out
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if not (row.get("component") and row.get("impl")):
                continue   # a blank or half-written line is no result
            prev = out.setdefault(row["component"], {}).get(row["impl"])
            if prev is None or (row.get("date") or "") >= (prev.get("date") or ""):
                out[row["component"]][row["impl"]] = row
    return out


def selected_impls(config: Config, solutions: List[Row]) -> Dict[str, str]:
    """{component: selected impl name} for solutions whose metric is one or more harness commands."""
    out: Dict[str, str] = {}
    for row in solutions:
        for comp, impl in harness_arms(config, row.get("metric_command", "")):
            out.setdefault(comp, impl)   # a row may name more than one arm: each is that arm's selection
    return out


def pass_rate(row: Row) -> float:
    """Passed over cases; a blank or malformed count reads as zero, so one bad line cannot stop the whole board."""
    def count(name: str) -> int:
        try:
            return int(float(row.get(name) or 0))
        except ValueError:
            return 0
    return count("passed") / max(count("cases"), 1)


def dollars(row: Row) -> float:
    """The recorded dollar cost; a model-calling run whose cost is blank (no price known) counts as unbounded, never
    as free."""
    if cost_known(row):
        return float(row["cost_usd"])
    return float("inf") if is_sampled(row) else 0.0


def cost_known(row: Row) -> bool:
    """Whether the row records a dollar cost (a blank cell means the price was unknown; 0 is a real zero)."""
    return row.get("cost_usd") is not None and str(row["cost_usd"]).strip() != ""


def rank(rows: Rows) -> List[Row]:
    """Best first: pass rate, then cost (lower is better)."""
    return sorted(rows.values(), key=lambda r: (-pass_rate(r), dollars(r), r["impl"]))


def unverified(row: Row) -> bool:
    """A row recorded without provenance (no ``cases_sha``): shown, flagged, never trusted as evidence."""
    return not (row.get("cases_sha") or "").strip()


def comparable(a: Row, b: Row) -> bool:
    """Two rows are comparable only when scored on the same case file (blank == blank: legacy rows)."""
    return (a.get("cases_sha") or "") == (b.get("cases_sha") or "")


ARM_MARKER = re.compile(r'\s*"""\s*(ABLATION|BASELINE|FLOOR|ALTERNATIVE|VALIDITY)')
NOT_RIVALS = ("ablation", "validity")   # shown and tagged, never offered as the thing to adopt


def arm_kind(row: Row, eval_dir: Optional[Path] = None) -> str:
    """What an implementation is for, from the first word of its module docstring: ``ablation`` (a part of a
    candidate measured alone), ``baseline`` (a floor someone would plausibly ship; ``FLOOR`` counts), ``validity``
    (the metric's own offline check that it can tell good from bad, which no implementation can lose to),
    ``alternative``, or ``""`` for live code. Shown beside every row so a reader can tell a rival from a reference."""
    if eval_dir is None:
        return ""
    path = Path(eval_dir) / row.get("component", "") / "impls" / (row["impl"] + ".py")
    if not path.is_file():
        return ""
    found = ARM_MARKER.match(path.read_text(encoding="utf-8"))
    if not found:
        return ""
    return {"FLOOR": "baseline"}.get(found.group(1), found.group(1).lower())


def is_ablation(row: Row, eval_dir: Optional[Path] = None) -> bool:
    """True when the implementation is no rival: an ABLATION returns less than the whole job, and a VALIDITY arm
    checks the metric rather than competing on it, so both are ranked and never offered as the thing to adopt."""
    return arm_kind(row, eval_dir) in NOT_RIVALS


COST_TIE_TOLERANCE = 0.10        # spend within 10% is a tie for deterministic runs: noise must not flip a selection
SAMPLED_PASS_MARGIN = 0.10       # sampled, model-judged runs: pass rates within 10 percentage points are a tie
SAMPLED_SPEND_TOLERANCE = 0.15   # and spend within 15% is a tie


def is_sampled(row: Row) -> bool:
    """A run that called a model: its pass rate and tokens move between re-runs of the same code."""
    return int(float(row.get("model_calls") or 0)) > 0


def noise(row: Row, other: Row, eval_dir: Optional[Path] = None) -> Tuple[float, float]:
    """``(pass_margin, spend_tolerance)`` inside which two rows are a TIE (see the module docstring)."""
    if not (is_sampled(row) or is_sampled(other)):
        return 0.0, COST_TIE_TOLERANCE
    margin, tolerance = SAMPLED_PASS_MARGIN, SAMPLED_SPEND_TOLERANCE
    component = row.get("component") or other.get("component") or ""
    if component and eval_dir is not None:
        setting = Path(eval_dir) / component / "noise.json"
        if setting.is_file():
            found = json.loads(setting.read_text(encoding="utf-8"))
            margin = float(found.get("pass_margin", margin))
            tolerance = float(found.get("spend_tolerance", tolerance))
    return margin, tolerance


def spend(row: Row) -> Tuple[str, float]:
    """What a run consumed: tokens when the run reports them (dollars swing with caching), else the dollars."""
    tokens = float(row.get("tokens_in") or 0) + float(row.get("tokens_out") or 0)
    return ("tokens", tokens) if tokens > 0 else ("usd", dollars(row))


def clearly_cheaper(row: Row, other: Row, eval_dir: Optional[Path] = None) -> bool:
    """True when ``row`` spent more than the spend tolerance less than ``other``, in the same unit."""
    (unit, mine), (other_unit, theirs) = spend(row), spend(other)
    if unit != other_unit:
        unit, (mine, theirs) = "usd", (dollars(row), dollars(other))
    return mine < theirs * (1 - noise(row, other, eval_dir)[1])


def clearly_higher(row: Row, other: Row, eval_dir: Optional[Path] = None) -> bool:
    """True when ``row`` passes more than the pass margin above ``other``."""
    return Fraction(pass_rate(row)).limit_denominator(10000) - Fraction(pass_rate(other)).limit_denominator(10000) \
        > Fraction(noise(row, other, eval_dir)[0]).limit_denominator(10000)


def cheaper_without_passing_less(row: Row, other: Row, eval_dir: Optional[Path] = None) -> bool:
    """Spend settles a comparison only when the cheaper side passes at least as much."""
    return pass_rate(row) >= pass_rate(other) and clearly_cheaper(row, other, eval_dir)


def rival_rows(rows: Rows, selected: str, eval_dir: Optional[Path] = None) -> List[Row]:
    """The rows a verdict on ``selected`` rests on: comparable to it (same cases) and not an ablation or validity arm."""
    cur = rows.get(selected)
    if cur is None:
        return []
    return [r for r in rows.values() if r["impl"] != selected and comparable(r, cur) and not is_ablation(r, eval_dir)]


def stale_rivals(config: Config, component: str, rows: Rows, selected: str,
                 stale: Callable[[Config, str, Row, bool], str]) -> List[Tuple[str, str]]:
    """``(implementation, reason)`` for each rival of ``selected`` whose recorded row no longer counts under the strict
    rules (other cases, uncommitted code, or measured code that changed since its commit): a verdict that rests on it
    (WIN or TIE) compares the selected arm's current number with a rival's old one. ``stale`` is
    ``harness.stale_reason``, passed in because it needs git and the leaderboard is the inner layer."""
    return [(r["impl"], why) for r in rival_rows(rows, selected, config.evaluation)
            if (why := stale(config, component, r, True))]


def challengers(rows: Rows, selected: str, eval_dir: Optional[Path] = None) -> List[Row]:
    """Implementations that beat the selected one on pass rate by more than the margin, or stay inside it at
    clearly lower spend without passing less. Rows scored on a different ``cases_sha`` than the selected one are
    skipped, and an ablation or validity arm is never a challenger."""
    cur = rows.get(selected)
    if cur is None:
        return []
    better = []
    for r in rows.values():
        if r["impl"] == selected or not comparable(r, cur) or is_ablation(r, eval_dir):
            continue
        if clearly_higher(r, cur, eval_dir) or (not clearly_higher(cur, r, eval_dir)
                                                 and cheaper_without_passing_less(r, cur, eval_dir)):
            better.append(r)
    return better


def verdict(rows: Rows, selected: str, eval_dir: Optional[Path] = None) -> Tuple[str, str]:
    """How the selected implementation stands against the other measured ones, as ``(label, detail)``."""
    cur = rows.get(selected)
    if cur is None:
        return "UNMEASURED", "the selected implementation has no recorded row"
    rivals = rival_rows(rows, selected, eval_dir)
    if not rivals:
        return "UNMEASURED", "no rival implementation was measured on the same cases"
    beaten_by = [r["impl"] for r in challengers(rows, selected, eval_dir)]
    if beaten_by:
        return "LOSS", "beaten by " + ", ".join(sorted(beaten_by))
    tied = []
    for r in rivals:
        if clearly_higher(cur, r, eval_dir) or cheaper_without_passing_less(cur, r, eval_dir):
            continue
        margin, tolerance = noise(cur, r, eval_dir)
        tied.append((r["impl"], margin, tolerance))
    if tied:
        names = ", ".join(sorted(t[0] for t in tied))
        margin, tolerance = max(t[1] for t in tied), max(t[2] for t in tied)
        if margin:
            return "TIE", (f"within the stated margin of {names}: pass rate inside {margin * 100:.0f} percentage "
                           f"points and spend inside {tolerance * 100:.0f}% (sampled, model-judged runs move that "
                           "much between re-runs), so the metric does not separate them")
        return "TIE", (f"passes as many cases as {names} at spend within {tolerance * 100:.0f}% (or lower), so the "
                       "metric does not separate them")
    reasons = []
    for r in sorted(rivals, key=lambda r: r["impl"]):
        if clearly_higher(cur, r, eval_dir):
            margin = noise(cur, r, eval_dir)[0]
            reasons.append(f"passes more cases than {r['impl']}"
                           + (f" by more than the {margin * 100:.0f} point margin" if margin else ""))
        else:
            (_, theirs), (_, ours) = spend(r), spend(cur)
            saved = 1 - ours / theirs if theirs and spend(r)[0] == spend(cur)[0] else 0.0
            reasons.append(f"same pass rate as {r['impl']} at {saved:.0%} lower spend" if saved
                           else f"same pass rate as {r['impl']} at lower spend")
    return "WIN", "; ".join(reasons)


def solution_verdicts(config: Config, solutions: List[Row], results: Optional[Dict[str, Rows]] = None
                      ) -> Dict[str, Dict[str, str]]:
    """{solution_id: {"verdict", "detail", "component", "selected_by"}} for every ``eval`` solution, judged on the
    first harness arm of its ``metric_command`` (the primary metric; later arms are listed on the board)."""
    results = latest_results(config.results_path) if results is None else results
    out = {}
    for row in solutions:
        if (row.get("metric_kind") or "").strip() != "eval":
            continue
        comp, impl = first_arm(config, row.get("metric_command", ""))
        if not comp:
            out[row["solution_id"]] = dict(verdict="UNMEASURED", detail="no harness metric", component="",
                                           selected_by=row.get("selected_by", ""))
            continue
        label, detail = verdict(results.get(comp, {}), impl, config.evaluation)
        out[row["solution_id"]] = dict(verdict=label, detail=detail, component=comp,
                                       selected_by=row.get("selected_by", ""))
    return out


def tokens_label(row: Row) -> str:
    """Tokens in and out, compact (``1.29M``, ``610k``, ``0``): the number spend verdicts are decided on."""
    total = float(row.get("tokens_in") or 0) + float(row.get("tokens_out") or 0)
    return f"{total / 1e6:.2f}M" if total >= 1e6 else f"{total / 1e3:.0f}k" if total >= 1e3 else f"{total:.0f}"


def format_rows(rows: Rows, sel: Optional[str], eval_dir: Optional[Path] = None) -> List[str]:
    lines = []
    for r in rank(rows):
        mark = "*" if r["impl"] == sel else " "
        flag = "  [unverified: no cases_sha, recorded before provenance]" if unverified(r) else ""
        kind = arm_kind(r, eval_dir)
        tag = f"  [{kind.upper()}]" if kind else ""
        lines.append(f"  {mark} {r['impl']:<20} {r['passed']}/{r['cases']} (held-out {r.get('heldout', '')}) "
                     f"calls={r.get('model_calls', '')} tokens={tokens_label(r)} "
                     f"cost={'$%.4f' % float(r['cost_usd']) if cost_known(r) else 'unknown'}  "
                     f"{r.get('date', '')}{tag}{flag}")
        if (r.get("details") or "").strip():
            lines.append(f"      per-case reasons: {r['details'].strip()}")
    return lines


def board(config: Config, registry: Registry, strict: bool = False, say: Callable[[str], None] = print,
          stale: Optional[Callable[[Config, str, Row, bool], str]] = None) -> int:
    """Print the leaderboard. Returns 1 when ``strict`` and a challenger beats a selected implementation, or a verdict
    rests on a rival recorded before the measured code changed (``stale`` is ``harness.stale_reason``; without it
    only the cases are compared)."""
    results = latest_results(config.results_path)
    selected = selected_impls(config, registry.solutions)
    invariants = invariant_components(config, registry.solutions)
    flagged = 0
    apart = {c: rows for c, rows in results.items() if invariant_reason(c, invariants, config.evaluation)}
    for component, rows in sorted(results.items()):
        if component in apart:
            continue
        sel = selected.get(component)
        label, detail = verdict(rows, sel, config.evaluation) if sel else ("UNMEASURED", "no selected implementation")
        say(f"{component} (selected: {sel or 'none recorded'}) {label}: {detail}")
        for line in format_rows(rows, sel, config.evaluation):
            say(line)
        cur = rows.get(sel)
        for r in rows.values():
            if cur is not None and r["impl"] != sel and not comparable(r, cur):
                say(f"  ? {r['impl']} was scored on different cases (cases_sha {r.get('cases_sha') or 'blank'} "
                    f"vs {cur.get('cases_sha') or 'blank'}): not comparable, re-run both on the same cases")
        for r in challengers(rows, sel, config.evaluation):
            flagged += 1
            say(f"  ! {r['impl']} beats the selected {sel}: decide whether to adopt it "
                "(update the solution's `selected` and the live default together)")
        for impl, why in (stale_rivals(config, component, rows, sel, stale) if sel and stale else []):
            flagged += 1 if strict else 0
            say(f"  ~ {impl} is a rival the verdict on {sel} rests on, but {why}; re-run it on the current code "
                "before trusting the verdict")
    say("\nBy solution (WIN = the metric chose it; TIE = kept for the reason in selected_by, the metric did not "
        "separate it; UNMEASURED = no rival was compared)")
    for sid, v in sorted(solution_verdicts(config, registry.solutions, results).items()):
        reason = f"  kept because: {v['selected_by']}" if v["verdict"] == "TIE" else ""
        say(f"  {v['verdict']:<10} {sid}: {v['detail']}{reason}")
    if apart:
        say("\nInvariant solutions (a rule that holds or does not; listed with their recorded run, never ranked)")
        for component, rows in sorted(apart.items()):
            say(f"{component}: {invariant_reason(component, invariants, config.evaluation)}")
            for line in format_rows(rows, selected.get(component), config.evaluation):
                say(line)
    return 1 if flagged and strict else 0
