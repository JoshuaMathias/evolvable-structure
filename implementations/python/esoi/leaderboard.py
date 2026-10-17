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

Only rows scored on the same cases are compared: the same ``cases_sha`` (the case file), the same ``sample`` (``""``
for the full set, ``sample:N`` for the ``--sample N`` selection, ``only:ids`` for ``--only``) and the same case count
(so a log recorded before ``sample`` existed still tells a 40-case run from a 1,137-case one). A score on different
cases is not evidence. Each rival is compared with the selected arm on the newest ``(cases_sha, sample, cases)`` both
have a row for, not on each arm's latest row; a rival that shares none is not compared (UNMEASURED, or "not
comparable" on the board) and a verdict never rests on it. Rows recorded before ``cases_sha`` existed have it blank,
are FLAGGED ``unverified`` and are shown but never treated as evidence against a verified row.

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


def all_results(path: Path) -> Dict[str, Dict[str, List[Row]]]:
    """{component: {impl: [rows, oldest first]}}: every row of the results log, in date order (file order within a date)."""
    out: Dict[str, Dict[str, List[Row]]] = {}
    if not Path(path).exists():
        return out
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if not (row.get("component") and row.get("impl")):
                continue   # a blank or half-written line is no result
            out.setdefault(row["component"], {}).setdefault(row["impl"], []).append(row)
    for impls in out.values():
        for history in impls.values():
            history.sort(key=lambda r: r.get("date") or "")   # stable: a later line of the same date stays later
    return out


def latest_results(path: Path) -> Dict[str, Rows]:
    """{component: {impl: row}} keeping the newest row per implementation."""
    return {comp: {impl: history[-1] for impl, history in impls.items()} for comp, impls in all_results(path).items()}


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


def cases_key(row: Row) -> Tuple[str, str, int]:
    """What a row was scored on: ``(cases_sha, sample, case count)``. ``sample`` is blank for the full set (and for rows
    recorded before the column existed, which the case count then tells apart)."""
    try:
        count = int(float(row.get("cases") or 0))
    except ValueError:
        count = 0
    return (row.get("cases_sha") or "", (row.get("sample") or "").strip(), count)


def comparable(a: Row, b: Row) -> bool:
    """Two rows are comparable only when scored on the same cases: the same case file, the same sample and the same
    number of cases (blank == blank: legacy rows)."""
    return cases_key(a) == cases_key(b)


def describe_cases(row: Row) -> str:
    """``1137 cases`` or ``40 cases (sample:40)``, with the case file when it is recorded."""
    sha, sample, count = cases_key(row)
    return f"{count} cases" + (f" ({sample})" if sample else "") + (f" on cases_sha {sha}" if sha else "")


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


def history_of(rows: Rows, history: Optional[Dict[str, List[Row]]] = None) -> Dict[str, List[Row]]:
    """The rows each arm has, oldest first: ``history`` when given, else just each arm's latest row."""
    return history if history is not None else {impl: [row] for impl, row in rows.items()}


def rival_pairs(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                history: Optional[Dict[str, List[Row]]] = None) -> Tuple[List[Tuple[Row, Row]], List[Tuple[str, str]]]:
    """``(pairs, unmatched)`` for ``selected``. A pair is ``(selected row, rival row)`` scored on the same cases (see
    ``cases_key``): for each rival, the newest key both arms have a row for, and on it each arm's newest row.
    ``unmatched`` is ``(rival, why)`` for each rival (ablation and validity arms excluded) that shares no key, so it is
    not compared at all."""
    arms = history_of(rows, history)
    mine = arms.get(selected) or ([rows[selected]] if selected in rows else [])
    pairs: List[Tuple[Row, Row]] = []
    unmatched: List[Tuple[str, str]] = []
    for impl in sorted(arms):
        theirs = arms[impl]
        if impl == selected or not theirs or is_ablation(theirs[-1], eval_dir):
            continue
        best = None   # (rival position, selected position) of the newest shared key
        for i, rival in enumerate(theirs):
            for j, own in enumerate(mine):
                if comparable(own, rival) and (best is None or (i, j) > best):
                    best = (i, j)
        if best is None:
            if mine:
                unmatched.append((impl, f"scored on {describe_cases(theirs[-1])}, {selected} on "
                                        f"{describe_cases(mine[-1])}: no run of the two on the same cases and sample"))
            continue
        pairs.append((mine[best[1]], theirs[best[0]]))
    return pairs, unmatched


def incomparable_rivals(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                        history: Optional[Dict[str, List[Row]]] = None) -> List[Tuple[str, str]]:
    """``(implementation, reason)`` for each rival that shares no cases and sample with ``selected``: not stale, not
    comparable. Re-run it on the selected arm's sample (``esoi run --stale`` does)."""
    return rival_pairs(rows, selected, eval_dir, history)[1]


def stale_rivals(config: Config, component: str, rows: Rows, selected: str,
                 stale: Callable[[Config, str, Row, bool], str],
                 history: Optional[Dict[str, List[Row]]] = None) -> List[Tuple[str, str]]:
    """``(implementation, reason)`` for each compared rival of ``selected`` whose row no longer counts under the strict
    rules (other cases than on disk, uncommitted code, or measured code that changed since its commit): a verdict that
    rests on it (WIN or TIE) compares the selected arm's current number with a rival's old one. A rival on another
    sample is not stale, it is not compared (``incomparable_rivals``). ``stale`` is ``harness.stale_reason``, passed in
    because it needs git and the leaderboard is the inner layer."""
    pairs, _ = rival_pairs(rows, selected, config.evaluation, history)
    return [(r["impl"], why) for _, r in pairs if (why := stale(config, component, r, True))]


