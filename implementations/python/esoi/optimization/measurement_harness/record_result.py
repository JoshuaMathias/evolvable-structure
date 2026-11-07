"""Append one run's summary to the results log, the source of truth for metrics."""
from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from esoi.optimization.leaderboard.case_identity import cases_digest
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import code_provenance
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_provenance import code_shas, external_code_paths
from esoi.optimization.measurement_harness.run_cost import run_cost
from esoi.structure.intent_registry.config import Config


RESULT_COLUMNS = ["date", "component", "impl", "cases", "passed", "dev", "heldout", "model_calls",
                  "tokens_in", "tokens_out", "cost_usd", "seconds", "balanced", "git_sha", "cases_sha", "sample", "model", "details"]


def record_result(summary: Dict[str, Any], config: Config, date: Optional[str] = None,
                  path: Optional[Path] = None, model_env: Optional[str] = None) -> Dict[str, Any]:
    """Append one run's summary to the results log, the source of truth for metrics. Returns the row written."""
    comp = summary.get("component", "")
    model = summary.get("model") or (model_env if summary.get("model_calls") and model_env else
                                     ("unknown" if summary.get("model_calls") else "none"))
    row = dict(summary, date=date or datetime.date.today().isoformat(),
               cost_usd=run_cost(config, summary, model),
               git_sha=code_provenance.current_sha(config, summary.get("component", ""), summary.get("impl", "")), model=model, cases_sha=cases_digest(comp, config.evaluation))
    target = Path(path) if path else config.results_path
    wanted = bool(external_code_paths(config))
    if wanted:
        row["code_shas"] = code_shas(config)
    append_row(target, row, wanted, ["builds_on"] if row.get("builds_on") else [])
    return row


def read_log(target: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """``(header, rows)`` of the results log, empty when there is none yet."""
    if not target.exists():
        return [], []
    with open(target, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def append_row(target: Path, row: Dict[str, Any], with_code_shas: bool, extra: List[str] = ()) -> None:
    """Append ``row`` to the results log. The log gains a trailing ``code_shas`` column the first time a repository with
    code in another repository records (older rows keep it blank)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    header, old_rows = read_log(target)
    wanted = RESULT_COLUMNS + (["code_shas"] if with_code_shas else []) + [c for c in extra if c not in RESULT_COLUMNS]
    columns = header + [c for c in wanted if c not in header] if header else wanted
    rewrite = not header or columns != header
    with open(target, "w" if rewrite else "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        if rewrite:
            writer.writeheader()
            writer.writerows(old_rows)
        writer.writerow(row)
