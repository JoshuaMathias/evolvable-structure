"""Three guards that stop ``esoi run`` from spending on a measurement that cannot inform a decision. No model call, no network.

**Ceiling.** When another arm of the same component already passed every case on the same cases and sample, an arm that may
spend money cannot beat it on accuracy, and is refused unless it can still win on what the metric weighs besides accuracy:

  * a metric with no ``[balance.<component>]`` is pass or fail (ties broken by cost), so the arm is skipped unless its recorded
    cost per case is known and lower than the perfect arm's;
  * a metric with a balance weighs cost and time too, so the arm is skipped only when its recorded cost per case and seconds
    per case are both known and neither is lower than the perfect arm's. An unknown cost or time is never read as a loss.

The perfect arm's row must itself be current (not stale), or it proves nothing about the code as it is now. An arm that cannot
spend money (not paid) is never guarded: running it is free.

**Public first.** A component may declare the public benchmark its cases reproduce, in ``evaluation/<component>/benchmark.txt``
(the first line that is not blank or a ``#`` comment) or ``[evidence.benchmarks] <component> = "name"`` in the configuration.
The name is matched, ignoring case, ``_``, ``-`` and spaces, against the ``comparator`` column of the project's evidence. When
an independent row exists for the arm's candidate (the implementation name or an ``[evidence.aliases]`` target) on that
benchmark, the number is already public, so a run is refused unless it says what differs from the public one.

**Unsolved failures.** While the arm's earlier cases that failed in a development run have not been rerun to a pass, a plain
unrecorded ``esoi run`` reruns just those cases (what ``--failed`` does), and a recorded run of every case is refused
(``unsolved_reason``): the failing cases are solved first.

All three are bypassed with ``--force REASON``, and the public one with ``--differs "harness: ..."`` (harness, prompt, settings,
corpus or metric). The reason is recorded in the row's ``details``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import evidence, leaderboard, run_log, variants
from .config import Config

Row = Dict[str, str]
DIFFERS = ("harness", "prompt", "settings", "corpus", "metric")
BENCHMARK_FILE = "benchmark.txt"


def per_case(row: Row, column: str) -> Optional[float]:
    """The recorded ``column`` of a row per case, or None when it is blank or unreadable (unknown, never zero)."""
    try:
        cases = float(row.get("cases") or 0)
        text = str(row.get(column) if row.get(column) is not None else "").strip()
        return float(text) / cases if text and cases > 0 else None
    except ValueError:
        return None


def perfect(row: Row) -> bool:
    try:
        cases = int(float(row.get("cases") or 0))
        return cases > 0 and int(float(row.get("passed") or 0)) == cases
    except ValueError:
        return False


def money(value: Optional[float]) -> str:
    return "unknown" if value is None else f"${value:.4f}/case"


def can_exceed(config: Config, component: str, rival: Optional[Row], best: Row) -> bool:
    """Whether an arm with the ``rival`` row could still beat the perfect arm ``best``: yes when the metric weighs cost or time
    and the rival is, or may be, cheaper or faster; for a pass or fail metric only when it is known to be cheaper."""
    rival_cost = per_case(rival, "cost_usd") if rival else None
    best_cost = per_case(best, "cost_usd")
    if not config.balance.get(component):
        return rival_cost is not None and best_cost is not None and rival_cost < best_cost
    rival_time = per_case(rival, "seconds") if rival else None
    best_time = per_case(best, "seconds")
    if None in (rival_cost, rival_time, best_cost, best_time):
        return True   # cannot prove the rival is no cheaper and no faster
    return rival_cost < best_cost or rival_time < best_time


def ceiling_reason(config: Config, component: str, impl: str, sample: str, paid: str,
                   stale: Callable[[Config, str, Optional[Row]], str]) -> str:
    """Why running ``impl`` on ``sample`` cannot inform a decision (an empty string when it can). ``paid`` is the harness's
    ``paid_reason`` for the arm: an arm that cannot spend money is never refused. ``stale`` is ``harness.stale_reason``."""
    if not paid:
        return ""
    history = leaderboard.all_results(config.results_path).get(component, {})
    now = leaderboard.cases_digest(component, config.evaluation)
    mine = history.get(impl, [])
    own = mine[-1] if mine else None
    for name, rows in sorted(history.items()):
        if variants.canonical(name) == impl:
            continue
        same = [r for r in rows if r.get("cases_sha") == now and (r.get("sample") or "").strip() == sample]
        if not same or not perfect(same[-1]):
            continue
        best = same[-1]
        if leaderboard.is_ablation(best, config.evaluation) or stale(config, component, best):
            continue
        if can_exceed(config, component, own, best):
            continue
        kind = "balanced score" if config.balance.get(component) else "pass or fail result"
        where = f"sample {sample}" if sample else "the full set"
        return (f"{name} already passed {best['passed']}/{best['cases']} on these cases ({where}) at "
                f"{money(per_case(best, 'cost_usd'))}, and {impl} ({money(per_case(own, 'cost_usd') if own else None)}, "
                f"may spend money: {paid}) cannot beat it on the {kind}; pass --force \"reason\" to run it anyway "
                f"(the reason is recorded in the row's details)")
    return ""


def unsolved_cases(config: Config, component: str, impl: str) -> List[str]:
    """The ids of the arm's failed cases that have not passed since, in the order they were run (``run_log.unsolved_failures``)."""
    return run_log.unsolved_failures(Path(config.root) / config.runs_log, component, impl,
                                     leaderboard.cases_digest(component, config.evaluation))


