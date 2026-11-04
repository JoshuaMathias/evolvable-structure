"""Which implementation of each evaluated solution is best, from the committed results log.

``esoi leaderboard [--strict]`` reads ``results.csv`` (the latest row per component and implementation, written by
``esoi run --record``) and the registry (which implementation each solution selects). It prints a ranking per
component and flags every challenger that should replace the selected implementation (see the rule below). ``--strict`` exits 1 when one does, so a pipeline
can surface "a better implementation exists" without a human reading the implementations. The leaderboard only
ranks; switching the live implementation stays a deliberate decision.

Every metric outputs a number, so every evaluated solution is ranked the same way. A component that carries an
``invariant.txt`` (complementary arms of one evaluated solution, not alternatives) is the exception: it is listed
apart, with its recorded run, and never ranked.

Only rows scored on the same cases are compared: the same ``cases_sha`` (the case file), the same ``sample`` (``""``
for the full set, ``sample:N`` for the ``--sample N`` selection, ``only:ids`` for ``--only``) and the same case count
(so a log recorded before ``sample`` existed still tells a 40-case run from a 1,137-case one). A score on different
cases is not evidence. Each rival is compared with the selected arm on the newest ``(cases_sha, sample, cases)`` both
have a row for, not on each arm's latest row; a rival that shares none is not compared (UNMEASURED, or "not
comparable" on the board) and a verdict never rests on it. Rows recorded before ``cases_sha`` existed have it blank,
are FLAGGED ``unverified`` and are shown but never treated as evidence against a verified row.

Only rows that scored a whole run decide the default verdict: a run of named cases (``only:ids``) and a derived row for one
circumstance (``slice:id``, see ``esoi.circumstances``) are partial, so recording one never changes which arm the default
verdict favours. Slice rows are kept out of ``all_results`` and read with ``slice_results``; the same ``verdict`` judges them.

Verdicts: WIN (it is shown, or guessed, better than every rival), TIE (no rival is shown better, so the selection stays),
LOSS (a rival should replace it), UNMEASURED (no rival was compared).

The rule is pragmatic and statistical. The authoritative metric is the pass rate, or the balanced score when the component sets
``[balance.<component>]`` (so cost and speed count only through the metric, with its own weights). By default the arm with the
highest result on the authoritative metric at the latest comparable stage wins and is selected, significant or not: a new solution
with no end users yet, or a lead at a cascade stage that is not the highest, should still use the best it has. The verdict states
whether the lead is significant (a two-sided exact paired test: McNemar for pass or fail per case, an exact sign test on the paired
per-case balanced scores, Holm-adjusted across the rivals, at ``alpha`` 0.05, divided by the number of looks when the pair was run at several stages; with the test, p and the disagreeing cases named) or
"best guess, not yet significant". Without per-case rows, aggregate pass counts on the same cases and sample get Fisher's exact
two-sided test; where no test is possible (a balanced aggregate, a figure with no case count) the lead is a best guess on the point
estimate. With ``[selection] holdout = F`` each case set is split by a hash of the case id: the leader is chosen on the selection part and every claim is computed on the held-out part alone. Exactly equal estimates keep the selected arm. The way to turn a best guess into evidence is more cases (size the highest
cascade stage so a meaningful difference can reach significance), never a margin. The library specifies nothing else: cost, speed and
dependencies enter only through the authoritative metric, which is responsible for them. A project (``[switching]``) or a solution
(``[switching.<solution id>]``, which overrides the project) may opt into a stricter policy: ``require_significance = true`` (the
selected arm stays until a rival is significantly better, for solutions with production end users), a lower ``alpha``, ``min_cases``
shared cases, and a cascade stage that must have been reached (``require_stage``). ``best_guess_switch = false`` is a deprecated
alias of ``require_significance = true``. The verdict names the requirement that applied.

Functions that look at implementation files take ``eval_dir`` (the folder of component folders); without it they
rank rows only.
"""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import stats
from .config import Config
from .registry import Registry, first_arm, harness_arms
from .tables import ids
from .variants import base_of

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


def invariant_reason(component: str, eval_dir: Optional[Path] = None) -> str:
    """Why the component is not ranked: the reason in ``<component>/invariant.txt`` when its implementations are
    complementary (not alternatives)."""
    if eval_dir is not None:
        note = Path(eval_dir) / component / "invariant.txt"
        if note.is_file():
            return note.read_text(encoding="utf-8").strip()
    return ""


SLICE_MARK = "slice:"


def slice_id(row: Row) -> str:
    """The circumstance a derived row describes (``slice:small-file`` or ``sample:12/slice:small-file``), else ``""``."""
    last = (row.get("sample") or "").strip().rsplit("/", 1)[-1]
    return last[len(SLICE_MARK):] if last.startswith(SLICE_MARK) else ""


def is_partial(row: Row) -> bool:
    """A row that scored named cases (``only:``) or one circumstance's cases (``slice:``): never the default verdict's evidence."""
    return bool(slice_id(row)) or (row.get("sample") or "").strip().startswith("only:")