def challengers(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                history: Optional[Dict[str, List[Row]]] = None) -> List[Row]:
    """Rival rows that beat the selected one on the same cases and sample: a pass rate higher by more than the margin,
    or inside it at clearly lower spend without passing less. A rival on other cases is skipped, and an ablation or
    validity arm is never a challenger."""
    better = []
    for cur, r in rival_pairs(rows, selected, eval_dir, history)[0]:
        if clearly_higher(r, cur, eval_dir) or (not clearly_higher(cur, r, eval_dir)
                                                 and cheaper_without_passing_less(r, cur, eval_dir)):
            better.append(r)
    return better


def verdict(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
            history: Optional[Dict[str, List[Row]]] = None) -> Tuple[str, str]:
    """How the selected implementation stands against the other measured ones, as ``(label, detail)``."""
    if rows.get(selected) is None:
        return "UNMEASURED", "the selected implementation has no recorded row"
    pairs, unmatched = rival_pairs(rows, selected, eval_dir, history)
    if not pairs:
        if unmatched:
            return "UNMEASURED", ("no rival was measured on the same cases and sample as the selected "
                                  f"implementation: {'; '.join(f'{i} {why}' for i, why in unmatched)}")
        return "UNMEASURED", "no rival implementation was measured on the same cases"
    beaten_by = [r["impl"] for r in challengers(rows, selected, eval_dir, history)]
    if beaten_by:
        return "LOSS", "beaten by " + ", ".join(sorted(beaten_by))
    tied = []
    for cur, r in pairs:
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
    for cur, r in sorted(pairs, key=lambda pair: pair[1]["impl"]):
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


def solution_verdicts(config: Config, solutions: List[Row], results: Optional[Dict[str, Rows]] = None,
                      history: Optional[Dict[str, Dict[str, List[Row]]]] = None) -> Dict[str, Dict[str, str]]:
    """{solution_id: {"verdict", "detail", "component", "selected_by"}} for every ``eval`` solution, judged on the
    first harness arm of its ``metric_command`` (the primary metric; later arms are listed on the board)."""
    if results is None:
        history = all_results(config.results_path)
        results = {comp: {impl: rows[-1] for impl, rows in impls.items()} for comp, impls in history.items()}
    out = {}
    for row in solutions:
        if (row.get("metric_kind") or "").strip() != "eval":
            continue
        comp, impl = first_arm(config, row.get("metric_command", ""))
        if not comp:
            out[row["solution_id"]] = dict(verdict="UNMEASURED", detail="no harness metric", component="",
                                           selected_by=row.get("selected_by", ""))
            continue
        label, detail = verdict(results.get(comp, {}), impl, config.evaluation, (history or {}).get(comp))
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
    history = all_results(config.results_path)
    results = {comp: {impl: rows[-1] for impl, rows in impls.items()} for comp, impls in history.items()}
    selected = selected_impls(config, registry.solutions)
    invariants = invariant_components(config, registry.solutions)
    flagged = 0
    apart = {c: rows for c, rows in results.items() if invariant_reason(c, invariants, config.evaluation)}
    for component, rows in sorted(results.items()):
        if component in apart:
            continue
        sel = selected.get(component)
        label, detail = verdict(rows, sel, config.evaluation, history[component]) if sel else ("UNMEASURED", "no selected implementation")
        say(f"{component} (selected: {sel or 'none recorded'}) {label}: {detail}")
        for line in format_rows(rows, sel, config.evaluation):
            say(line)
        for impl, why in (incomparable_rivals(rows, sel, config.evaluation, history[component]) if sel else []):
            flagged += 1 if strict else 0
            say(f"  ? {impl} is not comparable with {sel}: {why}; re-run both on the same sample "
                "(`esoi run --stale` re-runs a rival on the selected arm's sample)")
        for r in (challengers(rows, sel, config.evaluation, history[component]) if sel else []):
            flagged += 1
            say(f"  ! {r['impl']} beats the selected {sel}: decide whether to adopt it "
                "(update the solution's `selected` and the live default together)")
        for impl, why in (stale_rivals(config, component, rows, sel, stale, history[component]) if sel and stale else []):
            flagged += 1 if strict else 0
            say(f"  ~ {impl} is a rival the verdict on {sel} rests on, but {why}; re-run it on the current code "
                "before trusting the verdict")
    say("\nBy solution (WIN = the metric chose it; TIE = kept for the reason in selected_by, the metric did not "
        "separate it; UNMEASURED = no rival was compared)")
    for sid, v in sorted(solution_verdicts(config, registry.solutions, results, history).items()):
        reason = f"  kept because: {v['selected_by']}" if v["verdict"] == "TIE" else ""
        say(f"  {v['verdict']:<10} {sid}: {v['detail']}{reason}")
    if apart:
        say("\nInvariant solutions (a rule that holds or does not; listed with their recorded run, never ranked)")
        for component, rows in sorted(apart.items()):
            say(f"{component}: {invariant_reason(component, invariants, config.evaluation)}")
            for line in format_rows(rows, selected.get(component), config.evaluation):
                say(line)
    return 1 if flagged and strict else 0
