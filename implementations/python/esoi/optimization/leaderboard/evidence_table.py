"""One Markdown table of every evaluated solution's arms, with the evidence and the rule behind each verdict.

``esoi evidence-table`` (or ``evidence_table`` here) lists, for every evaluated solution, every arm that has a recorded run: the
cases it was scored on, its pass rate with the 95% Wilson interval, its cost per passing case, its seconds per case, and its
standing against the selected arm with the rule that decided it and the p-value (``esoi.optimization.leaderboard.rival_decisions.decisions``). The last
column shows what others measured for the arm (``esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading``), graded and labelled public: it is shown beside our numbers and
never mixed into them. A project with no per-case rows still gets a row for each arm, with the margin rule named as the rule.

With ``--file`` the table is written between two marker lines in that file, so a README can embed it and refresh it by running the
command again. The default markers are ``BEGIN`` and ``END`` below; a project may choose its own. Nothing here calls a model or the
network.
"""
from __future__ import annotations

import datetime
import re
import statistics
from pathlib import Path
from typing import Callable, Dict, List, Optional

from esoi.optimization.when_metrics_are_run.public_evidence import evidence_grading, evidence_records
from esoi.optimization.leaderboard import stats, arm_kinds, arm_selection, held_out_parts, ranking, results_log, rival_decisions, rival_pairing, switching_policy
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import Registry
from esoi.runtime.implementation_selection.variants import base_of

BEGIN = "<!-- esoi:evidence-table:begin -->"
END = "<!-- esoi:evidence-table:end -->"
HEADER = ["Solution", "Arm", "Cases", "Pass rate (95% Wilson)", "Cost per passing case", "Seconds per case",
          "Versus the selected arm (rule, p-value)", "Public evidence (not in our numbers)"]
Row = Dict[str, str]


def cell(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).replace("|", "/").strip()


def cost_label(row: Row) -> str:
    if ranking.passes(row) <= 0:
        return "no passing case"
    per = ranking.cost_per_passing(row)
    if per is None:
        return "unknown (no price recorded)"
    return f"${per[1]:.4g}" if per[0] == "usd" else f"{per[1]:.3g} model calls (no price)"


def seconds_mean(row: Row) -> str:
    try:
        seconds, cases = float(row.get("seconds") or ""), int(float(row.get("cases") or 0))
    except ValueError:
        return "not recorded"
    return f"{seconds / cases:.3g} (mean)" if cases else "not recorded"


def seconds_label(row: Row, per_case: Optional[List[Row]]) -> str:
    """Median seconds per case when the per-case log holds exactly this run, else the total over the cases, labelled mean."""
    if held_out_parts.case_outcomes(per_case, row) is None:
        return seconds_mean(row)
    sample = (row.get("sample") or "").strip()
    times = []
    for r in per_case or []:
        if (r.get("component"), r.get("impl"), r.get("cases_sha"), (r.get("sample") or "").strip()) == \
                (row.get("component"), row.get("impl"), row.get("cases_sha"), sample):
            try:
                times.append(float(r.get("seconds") or ""))
            except ValueError:
                return seconds_mean(row)
    return f"{statistics.median(times):.3g} (median)" if times else seconds_mean(row)


def rate_label(row: Row) -> str:
    passed, cases = ranking.passes(row), int(float(row.get("cases") or 0))
    if not cases:
        return "no cases"
    low, high = stats.wilson_interval(passed, cases)
    return f"{passed / cases:.1%} ({low:.1%} to {high:.1%}), {passed}/{cases}"


def verdict_label(d: "rival_decisions.Decision") -> str:
    tested = d.basis == "significance"
    standing = {"rival": "better than the selected arm", "incumbent": "behind the selected arm", "tie": "not shown better than the selected arm"}[d.outcome] \
        if tested else {"rival": "ahead of the selected arm", "incumbent": "behind the selected arm", "tie": "equal to the selected arm"}[d.outcome]
    if d.outcome == "rival" and d.switch and d.significant:
        standing = "beats the selected arm"
    elif d.outcome == "rival" and d.switch:
        standing = "leads the selected arm (best guess, not yet significant)"
    if not tested:
        number = "point estimates only, no per-case rows for both arms"
    else:
        number = f"Holm-adjusted p = {d.p:.3g}" + ("" if "Fisher" in d.text else f", {d.disagree} of {d.shared} cases disagree")
    return f"{standing}: {d.rule}, {number}"


def public_label(config: Config, registry: Registry, graded: Dict, solution_id: str, impl: str) -> str:
    keys = evidence_records.implementation_candidates(config, registry, solution_id).get(base_of(impl), "")
    found = evidence_grading.lines_for_implementation(graded, keys) if keys else []
    return "; ".join(f"public, grade {e.grade}: {e.line()}" for e in found) or "none recorded"