def all_results(path: Path, slices: bool = False) -> Dict[str, Dict[str, List[Row]]]:
    """{component: {impl: [rows, oldest first]}}: every row of the results log, in date order (file order within a date).
    Derived slice rows are left out unless ``slices`` is true (``slice_results`` reads those)."""
    out: Dict[str, Dict[str, List[Row]]] = {}
    if not Path(path).exists():
        return out
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if not (row.get("component") and row.get("impl")):
                continue   # a blank or half-written line is no result
            if bool(slice_id(row)) != slices:
                continue
            out.setdefault(row["component"], {}).setdefault(row["impl"], []).append(row)
    for impls in out.values():
        for history in impls.values():
            history.sort(key=lambda r: r.get("date") or "")   # stable: a later line of the same date stays later
    return out


def slice_results(path: Path) -> Dict[str, Dict[str, Dict[str, List[Row]]]]:
    """{component: {circumstance id: {impl: [rows, oldest first]}}}: the derived slice rows of the results log."""
    out: Dict[str, Dict[str, Dict[str, List[Row]]]] = {}
    for comp, impls in all_results(path, slices=True).items():
        for impl, history in impls.items():
            for found in history:
                out.setdefault(comp, {}).setdefault(slice_id(found), {}).setdefault(impl, []).append(found)
    return out


def as_whole(row: Row) -> Row:
    """A slice row read as the run of its slice's cases: the ``slice:`` part of its ``sample`` label dropped, so ``verdict``
    judges the arms of one circumstance exactly as it judges the arms of one case set."""
    head, _, last = (row.get("sample") or "").strip().rpartition("/")
    return {**row, "sample": head if last.startswith(SLICE_MARK) else (row.get("sample") or "")}


def slice_verdicts(component: str, incumbent: str, slices: Dict[str, Dict[str, Dict[str, List[Row]]]],
                   eval_dir: Optional[Path] = None) -> List[Tuple[str, str, str]]:
    """``(circumstance id, verdict label, detail)`` of ``incumbent`` in each circumstance the component has slice rows for
    (``slice_results``). A slice verdict is a PROPOSAL read by a person: nothing is selected by it. Name the incumbent the
    marginal-value rule names (the no-add-on baseline arm, to which a tie goes), not the arm that is selected. An add-on must show
    its marginal value, so a slice is judged with ``require_significance``."""
    out = []
    for cid, group in sorted(slices.get(component, {}).items()):
        history = {impl: [as_whole(r) for r in found] for impl, found in group.items()}
        out.append((cid, *verdict({impl: found[-1] for impl, found in history.items()}, incumbent, eval_dir, history,
                                  policy=Policy(require_significance=True))))
    return out


def latest_results(path: Path, whole: bool = False) -> Dict[str, Rows]:
    """{component: {impl: row}} keeping the newest row per implementation. With ``whole``, the newest row that scored a whole
    run (not ``only:`` or ``slice:``), the row staleness is judged on; an arm with none is left out."""
    return {comp: {impl: found[-1] for impl, history in impls.items() if (found := [r for r in history if not (whole and is_partial(r))])}
            for comp, impls in all_results(path).items()}


def selected_arm(config: Config, row: Row, component: str = "", registry: Optional[Registry] = None) -> Tuple[str, str]:
    """``(component, arm)`` the solution's selection means on ``component`` (default: the first component of its metric command).
    The command lists the arms to measure; the choice is the solution's ``selected`` in the records: a name, ``solution:name`` or
    the path of the implementation's file, read as an arm when the command lists it or the results log holds a run of it on the component. The
    registry maps a file path to its arm name. With no such ``selected`` it is the first arm the command lists for the component. Promotion therefore changes
    ``selected`` and never the command."""
    arms = harness_arms(config, row.get("metric_command", ""))
    if not arms:
        return "", ""
    component = component or arms[0][0]
    listed = [impl for comp, impl in arms if comp == component]
    cell = (row.get("selected") or "").strip()
    sid = row.get("solution_id", "")
    records = {r.get("implementation_id", ""): r for r in (registry.implementations if registry is not None else [])}
    chosen = ""
    if cell:
        by_path = next((i.split(":", 1)[-1] for i, r in records.items() if i.startswith(f"{sid}:") and (r.get("filepath") or "").strip() == cell), "")
        chosen = by_path or cell.split(":", 1)[-1]
    known = chosen in listed or chosen in all_results(config.results_path).get(component, {})
    return component, chosen if chosen and known else (listed[0] if listed else "")


def selected_impls(config: Config, solutions: List[Row], registry: Optional[Registry] = None) -> Dict[str, str]:
    """{component: selected impl name} for solutions whose metric is one or more harness commands (see ``selected_arm``)."""
    out: Dict[str, str] = {}
    for row in solutions:
        for comp, _ in harness_arms(config, row.get("metric_command", "")):
            out.setdefault(comp, selected_arm(config, row, comp, registry)[1])
    return out


def pass_rate(row: Row) -> float:
    """The score a row is ranked by. A row recorded with a balanced score (its component sets ``[balance.<component>]``,
    see ``esoi.balance``) ranks by that, so accuracy bought with a large price in money or time does not win by itself.
    Otherwise passed over cases; a blank or malformed count reads as zero, so one bad line cannot stop the whole board."""
    try:
        if str(row.get("balanced") or "").strip():
            return float(row["balanced"])
    except ValueError:
        pass
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
FLOOR_KINDS = ("baseline",)   # a floor that only shows what the live arms must beat: ranked and shown, never selected or promoted
NOT_RIVALS = ("ablation", "validity")   # shown and tagged, never offered as the thing to adopt


