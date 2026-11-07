"""Say why a recorded result no longer counts: other cases, changed code, changed circumstances, a malformed row or an expired metric."""
from __future__ import annotations

import datetime
import subprocess
from typing import Dict, Optional

from esoi.structure.intent_registry.interface import circumstances
from esoi.optimization.leaderboard.case_identity import cases_digest
from esoi.optimization.leaderboard.results_log import is_partial, per_case_rows
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import builds_on
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_changed import code_changed_reason
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_provenance import external_code_paths, parse_code_shas
from esoi.structure.intent_registry.config import Config


def external_reason(config: Config, row: Dict[str, str]) -> str:
    """Why the code a row measured in other repositories (``code_paths`` outside this one) no longer counts."""
    recorded = parse_code_shas(row.get("code_shas", ""))
    for entry, repo, inside in external_code_paths(config):
        sha = recorded.get(entry)
        if not sha:
            return f"its latest row records no commit for the code path {entry} in another repository (re-run with --record)"
        if sha.endswith("-dirty"):
            return f"its latest row was recorded on uncommitted code in {entry}"
        done = subprocess.run(["git", "diff", "--name-only", sha, "--", inside], cwd=repo, capture_output=True, text=True)
        if done.returncode == 0 and done.stdout.split():
            changed = done.stdout.split()
            return f"the measured code in {entry} changed since its commit {sha} ({changed[0]}{' and others' if len(changed) > 1 else ''})"
    return ""


def defect_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a recorded row is malformed, as opposed to stale: it names no commit (it cannot say what it measured), or
    ``circumstances.csv`` cannot be read. A defect is a problem for ``esoi check``; every other reason in ``stale_reason``
    (the cases, the code, the circumstances or the tree changed since the run) is a fact about time and only informs."""
    if not row.get("git_sha", "").strip():
        return "its latest row has no git_sha"
    try:
        circumstances.for_component(config, component)
    except ValueError as exc:
        return f"circumstances.csv cannot be read: {exc}"
    return ""


def other_cases_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a row no longer counts when it was run on other cases than the ones now on disk."""
    now = cases_digest(component, config.evaluation)
    if row.get("cases_sha", "") == now:
        return ""
    return f"its latest row was recorded on other cases (cases_sha {row.get('cases_sha') or 'blank'}, now {now})"


def code_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a row no longer counts when it was run on uncommitted code or the measured code has changed since its commit."""
    if row["git_sha"].endswith("-dirty"):
        return "its latest row was recorded on uncommitted code"
    return code_changed_reason(config, component, row)


def stale_reason(config: Config, component: str, row: Optional[Dict[str, str]], strict: bool = True) -> str:
    """Why a recorded result no longer counts, or an empty string when it is current. A result is stale when it is missing,
    has no commit, was run on other cases than the ones now on disk, and (strict) was run on uncommitted code or the
    measured code, in this repository or in another one named by ``code_paths``, has changed since its commit."""
    if row is None:
        return "it has no recorded result"
    return (defect_reason(config, component, row) or other_cases_reason(config, component, row) or circumstances_stale(config, component, row)
            or (code_reason(config, component, row) if strict else "")
            or builds_on.stale_reason(config, component, row)   # a foundation this row builds on changed (esoi.runtime.consumer_check.foundation)
            or (external_reason(config, row) if strict else ""))


def circumstances_stale(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a whole-run row's derived rows no longer count: ``circumstances.csv`` changed (or cannot be read) since they were
    derived, or the per-case log holds no rows for the run. Empty for a component with no circumstances."""
    if is_partial(row):
        return ""
    try:
        circs = circumstances.for_component(config, component)
    except ValueError as exc:
        return f"circumstances.csv cannot be read: {exc}"
    if not circs:
        return ""
    wanted = (component, row.get("impl", ""), row.get("cases_sha", ""), (row.get("sample") or "").strip())
    mine = [r for r in per_case_rows(config) if (r["component"], r["impl"], r["cases_sha"], r["sample"]) == wanted]
    if not any(r["circumstances_sha"] == circumstances.digest(circs) for r in mine):
        return "its slice rows and per-case log were not derived from the current circumstances.csv (re-run it to derive them)"
    return ""


def expiration_days(config: Config, metric: Dict[str, str]) -> Optional[int]:
    """The days after which a metric's results expire: its own expiration, else the project's default, else none."""
    from esoi.optimization.leaderboard import cascade_stages
    days, _ = cascade_stages.parse_expiration(metric.get("expiration", ""))
    if days is None and not metric.get("expiration", "").strip():
        days, _ = cascade_stages.default_days(config)
    return days


def expired_reason(config: Config, component: str, row: Optional[Dict[str, str]], today: Optional[datetime.date] = None) -> str:
    """Why a row's age makes it worth re-running: a metric of the solutions this component measures declares an expiration (or the
    project's ``[expiration] default`` does) and the row is older. Empty when none is declared (never by default) or it has not passed."""
    from esoi.structure.intent_registry.registry import harness_arms, load
    if not row or not row.get("date"):
        return ""
    try:
        recorded = datetime.date.fromisoformat(row["date"][:10])
    except ValueError:
        return ""
    today = today or datetime.date.today()
    for metric in load(config).metrics:
        days = expiration_days(config, metric) if any(comp == component for comp, _ in harness_arms(config, metric.get("command", ""))) else None
        if days is not None and (today - recorded).days > days:
            return f"its metric {metric.get('metric_id', '')} declares an expiration of {days} days and the row is {(today - recorded).days} days old"
    return ""