def unsolved_reason(config: Config, component: str, impl: str) -> str:
    """Why a run of every case is premature: cases of the arm's latest runs failed and were not rerun to a pass (an empty
    string when none). The iterative use of a metric fixes a failing case at once and reruns only the failing cases
    (``esoi run --failed``) until they pass; the whole set waits for that. A failure inside a finished, recorded whole run is a
    measurement, not work in progress, and is not counted (``run_log.unsolved_failures``)."""
    failing = run_log.unsolved_failures(Path(config.root) / config.runs_log, component, impl,
                                        leaderboard.cases_digest(component, config.evaluation))
    if not failing:
        return ""
    shown = ", ".join(failing[:8]) + (f" and {len(failing) - 8} more" if len(failing) > 8 else "")
    return (f"{len(failing)} case(s) failed in the latest run and have not passed since ({shown}); run `esoi run {component} "
            f"--impl {impl} --failed` until they pass, or pass --force \"reason\" to run the whole set anyway "
            "(the reason is recorded in the row's details)")


def declared_benchmark(config: Config, component: str) -> str:
    """The public benchmark name a component declares, else an empty string."""
    path = Path(config.evaluation) / component / BENCHMARK_FILE
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.strip().startswith("#"):
                return line.strip()
    table = (config.evidence or {}).get("benchmarks", {})
    return str(table.get(component, "")).strip()


def public_rows(config: Config, component: str, impl: str) -> Tuple[str, List[evidence.Evidence]]:
    """``(benchmark, independent evidence rows)`` for the arm's candidate on the component's declared benchmark."""
    benchmark = declared_benchmark(config, component)
    if not benchmark:
        return "", []
    try:
        rows = evidence.load_for(config)
    except evidence.EvidenceError as exc:
        raise ValueError(f"the evidence file cannot be read: {exc}") from exc
    names = {evidence.norm(impl), evidence.norm(variants.base_of(impl))}
    alias = evidence.aliases(config)

    def matches(row: evidence.Evidence) -> bool:
        candidate = evidence.norm(row.candidate)
        target = alias.get(candidate, "")
        return candidate in names or (bool(target) and (target in names or target.split(":")[-1] in names))

    wanted = evidence.norm(benchmark)
    return benchmark, [r for r in rows if r.independent and matches(r) and evidence.norm(r.comparator) == wanted]


def public_line(row: evidence.Evidence, benchmark: str) -> str:
    return (f"{row.candidate} {row.measure} = {row.value:g} {row.unit} on {benchmark} ({row.source_kind}, "
            f"{row.source_url}, checked {row.date_checked})")


def check_differs(text: str) -> str:
    """The ``--differs`` text, or a ValueError naming the accepted kinds. It must start with one of ``DIFFERS``."""
    clean = " ".join((text or "").split())
    head = clean.split(":", 1)[0].strip().lower()
    if head not in DIFFERS:
        raise ValueError(f"--differs needs to start with what differs, one of {', '.join(DIFFERS)} "
                         f"(for example --differs \"harness: our tool set\"), got {text!r}")
    return clean


def public_reason(config: Config, component: str, impl: str) -> Tuple[str, List[str]]:
    """``(refusal, lines)``: the public numbers found for the arm (printed whichever way the run goes) and the refusal
    sentence (blank when there are none)."""
    benchmark, found = public_rows(config, component, impl)
    if not found:
        return "", []
    lines = [public_line(r, benchmark) for r in found]
    return (f"a public result already exists for {impl} on {benchmark}: {lines[0]}"
            f"{' (and %d more)' % (len(lines) - 1) if len(lines) > 1 else ''}; run only to learn what differs: pass "
            f"--differs \"harness: ...\" (or prompt, settings, corpus, metric), or --force \"reason\""), lines


def note_details(details: str, notes: List[str], limit: int = 300) -> str:
    """``details`` with the override notes appended after it (the notes are kept whole; the headline is clipped to fit)."""
    if not notes:
        return details
    tail = " | ".join(notes)
    room = max(limit - len(tail) - 3, 0)
    head = details if len(details) <= room else details[:max(room - 3, 0)] + "..."
    return f"{head} | {tail}" if head else tail


def force_reason(text: Optional[Any]) -> str:
    """The cleaned ``--force`` reason; a blank one raises, because an override with no reason is not recorded."""
    clean = " ".join(str(text or "").split())
    if text is not None and not clean:
        raise ValueError("--force needs a reason, for example --force \"checking a regression after the prompt change\"")
    return clean


def sample_of(flags: List[str]) -> str:
    """The ``sample`` label that the run flags ``--sample N`` or ``--only IDS`` record (blank for the whole set)."""
    if len(flags) == 2 and flags[0] == "--sample":
        return f"sample:{flags[1]}"
    if len(flags) == 2 and flags[0] == "--only":
        return "only:" + flags[1]
    return ""
