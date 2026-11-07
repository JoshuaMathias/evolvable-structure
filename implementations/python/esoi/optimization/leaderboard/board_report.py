"""``esoi leaderboard [--strict]``: print the ranking per component, the verdict per solution and every challenger that should replace a selected implementation.

The leaderboard only ranks; switching the live implementation stays a deliberate decision. Only rows scored on the same cases are
compared (same ``cases_sha``, ``sample`` and case count); a rival that shares none is UNMEASURED or "not comparable". Rows with no
``cases_sha`` are flagged ``unverified``. Only whole-run rows decide the default verdict; ``only:`` and ``slice:`` rows are partial.
A component with an ``invariant.txt`` is listed apart, with its recorded run, and never ranked."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import Registry
from esoi.optimization.leaderboard.arm_kinds import arm_kind, invariant_reason
from esoi.optimization.leaderboard.arm_selection import selected_impls
from esoi.optimization.leaderboard.case_identity import describe_cases, unverified
from esoi.optimization.leaderboard.ranking import cost_known, rank, tokens_label
from esoi.optimization.leaderboard.results_log import Row, Rows, all_results, per_case_rows
from esoi.optimization.leaderboard.rival_decisions import best_guess, challengers
from esoi.optimization.leaderboard.rival_pairing import incomparable_rivals, rival_pairs, stale_rivals
from esoi.optimization.leaderboard.switching_policy import policies
from esoi.optimization.leaderboard.verdict_labels import solution_verdicts, verdict


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


def say_component(config: Config, component: str, rows: Dict[str, Row], sel: Optional[str], history: Dict[str, List[Row]], per_case: List[Row],
                  policy, strict: bool, say: Callable[[str], None], stale, attested) -> int:
    """Print one component's verdict, rows, comparisons and flags; returns how many flags count against a strict run."""
    flagged = 0
    label, detail = verdict(rows, sel, config.evaluation, history, per_case, policy) if sel else ("UNMEASURED", "no selected implementation: " + best_guess(rows, config.evaluation)[1])
    say(f"{component} (selected: {sel or 'none recorded'}) {label}: {detail}")
    for line in format_rows(rows, sel, config.evaluation):
        say(line)
    if stale and attested:
        for impl, r in sorted(rows.items()):
            if (said := attested(config, component, impl, r.get("git_sha", ""))) and not stale(config, component, r, True):
                say(f"  = {impl}: {said}")
    if not sel:
        return 0
    for own, rival in rival_pairs(rows, sel, config.evaluation, history)[0]:
        if own is not rows.get(sel) or rival is not rows.get(rival["impl"]):
            say(f"  = compared on {describe_cases(own)}: {sel} {own['passed']}/{own['cases']} ({own.get('date', '')}) "
                f"against {rival['impl']} {rival['passed']}/{rival['cases']} ({rival.get('date', '')})")
    for impl, why in incomparable_rivals(rows, sel, config.evaluation, history):
        flagged += 1 if strict else 0
        say(f"  ? {impl} is not comparable with {sel}: {why}; re-run both on the same sample "
            "(`esoi run --stale` re-runs a rival on the selected arm's sample)")
    for r in challengers(rows, sel, config.evaluation, history, per_case, policy):
        flagged += 1
        say(f"  ! {r['impl']} should replace the selected {sel}: decide whether to adopt it "
            "(update the solution's `selected` and the live default together)")
    for impl, why in (stale_rivals(config, component, rows, sel, stale, history) if stale else []):
        flagged += 1 if strict else 0
        say(f"  ~ {impl} is a rival the verdict on {sel} rests on, but {why}; re-run it on the current code "
            "before trusting the verdict")
    return flagged


def say_solutions(config: Config, registry: Registry, results: Dict, history: Dict, per_case: List[Row], say: Callable[[str], None]) -> None:
    """Print the verdict of each solution, by name and id."""
    say("\nBy solution, as Name (id); commands take the id (WIN = shown, or guessed, better than every rival; TIE = no rival is shown better, so it stays; "
        "UNMEASURED = no rival was compared; a rival that should replace the selected arm is flagged with `!` above)")
    called = {r.get("solution_id", ""): " ".join((r.get("name") or "").split()) for r in registry.every_solution()}
    for sid, v in sorted(solution_verdicts(config, registry.solutions, results, history, registry, per_case).items()):
        reason = f"  kept because: {v['selected_by']}" if v["verdict"] == "TIE" else ""
        title = f"{called[sid]} ({sid})" if called.get(sid) and called[sid].lower() != sid.lower() else sid
        say(f"  {v['verdict']:<10} {title}: {v['detail']}{reason}")


def board(config: Config, registry: Registry, strict: bool = False, say: Callable[[str], None] = print,
          stale: Optional[Callable[[Config, str, Row, bool], str]] = None,
          attested: Optional[Callable[[Config, str, str, str], str]] = None) -> int:
    """Print the leaderboard. ``attested`` (``attest.note``) says, for a row, ``current by attestation (reason)`` or ''. Returns 1 when ``strict`` and a challenger beats a selected implementation, or a verdict
    rests on a rival recorded before the measured code changed (``stale`` is ``stale_reasons.stale_reason``; without it
    only the cases are compared)."""
    history = all_results(config.results_path)
    results = {comp: {impl: rows[-1] for impl, rows in impls.items()} for comp, impls in history.items()}
    selected = selected_impls(config, registry.solutions, registry)
    per_case = per_case_rows(config)
    chosen = policies(config, registry, per_case)
    apart = {c: rows for c, rows in results.items() if invariant_reason(c, config.evaluation)}
    flagged = 0
    for component, rows in sorted(results.items()):
        if component not in apart:
            flagged += say_component(config, component, rows, selected.get(component), history[component], per_case, chosen.get(component),
                                     strict, say, stale, attested)
    say_solutions(config, registry, results, history, per_case, say)
    for line in unmeasured_candidates(registry, history):
        say(line)
    if apart:
        say("\nComplementary arms (not alternatives; listed with their recorded run, never ranked)")
        for component, rows in sorted(apart.items()):
            say(f"{component}: {invariant_reason(component, config.evaluation)}")
            for line in format_rows(rows, selected.get(component), config.evaluation):
                say(line)
    return 1 if flagged and strict else 0
