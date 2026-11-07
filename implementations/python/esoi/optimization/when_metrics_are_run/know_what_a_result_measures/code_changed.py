"""Say whether the code a recorded row measured changed since its commit, naming the changed file and who owns it."""
from __future__ import annotations

from typing import Dict

from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import attest, ownership_index, staleness
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_provenance import changed_since
from esoi.structure.intent_registry.config import Config


def code_changed_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why the code a row measured changed since its commit, naming the changed file and who owns it, or an empty string. The
    files that count are the ones the staleness rule says the arm measures (``esoi.optimization.when_metrics_are_run.know_what_a_result_measures.staleness``); under ``repo_wide`` any file
    of the measured folders."""
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