def arm_kind(row: Row, eval_dir: Optional[Path] = None) -> str:
    """What an implementation is for, from the first word of its module docstring: ``ablation`` (a part of a
    candidate measured alone), ``baseline`` (a floor someone would plausibly ship; ``FLOOR`` counts), ``validity``
    (the metric's own offline check that it can tell good from bad, which no implementation can lose to),
    ``alternative``, or ``""`` for live code. Shown beside every row so a reader can tell a rival from a reference."""
    if eval_dir is None:
        return ""
    path = Path(eval_dir) / row.get("component", "") / "impls" / (base_of(row["impl"]) + ".py")
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


SIMULATED = "simulated"


def is_simulated(row: Row) -> bool:
    """A run of an arm that declared itself a deterministic stand-in for a model (model ``simulated``)."""
    return (row.get("model") or "").strip() == SIMULATED


def is_sampled(row: Row) -> bool:
    """A run that called a model: its pass rate and tokens move between re-runs of the same code. A simulated run
    counts the calls a model would make but is deterministic."""
    return int(float(row.get("model_calls") or 0)) > 0 and not is_simulated(row)


def higher(row: Row, other: Row) -> bool:
    """True when ``row`` has the strictly better point estimate on the authoritative metric. A screen for cascading stages, never a
    reason to switch the selected arm (that takes ``decisions``)."""
    return estimate(row) > estimate(other)


def history_of(rows: Rows, history: Optional[Dict[str, List[Row]]] = None) -> Dict[str, List[Row]]:
    """The rows each arm has, oldest first: ``history`` when given, else just each arm's latest row."""
    return history if history is not None else {impl: [row] for impl, row in rows.items()}


def rival_pairs(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                history: Optional[Dict[str, List[Row]]] = None) -> Tuple[List[Tuple[Row, Row]], List[Tuple[str, str]]]:
    """``(pairs, unmatched)`` for ``selected``. A pair is ``(selected row, rival row)`` scored on the same cases (see
    ``cases_key``): for each rival, the newest key both arms have a row for, and on it each arm's newest row.
    ``unmatched`` is ``(rival, why)`` for each rival (ablation and validity arms excluded) that shares no key, so it is
    not compared at all."""
    every = history_of(rows, history)
    arms = {impl: [r for r in found if not is_partial(r)] for impl, found in every.items()}
    mine = arms.get(selected) or []
    pairs: List[Tuple[Row, Row]] = []
    unmatched: List[Tuple[str, str]] = []
    for impl in sorted(arms):
        theirs = arms[impl]
        if impl == selected or is_ablation((theirs or every[impl])[-1], eval_dir):
            continue
        if not theirs:   # recorded only on named cases (only:) or slices: never silently skipped
            if mine:
                unmatched.append((impl, f"scored on {every[impl][-1].get('sample')} only; not comparable: named cases only (no run of the whole set)"))
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


PER_CASE_KEY = ("component", "impl", "cases_sha", "sample", "case_id")
ALPHA = stats.ALPHA


def per_case_rows(config: Config, every: bool = False) -> List[Row]:
    """The per-case log (``esoi run --record`` writes it; empty when the project has none yet): the newest row of each (arm,
    cases, sample, case) or, with ``every``, every row in file order. A repeated header line (two recorders creating the
    file together) is not a row."""
    path = config.root / config.per_case
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("component") != "component"]
    return rows if every else list({tuple(r.get(k) or "" for k in PER_CASE_KEY): r for r in rows}.values())


@dataclass(frozen=True)
class Policy:
    """How one solution is judged. The default: a rival with a higher result on the authoritative metric replaces the selected arm,
    and the verdict says whether that lead is significant (two-sided paired test, ``alpha`` 0.05 divided by the looks at the pair, Holm across rivals) or a best guess.
    A project or a solution may opt into a stricter policy: ``require_significance`` (the selected arm stays until a rival is
    significantly better), a lower ``alpha``, a minimum number of shared cases (``min_cases``) and a cascade stage that must have been
    reached (``require_stage``, applied when promoting). ``origin`` says which level (``project`` or ``solution``) set each
    requirement, so a verdict can name it."""
    alpha: float = ALPHA
    min_cases: int = 0
    require_stage: str = ""
    require_significance: bool = False
    origin: Tuple[Tuple[str, str], ...] = ()
    holdout: float = 0.0   # [selection] holdout: the share of each case set kept out of the choice; claims are computed on it alone

    def source(self, key: str) -> str:
        return dict(self.origin).get(key, "configuration")


STRICTER_KEYS = ("alpha", "min_cases", "require_stage", "require_significance", "best_guess_switch")


def policy_for(config: Config, solution_id: str, component: str = "", per_case: Optional[List[Row]] = None) -> Policy:
    """The solution's policy from ``[switching]`` (the project) and ``[switching.<solution id>]`` (the solution, which overrides the
    project) in the configuration. Only stricter requirements count: an ``alpha`` above 0.05 is read as 0.05 and a negative
    ``min_cases`` as none. ``best_guess_switch = false`` is a deprecated alias of ``require_significance = true``; ``true`` changes
    nothing. ``component`` and ``per_case`` are accepted for older callers and unused."""
    table = getattr(config, "switching", {}) or {}
    project = {k: v for k, v in table.items() if k in STRICTER_KEYS}
    solution = table.get(solution_id, {}) if isinstance(table.get(solution_id), dict) else {}
    chosen, origin = {}, []
    for level, found in (("project", project), ("solution", solution)):
        for key, value in found.items():
            if key == "best_guess_switch":
                key, value = "require_significance", not bool(value)
            if key in STRICTER_KEYS:
                chosen[key] = value
                origin.append((key, level))
    return Policy(alpha=min(float(chosen.get("alpha", ALPHA)), ALPHA), min_cases=max(int(chosen.get("min_cases", 0)), 0),
                  require_stage=str(chosen.get("require_stage", "")),
                  require_significance=bool(chosen.get("require_significance", False)), origin=tuple(origin),
                  holdout=holdout_fraction(config))