def table_rows(config: Config, registry: Registry, today: Optional[datetime.date] = None, solution: str = "") -> List[List[str]]:
    history = results_log.all_results(config.results_path)
    per_case = results_log.per_case_rows(config)
    chosen = switching_policy.policies(config, registry, per_case)
    note = ""
    try:
        graded = evidence_grading.estimates(evidence_records.load_for(config), today)
    except evidence_records.EvidenceError as exc:
        graded, note = {}, f" (public evidence file cannot be read: {exc})"
    out: List[List[str]] = []
    impl_names = {r.get("implementation_id", ""): " ".join((r.get("name") or "").split()) for r in registry.implementations}
    for sol in registry.solutions:
        sid = sol["solution_id"]
        component, selected = arm_selection.selected_arm(config, sol, "", registry)
        if not component or (solution and sid != solution) or component not in history:
            continue
        arms = {impl: [r for r in found if not results_log.is_partial(r)] for impl, found in history[component].items()}
        arms = {impl: found for impl, found in arms.items() if found}
        rows = {impl: found[-1] for impl, found in arms.items()}
        apart = bool(arm_kinds.invariant_reason(component, config.evaluation))
        ranked = selected in rows and not apart
        found = {d.rival: d for d in rival_decisions.decisions(rows, selected, config.evaluation, history[component], per_case,
                                                            chosen.get(component))} if ranked else {}
        pairs = {r["impl"]: (own, r) for own, r in rival_pairing.rival_pairs(rows, selected, config.evaluation, history[component])[0]} \
            if ranked else {}
        for impl in sorted(arms, key=lambda i: (i != selected, i)):
            if impl in pairs:
                row = pairs[impl][1]   # the run scored on the selected arm's cases
            elif impl == selected and pairs:
                row = next(iter(pairs.values()))[0]
            else:
                row = rows[impl]
            if apart:
                standing = "complementary arm, not ranked"
            elif impl == selected:
                standing = "selected"
            elif impl in found:
                standing = verdict_label(found[impl])
            elif arm_kinds.is_ablation(rows[impl], config.evaluation):
                standing = "reference arm (ablation or validity), not a rival"
            else:
                standing = "not compared: no run on the same cases and sample as the selected arm"
            arm = impl_names.get(f"{sid}:{impl}", "")
            out.append([f"{sol.get('name') or sid} (`{sid}`)" if (sol.get("name") or "").strip().lower() != sid else f"`{sid}`",
                        (f"{arm} (`{impl}`)" if arm and arm.lower() != impl.lower() else f"`{impl}`") + (" (selected)" if impl == selected else ""), str(row.get("cases", "")), rate_label(row),
                        cost_label(row), seconds_label(row, per_case), standing,
                        public_label(config, registry, graded, sid, impl) + note])
    return out


def evidence_table(config: Config, registry: Registry, today: Optional[datetime.date] = None, solution: str = "") -> str:
    """The Markdown table, or a one-line note when nothing has been recorded."""
    rows = table_rows(config, registry, today, solution)
    if not rows:
        return "No evaluated solution has a recorded run yet."
    lines = ["| " + " | ".join(HEADER) + " |", "|" + "---|" * len(HEADER)]
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    lines.append("")
    lines.append("Pass rates carry the 95% Wilson interval. A verdict compares an arm with the selected arm on identical cases: it "
                 "leads only when a one-sided exact paired test (McNemar for pass or fail per case, a sign test on per-case scores, Holm-adjusted across rivals) gives p below "
                 "0.05; otherwise the selected arm stays. Without per-case rows, pass counts get Fisher's exact test; a figure with no case counts is compared on point estimates and labelled a best guess. "
                 "The width of the interval shows how little a small sample says. Public evidence is what others measured, graded, and is never added "
                 "to these numbers.")
    return "\n".join(lines)


def write_between(path: Path, begin: str, end: str, block: str) -> None:
    """Replace what lies between the marker lines ``begin`` and ``end`` in ``path`` with ``block``; raise ``ValueError`` when a
    marker is missing, so a file is never changed anywhere else."""
    text = Path(path).read_text(encoding="utf-8")
    start = text.find(begin)
    stop = text.find(end, start + len(begin)) if start >= 0 else -1
    if start < 0 or stop < 0:
        raise ValueError(f"{path} needs the two marker lines {begin!r} and then {end!r}")
    Path(path).write_text(text[:start + len(begin)] + "\n" + block.strip("\n") + "\n" + text[stop:], encoding="utf-8")


def run_cli(config: Config, file: str = "", begin: str = BEGIN, end: str = END, solution: str = "",
            say: Callable[[str], None] = print) -> int:
    """``esoi evidence-table [--file PATH]``: print the table, or write it between the markers of ``PATH``."""
    from esoi.structure.intent_registry import registry as registry_module
    block = evidence_table(config, registry_module.load(config), solution=solution)
    if not file:
        say(block)
        return 0
    target = Path(file) if Path(file).is_absolute() else config.root / file
    try:
        write_between(target, begin, end, block)
    except (OSError, ValueError) as exc:
        say(f"esoi: {exc}")
        return 1
    say(f"wrote the evidence table into {file}")
    return 0
