"""Rules S60 and S61. S60: a finding or candidate rated against a solution that has recorded results cites those results, and is about
one solution. S61: a knowledge item has a source and stays current (``esoi.understanding.solution_consideration.knowledge.problems``).

The files are the ones ``[[consider.records]]`` in the configuration declares with ``kind = "finding"`` or ``"candidate"``
(``esoi.understanding.solution_consideration.network_records``). A row reaches a solution through its solution column, or through a
candidate that is one of the solution's implementations. Two failures:

* the row reaches a solution whose metric has recorded results, and it neither fills the declared ``results`` column nor names the
  results log (``esoi/results.csv`` or whatever ``results`` is set to): a rating made without the measurements already held;
* the row reaches more than one solution: each solution gets its own consideration, so a candidate is one row per solution;
* the file has no column that names the solution: a row can then be tied to a solution only through its candidate.

A waiver excuses one key: the row's id (or the file's path for the missing column).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from esoi.structure.structure_check.rules.base import Context, RuleGroup

SUMMARIES = {
    "S60": "A finding or candidate in a file `[[consider.records]]` declares is about one solution, and when that solution has recorded "
           "results it cites them (its `results` column, or the results log named in its text); the file has a column naming the solution "
           "(waive as the row id, or the file path).",
    "S61": "A knowledge item (knowledge.csv) has a source, a known kind, status and solution; an active item is not past its expiration, and "
           "one sourced on a result is re-confirmed when a newer result of that arm departs from it (waive as the knowledge id).",
}


def measured_solutions(ctx: Context) -> Dict[str, str]:
    """``{solution id: a short account of its recorded results}`` for every solution whose metric's component has rows in the log."""
    from esoi.structure.intent_registry.registry import harness_arms
    from esoi.structure.intent_registry.tables import ids
    out: Dict[str, str] = {}
    for metric in ctx.registry.metrics:
        for component, _ in harness_arms(ctx.config, metric.get("command", "")):
            arms = ctx.history.get(component, {})
            if not arms:
                continue
            account = f"{sum(len(r) for r in arms.values())} row(s) of {component}"
            for sid in ids(metric.get("solution_ids", "")):
                out.setdefault(sid, account)
    return out


def knowledge_lines(ctx: Context) -> List[str]:
    from esoi.understanding.solution_consideration import knowledge
    return [f"S61 {key}: {problem}" for key, problem in knowledge.problems(ctx.config, ctx.registry, ctx.history) if not ctx.waived("S61", key)]


def run(ctx: Context) -> List[str]:
    return finding_lines(ctx) + knowledge_lines(ctx)


def finding_lines(ctx: Context) -> List[str]:
    from esoi.optimization.when_metrics_are_run.public_evidence.evidence_records import aliases
    from esoi.understanding.solution_consideration import network_records
    files = [f for f in network_records.declared(ctx.config) if f.checked]
    if not files:
        return []
    measured = measured_solutions(ctx)
    known = {r.get("solution_id", "") for r in ctx.registry.every_solution()}
    alias = aliases(ctx.config)
    results_name = Path(ctx.config.results).name
    bad: List[str] = []
    for record in files:
        where = record.path.relative_to(ctx.root) if record.path.is_relative_to(ctx.root) else record.path
        if not record.solution_column and not ctx.waived("S60", str(where)):
            bad.append(f"S60 {where}: no column names the solution a row is rated against; add solution_id (one row per solution) "
                       "or name the column with `solution =` in [[consider.records]]")
        for position, row in enumerate(record.rows, 2):
            key = network_records.row_id(record, row, position)
            reached = network_records.row_solutions(record, row, ctx.registry.implementations, alias, known)
            if not reached or ctx.waived("S60", key):
                continue
            if len(reached) > 1:
                bad.append(f"S60 {where} {key}: one row rates {len(reached)} solutions ({', '.join(sorted(reached))}); "
                           "write one row per solution, each judged against that solution's own records")
            uncited = [sid for sid in sorted(reached) if sid in measured]
            if uncited and not network_records.cites_results(record, row, results_name):
                bad.append(f"S60 {where} {key}: rated against {', '.join(uncited)}, which has recorded results "
                           f"({'; '.join(measured[s] for s in uncited)} in {ctx.config.results}); cite them "
                           f"(`esoi spec prompt {uncited[0]}` shows them)")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