def holdout_fraction(config: Config) -> float:
    """``[selection] holdout`` as a fraction between 0 and 1 (0, the default, keeps no case out: every claim is on the cases the choice used)."""
    table = getattr(config, "selection", None)
    try:
        value = float(table.get("holdout", 0)) if isinstance(table, dict) else 0.0
    except (TypeError, ValueError):
        return 0.0
    return value if 0 < value < 1 else 0.0


def part_of(row: Row) -> str:
    """``"selection"`` or ``"heldout"`` for a row made by ``part_row``, else ``""`` (the whole case set)."""
    return (row.get("part") or "").strip()


def part_row(per_case: Optional[List[Row]], row: Row, fraction: float, heldout: bool) -> Optional[Row]:
    """A copy of a results row restricted to the selection part or the held-out part of its cases (``stats.in_heldout``), with the
    case count and pass count of that part, or ``None`` when the per-case log does not hold exactly that run. Cost and calls stay
    those of the whole run; the row is marked with ``part`` so the tests read only that part."""
    found = case_outcomes(per_case, row)
    if found is None:
        return None
    mine = {c: ok for c, ok in found.items() if stats.in_heldout(c, fraction) == heldout}
    out = dict(row)
    out.update({"cases": str(len(mine)), "passed": str(sum(mine.values())), "part": "heldout" if heldout else "selection",
                "split": f"{fraction:g}", "balanced": "", "balanced_all": row.get("balanced", ""), "cases_all": row.get("cases", ""), "passed_all": row.get("passed", "")})
    return out


def whole_row(row: Row) -> Row:
    """The results row a ``part_row`` was made from (its whole case set again)."""
    if not part_of(row):
        return row
    out = {k: v for k, v in row.items() if k not in ("part", "split", "cases_all", "passed_all", "balanced_all")}
    out.update({"cases": row.get("cases_all", ""), "passed": row.get("passed_all", ""), "balanced": row.get("balanced_all", "")})
    return out


def selection_view(history: Dict[str, List[Row]], per_case: Optional[List[Row]], policy: Policy) -> Tuple[Dict[str, List[Row]], Policy]:
    """``(history, policy)`` to choose a leader with: with a holdout, every run restricted to the selection part of its cases (a run the
    per-case log cannot split is left out) and the policy without the holdout, since the choice is made on that part; without one, the
    history and policy as given."""
    if not policy.holdout:
        return history, policy
    part = {impl: [p for r in rs if (p := part_row(per_case, r, policy.holdout, False)) is not None] for impl, rs in history.items()}
    return {impl: rs for impl, rs in part.items() if rs}, Policy(policy.alpha, policy.min_cases, policy.require_stage,
                                                                  policy.require_significance, policy.origin, 0.0)


def selection_leader(rows: Rows, per_case: Optional[List[Row]], fraction: float, selected: str, eval_dir: Optional[Path] = None) -> Optional[str]:
    """The arm with the highest result on the selection part of the cases the selected arm was scored on (the standing rule applied to
    that part: an exact tie keeps ``selected``), or ``None`` when the selected arm has no per-case rows to split."""
    parts = {impl: part_row(per_case, r, fraction, False) for impl, r in rows.items() if not is_partial(r) and not is_ablation(r, eval_dir)}
    parts = {impl: p for impl, p in parts.items() if p is not None}
    own = parts.get(selected)
    if own is None:
        return None
    same = {impl: p for impl, p in parts.items() if comparable(p, own)}
    best = max(estimate(p) for p in same.values())
    top = {impl: p for impl, p in same.items() if estimate(p) == best}
    return selected if selected in top else rank(top)[0]["impl"]


def looks_between(history: Optional[Dict[str, List[Row]]], first: str, second: str, cases_sha: str) -> int:
    """How many looks two arms had at the same case file: the distinct samples (3, 10, 30 cases, the full set) both have a run of.
    A claim at one of several looks spends a share of alpha (Bonferroni over looks)."""
    if not history:
        return 1
    def samples(impl: str) -> set:
        return {(r.get("sample") or "").strip() for r in history.get(impl, []) if r.get("cases_sha") == cases_sha and not is_partial(r)}
    return max(1, len(samples(first) & samples(second)))


def policies(config: Config, registry: Registry, per_case: Optional[List[Row]]) -> Dict[str, Policy]:
    """``{component: Policy}`` for every evaluated solution."""
    out: Dict[str, Policy] = {}
    for row in registry.solutions:
        component, _ = first_arm(config, row.get("metric_command", ""))
        if component:
            out.setdefault(component, policy_for(config, row["solution_id"], component, per_case))
    return out


