"""Say why a recorded result no longer counts: other cases, changed code, changed circumstances, a malformed row or an expired metric."""
from __future__ import annotations

import datetime
import subprocess
from typing import Dict, Optional

from esoi.optimization.leaderboard import circumstances
from esoi.optimization.leaderboard.case_identity import cases_digest
from esoi.optimization.leaderboard.results_log import is_partial
from esoi.optimization.measurement_harness.code_provenance import changed_since, external_code_paths, parse_code_shas
from esoi.optimization.measurement_harness.per_case_log import read_per_case
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import ownership_index, staleness
from esoi.runtime.consumer_check import foundation
from esoi.structure.intent_registry.config import Config


def code_changed_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why the code a row measured changed since its commit, naming the changed file and who owns it, or an empty string. The
    files that count are the ones the staleness rule says the arm measures (``esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness``); under ``repo_wide`` any file
    of the measured folders."""
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import attest
    sha = attest.covered_base(config, component, row.get("impl", ""), row["git_sha"])   # an attested range is not counted
    if ownership_index.rule_for(config) == "repo_wide":
        changed = changed_since(config, sha)
        return f"the measured code changed since its commit {sha} ({changed[0]}{' and others' if len(changed) > 1 else ''})" if changed else ""
    found = staleness.explain(config, component, row.get("impl", ""), sha)
    if not found or not found["counts"]:
        return ""
    counts, rule, note = found["counts"], found["rule"][0], found["rule"][1]
    more = f" and {len(counts) - 1} more" if len(counts) > 1 else ""
    fallback = f"; {rule} rule, {note}" if note else f"; {rule} rule"
    return f"the measured code changed since its commit {sha} ({counts[0]}{more}{fallback})"


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


def stale_reason(config: Config, component: str, row: Optional[Dict[str, str]], strict: bool = True) -> str:
    """Why a recorded result no longer counts, or an empty string when it is current. A result is stale when it is missing,
    has no commit, was run on other cases than the ones now on disk, and (strict) was run on uncommitted code or the
    measured code, in this repository or in another one named by ``code_paths``, has changed since its commit."""
    if row is None:
        return "it has no recorded result"
    if why := defect_reason(config, component, row):
        return why
    now = cases_digest(component, config.evaluation)
    if row.get("cases_sha", "") != now:
        return f"its latest row was recorded on other cases (cases_sha {row.get('cases_sha') or 'blank'}, now {now})"
    if why := circumstances_stale(config, component, row):
        return why
    if strict and row["git_sha"].endswith("-dirty"):
        return "its latest row was recorded on uncommitted code"
    if strict and (why := code_changed_reason(config, component, row)):
        return why
    if why := foundation.stale_reason(config, component, row):   # a foundation this row builds on changed (esoi.runtime.consumer_check.foundation)
        return why
    return external_reason(config, row) if strict else ""


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
    mine = [r for r in read_per_case(config) if (r["component"], r["impl"], r["cases_sha"], r["sample"]) == wanted]
    if not any(r["circumstances_sha"] == circumstances.digest(circs) for r in mine):
        return "its slice rows and per-case log were not derived from the current circumstances.csv (re-run it to derive them)"
    return ""


def expired_reason(config: Config, component: str, row: Optional[Dict[str, str]], today: Optional[datetime.date] = None) -> str:
    """Why a row's age makes it worth re-running: a metric of the solutions this component measures declares an expiration (or the
    project's ``[expiration] default`` does) and the row is older. Empty when none is declared (never by default) or it has not passed."""
    from esoi.optimization.leaderboard import cascade_stages
    from esoi.structure.intent_registry.registry import harness_arms, load
    if not row or not row.get("date"):
        return ""
    try:
        recorded = datetime.date.fromisoformat(row["date"][:10])
    except ValueError:
        return ""
    today = today or datetime.date.today()
    for metric in load(config).metrics:
        if not any(comp == component for comp, _ in harness_arms(config, metric.get("command", ""))):
            continue
        days, _ = cascade_stages.parse_expiration(metric.get("expiration", ""))
        if days is None and not metric.get("expiration", "").strip():
            days, _ = cascade_stages.default_days(config)
        if days is not None and (today - recorded).days > days:
            return f"its metric {metric.get('metric_id', '')} declares an expiration of {days} days and the row is {(today - recorded).days} days old"
    return ""