def case_outcomes(per_case: Optional[List[Row]], row: Row) -> Optional[Dict[str, bool]]:
    """``{case id: passed}`` of the run a results row summarises, or ``None`` when the per-case log does not hold exactly that
    run (no rows, another count, or another pass total: the log keeps the newest run of a sample, the row may be older)."""
    if not per_case or unverified(row):
        return None
    sample = (row.get("sample") or "").strip()
    found = {r["case_id"]: stats.passed(r.get("ok")) for r in per_case
             if r.get("component") == row.get("component") and r.get("impl") == row.get("impl")
             and r.get("cases_sha") == row.get("cases_sha") and (r.get("sample") or "").strip() == sample}
    if part_of(row):   # a part of the run: the cases of that part must be all the row counts
        found = {c: ok for c, ok in found.items() if stats.in_heldout(c, float(row.get("split") or 0)) == (part_of(row) == "heldout")}
    try:
        total, passed = int(float(row.get("cases") or 0)), int(float(row.get("passed") or 0))
    except ValueError:
        return None
    return found if found and len(found) == total and sum(found.values()) == passed else None


def case_numbers(per_case: Optional[List[Row]], row: Row) -> Optional[Dict[str, float]]:
    """``{case id: balanced score of that case}`` for a run whose authoritative metric is the balanced score, or ``None`` when the
    per-case log holds no complete set of scores for exactly that run."""
    if case_outcomes(per_case, row) is None:
        return None
    sample = (row.get("sample") or "").strip()
    found: Dict[str, float] = {}
    for r in per_case or []:
        if (r.get("component"), r.get("impl"), r.get("cases_sha"), (r.get("sample") or "").strip()) == \
                (row.get("component"), row.get("impl"), row.get("cases_sha"), sample):
            if part_of(row) and stats.in_heldout(r["case_id"], float(row.get("split") or 0)) != (part_of(row) == "heldout"):
                continue
            try:
                found[r["case_id"]] = float(r.get("score") or "")
            except ValueError:
                return None
    return found


def passes(row: Row) -> int:
    try:
        return int(float(row.get("passed") or 0))
    except ValueError:
        return 0


def cost_per_passing(row: Row) -> Optional[Tuple[str, float]]:
    """``(unit, amount)`` per passing case, shown beside a result: dollars when the cost is recorded, else model calls; ``None``
    with no passing case. It informs a reader; it decides nothing (cost and speed count only inside the authoritative metric)."""
    if passes(row) <= 0:
        return None
    if cost_known(row):
        return "usd", float(row["cost_usd"]) / passes(row)
    calls = float(row.get("model_calls") or 0)
    return ("calls", calls / passes(row)) if calls > 0 else None


def estimate(row: Row) -> Fraction:
    """The point estimate on the authoritative metric: the balanced score when the run has one, else the pass rate."""
    return Fraction(pass_rate(row)).limit_denominator(10000)


def uses_balanced(own: Row, other: Row) -> bool:
    return bool(str(own.get("balanced") or "").strip() and str(other.get("balanced") or "").strip())


def best_guess(rows: Rows, eval_dir: Optional[Path] = None) -> Tuple[Optional[str], str]:
    """``(arm, why)``: the arm with the best point estimate among arms scored on the same cases as the largest run, labelled a best
    guess because no test was possible. Exactly equal leaders are a tie: ``(None, why)``, and nothing is selected."""
    live = {i: r for i, r in rows.items() if not is_partial(r) and not is_ablation(r, eval_dir)}
    if not live:
        return None, "no arm has a result"
    reference = max(live.values(), key=lambda r: (int(float(r.get("cases") or 0)), r.get("date") or "", r["impl"]))
    ranked = rank({i: r for i, r in live.items() if comparable(r, reference)})
    top = [r for r in ranked if estimate(r) == estimate(ranked[0])]
    shown = ", ".join(f"{r['impl']} {pass_rate(r):.3g}" for r in ranked)
    if len(top) > 1:
        return None, f"best guess: a tie on the point estimate ({shown}); nothing is selected"
    return ranked[0]["impl"], f"best guess on the point estimate ({shown}); no test was possible"


@dataclass
class Decision:
    """How one rival stands against the selected arm. ``outcome``: ``rival`` (higher on the metric), ``incumbent`` (the selected
    arm is higher) or ``tie`` (exactly equal, or the policy requires significance and there is none; the selected arm stays).
    ``basis`` is ``significance`` (a two-sided exact test on shared cases was possible) or ``best guess`` (point estimates only).
    ``significant`` says whether the test passed. ``switch`` says whether a ``rival`` outcome replaces the selected arm."""
    rival: str
    outcome: str
    basis: str
    text: str
    own: Row
    other: Row
    p: Optional[float] = None          # Holm-adjusted two-sided p of the pair
    disagree: int = 0                  # cases where the two differ
    shared: int = 0
    switch: bool = False
    significant: bool = False          # the lead (or deficit) passed the two-sided test at the policy's alpha
    p_incumbent: Optional[float] = None   # the same two-sided p, read from the selected arm's side

    @property
    def rule(self) -> str:
        if self.basis != "significance":
            return "best guess"
        return "two-sided exact Fisher test" if "Fisher" in self.text else "two-sided paired test"


def disagreements(per_case: Optional[List[Row]], own: Row, rival: Row) -> Optional[Tuple[int, int, int, str]]:
    """``(cases the rival is ahead on, cases the selected arm is ahead on, shared cases, test name)`` from per-case rows of exactly
    these two runs, or ``None``. Pass or fail per case uses McNemar's exact test; a balanced-score metric compares the scores of
    each case with the exact sign test (cases with equal scores are left out)."""
    if uses_balanced(own, rival):
        a, b = case_numbers(per_case, own), case_numbers(per_case, rival)
        if a is None or b is None or a.keys() != b.keys():
            return None
        return (sum(round(b[c] - a[c], 9) > 0 for c in a), sum(round(b[c] - a[c], 9) < 0 for c in a), len(a), "exact sign test on per-case balanced scores")
    a, b = case_outcomes(per_case, own), case_outcomes(per_case, rival)
    if a is None or b is None or a.keys() != b.keys():
        return None
    return (sum(b[c] and not a[c] for c in a), sum(a[c] and not b[c] for c in a), len(a), "exact McNemar test")


def aggregate_counts(own: Row, rival: Row) -> Optional[Tuple[int, int, int, int]]:
    """``(rival passed, rival cases, selected passed, selected cases)`` when both rows are verified runs of the same cases and sample
    with pass counts and the metric is the pass rate: enough for an unpaired exact test when no per-case rows exist."""
    if unverified(own) or unverified(rival) or uses_balanced(own, rival) or str(own.get("balanced") or rival.get("balanced") or "").strip():
        return None
    try:
        counts = (int(float(rival["passed"])), int(float(rival["cases"])), int(float(own["passed"])), int(float(own["cases"])))
    except (KeyError, ValueError):
        return None
    return counts if counts[1] > 0 and counts[3] > 0 and 0 <= counts[0] <= counts[1] and 0 <= counts[2] <= counts[3] else None


def decisions(rows: Rows, selected: str, eval_dir: Optional[Path] = None, history: Optional[Dict[str, List[Row]]] = None,
              per_case: Optional[List[Row]] = None, policy: Optional[Policy] = None) -> List[Decision]:
    """One ``Decision`` per rival scored on the same cases as ``selected``, on the solution's authoritative metric.

    The test is two-sided and exact (the direction is read from the data, so it is not tested one-sided) and says whether a lead is significant: its Holm-adjusted p-value (across the rivals) is below
    ``policy.alpha`` (default 0.05). With per-case rows for both arms the test is paired (McNemar for pass or fail per case, a
    sign test on per-case balanced scores). With only aggregate pass counts on the same cases and sample it is Fisher's exact test on
    the 2 by 2 table of passed and failed cases. Otherwise (a balanced aggregate, a figure with no case count) the point estimates are
    compared and labelled a best guess. A higher rival replaces the selected arm by default, its text saying whether the lead is
    significant or "best guess, not yet significant"; with ``policy.require_significance`` only a significant lead replaces it.
    Exactly equal estimates keep the selected arm."""
    policy = policy or Policy()
    pairs = rival_pairs(rows, selected, eval_dir, history)[0]
    if policy.holdout:   # claims rest on the held-out part alone; a pair with no per-case rows has no held-out part and is a best guess on its whole set
        pairs = [(a, b) for own, rival in pairs
                 for a, b in [(part_row(per_case, own, policy.holdout, True), part_row(per_case, rival, policy.holdout, True))]
                 for a, b in [((a, b) if a is not None and b is not None else (own, rival))]]
    tested = []   # (own, rival, p rival better, p selected better, cases that differ, shared, test name, how the evidence reads)
    for own, rival in pairs:
        name = rival["impl"]
        found = disagreements(per_case, own, rival) if not policy.holdout or part_of(own) else None
        if found is not None:
            ahead, behind, shared, test = found
            two = stats.mcnemar_exact(ahead, behind)   # two-sided: a direction picked from the data is not tested one-sided
            tested.append((own, rival, two, two, ahead + behind, shared, test.replace("exact", "two-sided exact"),
                           f"{ahead + behind} of {shared} cases disagree"))
            continue
        agg = aggregate_counts(own, rival) if not policy.holdout else None
        if agg is not None:
            xr, nr, xo, no = agg
            two = stats.fisher_exact_two_sided(xr, nr, xo, no)
            tested.append((own, rival, two, two, 0, min(nr, no),
                           "two-sided exact Fisher test on the pass counts (no per-case rows)", f"{name} passed {xr} of {nr}, {selected} {xo} of {no}"))
        else:
            tested.append((own, rival, None, None, 0, 0, "", ""))
    better = iter(stats.holm([t[2] for t in tested if t[2] is not None]))
    worse = iter(stats.holm([t[3] for t in tested if t[3] is not None]))
    looked = {}
    out: List[Decision] = []
    for own, rival, raw, _, differ, shared, test, counted in tested:
        name = rival["impl"]
        mine, theirs = estimate(own), estimate(rival)
        figures = f"{name} {pass_rate(rival):.3g} against {selected} {pass_rate(own):.3g}"
        if raw is None:   # no test is possible: the point estimates decide, labelled a best guess
            note = f"best guess, not yet significant: {figures} on the point estimate; no case counts or per-case rows allow a test"
            if theirs > mine:
                if policy.require_significance:
                    out.append(Decision(name, "rival", "best guess", note + f"; the {policy.source('require_significance')} requires significance, so {selected} stays", own, rival))
                else:
                    out.append(Decision(name, "rival", "best guess", note, own, rival, switch=True))
            elif mine > theirs:
                out.append(Decision(name, "incumbent", "best guess", note, own, rival))
            else:
                out.append(Decision(name, "tie", "best guess", note + f"; exactly equal, so {selected} stays", own, rival))
            continue
        p, q = next(better), next(worse)
        looks = looks_between(history, selected, name, own.get("cases_sha", ""))
        alpha = stats.bonferroni_alpha(policy.alpha, looks)
        if looks > 1:
            counted += f"; one of {looks} looks, alpha {alpha:.3g}"
        args = (own, rival, p, differ, shared)
        mark = len(out)
        enough = shared >= policy.min_cases
        if theirs > mine and p < alpha and enough:
            out.append(Decision(name, "rival", "significance", f"{name} is better than {selected} ({test}, Holm-adjusted p={p:.3g}, {counted})",
                                *args, switch=True, significant=True))
        elif theirs > mine:
            lead = f"{name} leads {selected} ({figures}; {test}, Holm-adjusted p={p:.3g}, {counted})"
            if not policy.require_significance:
                why = f"; {policy.source('min_cases')} asks for {policy.min_cases} shared cases and there are {shared}" if not enough else ""
                out.append(Decision(name, "rival", "significance", f"best guess, not yet significant: {lead}; more cases would settle it{why}",
                                    *args, switch=True))
            else:
                if not enough:
                    reason = f"the {policy.source('min_cases')} requires at least {policy.min_cases} shared cases and there are {shared}"
                elif p < ALPHA:
                    reason = f"it is significant at alpha {ALPHA:g} but the {policy.source('alpha')} requires alpha {policy.alpha:g}"
                else:
                    reason = f"the {policy.source('require_significance')} requires a significant lead"
                out.append(Decision(name, "tie", "significance", f"{name} is not shown better than {selected} (p={p:.3g}, {counted}); more cases "
                                    f"would settle it: {reason}, so {selected} stays", *args))
        elif q < alpha:
            out.append(Decision(name, "incumbent", "significance", f"{selected} is better than {name} ({test}, Holm-adjusted p={q:.3g}, {counted})",
                                *args, significant=True))
        elif mine > theirs:
            out.append(Decision(name, "incumbent", "significance", f"{selected} leads {name} ({figures}; best guess, not yet significant, {test}, "
                                f"Holm-adjusted p={q:.3g}, {counted})", *args))
        else:
            out.append(Decision(name, "tie", "significance", f"{name} is exactly equal to {selected} on the metric ({figures}), so {selected} stays", *args))
        out[mark].p_incumbent = q
    return out


def challengers(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
                history: Optional[Dict[str, List[Row]]] = None, per_case: Optional[List[Row]] = None,
                policy: Optional[Policy] = None) -> List[Row]:
    """Rival rows that should replace the selected arm (see ``decisions``). A rival on other cases is skipped, and an ablation or
    validity arm is never a challenger."""
    return [d.other for d in decisions(rows, selected, eval_dir, history, per_case, policy) if d.outcome == "rival" and d.switch]


def verdict(rows: Rows, selected: str, eval_dir: Optional[Path] = None,
            history: Optional[Dict[str, List[Row]]] = None, per_case: Optional[List[Row]] = None,
            policy: Optional[Policy] = None) -> Tuple[str, str]:
    """How the selected implementation stands against the other measured ones, as ``(label, detail)``. LOSS: a rival should replace
    it. WIN: it is shown, or guessed, better than every rival. TIE: no rival is shown better, so it stays. The detail says which
    basis decided each rival: a significance test or a best guess."""
    if rows.get(selected) is None:
        guess, why = best_guess(rows, eval_dir)
        return "UNMEASURED", "the selected implementation has no recorded row" + (f"; {why}" if len(rows) else "")
    pairs, unmatched = rival_pairs(rows, selected, eval_dir, history)
    if not pairs:
        if unmatched:
            return "UNMEASURED", ("no rival was measured on the same cases and sample as the selected "
                                  f"implementation: {'; '.join(f'{i} {why}' for i, why in unmatched)}")
        return "UNMEASURED", "no rival implementation was measured on the same cases"
    found = decisions(rows, selected, eval_dir, history, per_case, policy)
    text = "; ".join(d.text for d in sorted(found, key=lambda d: d.rival))
    if any(d.outcome == "rival" and d.switch for d in found):
        return "LOSS", "beaten by " + ", ".join(sorted(d.rival for d in found if d.outcome == "rival" and d.switch)) + ": " + text
    if all(d.outcome == "incumbent" for d in found):
        return "WIN", text
    return "TIE", text


def solution_verdicts(config: Config, solutions: List[Row], results: Optional[Dict[str, Rows]] = None,
                      history: Optional[Dict[str, Dict[str, List[Row]]]] = None, registry: Optional[Registry] = None,
                      per_case: Optional[List[Row]] = None) -> Dict[str, Dict[str, str]]:
    """{solution_id: {"verdict", "detail", "component", "selected_by"}} for every solution, judged on the
    first harness arm of its ``metric_command`` (the primary metric; later arms are listed on the board)."""
    if results is None:
        history = all_results(config.results_path)
        results = {comp: {impl: rows[-1] for impl, rows in impls.items()} for comp, impls in history.items()}
    per_case = per_case_rows(config) if per_case is None else per_case
    out = {}
    for row in solutions:
        comp, impl = selected_arm(config, row, "", registry)
        if not comp:
            out[row["solution_id"]] = dict(verdict="UNMEASURED", detail="no harness metric", component="",
                                           selected_by=row.get("selected_by", ""))
            continue
        label, detail = verdict(results.get(comp, {}), impl, config.evaluation, (history or {}).get(comp), per_case,
                                policy_for(config, row["solution_id"], comp, per_case))
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


def unmeasured_candidates(registry: Registry, history: Dict[str, Dict[str, List[Row]]]) -> List[str]:
    """What the leaderboard would otherwise leave out: implementations recorded with no code (an empty ``filepath``, no sub-intent
    that holds their specification) and no result of any component. Each is a rival nobody could run yet, named with its solution."""
    measured = {impl for impls in history.values() for impl in impls}
    found = []
    for row in registry.implementations:
        impl_id = row.get("implementation_id", "")
        short = impl_id.split(":", 1)[-1]
        if (row.get("filepath") or "").strip() or (row.get("sub_intent") or "").strip() or short in measured or impl_id in measured:
            continue
        found.append(f"  NOT MEASURED  {row.get('solution_id', '')}: {row.get('name') or short} ({impl_id}) has no arm yet, so no result")
    return (["\nCandidates with no arm yet (recorded, so they are not forgotten; `esoi admit` registers one, declaring its code and "
             "`esoi records sync` make it an arm)"] + found) if found else []


def board(config: Config, registry: Registry, strict: bool = False, say: Callable[[str], None] = print,
          stale: Optional[Callable[[Config, str, Row, bool], str]] = None,
          attested: Optional[Callable[[Config, str, str, str], str]] = None) -> int:
    """Print the leaderboard. ``attested`` (``attest.note``) says, for a row, ``current by attestation (reason)`` or ''. Returns 1 when ``strict`` and a challenger beats a selected implementation, or a verdict
    rests on a rival recorded before the measured code changed (``stale`` is ``harness.stale_reason``; without it
    only the cases are compared)."""
    history = all_results(config.results_path)
    results = {comp: {impl: rows[-1] for impl, rows in impls.items()} for comp, impls in history.items()}
    selected = selected_impls(config, registry.solutions, registry)
    per_case = per_case_rows(config)
    chosen = policies(config, registry, per_case)
    flagged = 0
    apart = {c: rows for c, rows in results.items() if invariant_reason(c, config.evaluation)}
    for component, rows in sorted(results.items()):
        if component in apart:
            continue
        sel = selected.get(component)
        label, detail = verdict(rows, sel, config.evaluation, history[component], per_case, chosen.get(component)) if sel else ("UNMEASURED", "no selected implementation: " + best_guess(rows, config.evaluation)[1])
        say(f"{component} (selected: {sel or 'none recorded'}) {label}: {detail}")
        for line in format_rows(rows, sel, config.evaluation):
            say(line)
        if stale and attested:
            for impl, r in sorted(rows.items()):
                if (said := attested(config, component, impl, r.get("git_sha", ""))) and not stale(config, component, r, True):
                    say(f"  = {impl}: {said}")
        for own, rival in (rival_pairs(rows, sel, config.evaluation, history[component])[0] if sel else []):
            if own is not rows.get(sel) or rival is not rows.get(rival["impl"]):
                say(f"  = compared on {describe_cases(own)}: {sel} {own['passed']}/{own['cases']} ({own.get('date', '')}) "
                    f"against {rival['impl']} {rival['passed']}/{rival['cases']} ({rival.get('date', '')})")
        for impl, why in (incomparable_rivals(rows, sel, config.evaluation, history[component]) if sel else []):
            flagged += 1 if strict else 0
            say(f"  ? {impl} is not comparable with {sel}: {why}; re-run both on the same sample "
                "(`esoi run --stale` re-runs a rival on the selected arm's sample)")
        for r in (challengers(rows, sel, config.evaluation, history[component], per_case, chosen.get(component)) if sel else []):
            flagged += 1
            say(f"  ! {r['impl']} should replace the selected {sel}: decide whether to adopt it "
                "(update the solution's `selected` and the live default together)")
        for impl, why in (stale_rivals(config, component, rows, sel, stale, history[component]) if sel and stale else []):
            flagged += 1 if strict else 0
            say(f"  ~ {impl} is a rival the verdict on {sel} rests on, but {why}; re-run it on the current code "
                "before trusting the verdict")
    say("\nBy solution (WIN = shown, or guessed, better than every rival; TIE = no rival is shown better, so it stays; "
        "UNMEASURED = no rival was compared; a rival that should replace the selected arm is flagged with `!` above)")
    for sid, v in sorted(solution_verdicts(config, registry.solutions, results, history, registry, per_case).items()):
        reason = f"  kept because: {v['selected_by']}" if v["verdict"] == "TIE" else ""
        say(f"  {v['verdict']:<10} {sid}: {v['detail']}{reason}")
    for line in unmeasured_candidates(registry, history):
        say(line)
    if apart:
        say("\nComplementary arms (not alternatives; listed with their recorded run, never ranked)")
        for component, rows in sorted(apart.items()):
            say(f"{component}: {invariant_reason(component, config.evaluation)}")
            for line in format_rows(rows, selected.get(component), config.evaluation):
                say(line)
    return 1 if flagged and strict else 0
