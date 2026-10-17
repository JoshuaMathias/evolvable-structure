"""Rules about generated files and the intent records: S8, S17, S26 and S27.

S8 the generated component index matches components.csv, S17 the tracker tabs match the registry (checked only
when a tracker folder exists), S26 the intent records fill every template field and link as the template says
(rules R1 to R4 of ``esoi.records``), S27 the committed template copy matches its source (skipped where the
source is not reachable).
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .. import template as template_module
from .. import tracker
from ..records import check_records, overall_ids
from .base import Context, RuleGroup

TRACKER_DUPLICATE_HINT = {
    "implementations": "two implementations of one solution get the same record id; give their paths or names "
                       "(`path::name`) or their implementations.csv ids a difference",
    "solutions": "a solution_id repeats in solutions.csv", "problems": "a problem_id repeats in problems.csv",
    "ideals": "an ideal_id repeats in ideals.csv or collides with a principle", "metrics": "a metric_id repeats in metrics.csv"}

SUMMARIES = {
    "S8": "COMPONENTS.md matches components.csv (esoi check --write-docs regenerates it).",
    "S17": "The tracker tabs match what the registry and the results log now produce (only tracking_* columns are "
           "hand-edited). Checked when the tracker folder exists.",
    "S26": "The intent records fill every field of the evolvable-structure template and link as it says "
           "(a problem is not a task, every problem has a solution and an ideal, links agree both ways), and "
           "parent links to the repository's overall solution network resolve.",
    "S27": "The committed template copy equals the source it was parsed from (skipped when the source is not reachable).",
}


def render_components_doc(components: List[Dict[str, str]], structure_dir: str) -> str:
    lines = [
        "# Components",
        "",
        f"Generated from `{structure_dir}/components.csv` by `esoi check --write-docs`.",
        "Edit the CSV, never this file. The rules are listed by `esoi rules`.",
        "",
        "| Component | Layer | Role | Serves |",
        "|---|---|---|---|",
    ]
    for r in components:
        def cell(key: str) -> str:
            return r[key].replace("|", "/").replace(";", ", ")
        lines.append(f"| `{r['component_id']}` | {r['layer']} | {cell('role')} | {cell('solutions')} |")
    return "\n".join(lines) + "\n"


def run(ctx: Context) -> List[str]:
    bad: List[str] = []
    config = ctx.config
    doc = config.structure / "COMPONENTS.md"
    if not doc.exists() or doc.read_text(encoding="utf-8") != render_components_doc(ctx.components, config.structure_dir):
        bad.append(f"S8 {config.structure_dir}/COMPONENTS.md: out of date (run `esoi check --write-docs`)")

    if config.tracker_dir.is_dir():
        template = ctx.template
        cols = tracker.columns(template, tracker.extras(config))
        for tab, rows in tracker.build(config, ctx.registry, template).items():
            key = cols[tab][0]
            for ident, n in Counter(r[key] for r in rows).items():
                if n > 1:
                    bad.append(f"S18 tracker {tab}: id {ident} appears {n} times ({TRACKER_DUPLICATE_HINT.get(tab, 'the ids of one tab must be unique')})")
        for tab in tracker.stale(config, ctx.registry, template):
            bad.append(f"S17 {config.structure_dir}/tracker/{tab}.csv: out of date (run `esoi tracker build`)")

    pending = {r["solution_id"] for r in ctx.solutions if ctx.waived("S26", r["solution_id"])}
    overall = None
    if config.overall:
        folder = config.root / config.overall
        if folder.is_dir():
            overall = overall_ids(folder)
            bad += [f"S26 overall network {line}" for line in
                    check_records(folder, ctx.template, interface_required=False, require_command=False)]
        else:
            bad.append(f"S26 {config.overall}: overall network folder not found")
    bad += [f"S26 {line}" for line in check_records(
        config.structure, ctx.template, pending, overall=overall,
        require_parent=bool(config.option("S26", "require_parent", False)))]
    if template_module.stale_against_source(config):
        bad.append(f"S27 {config.structure_dir}/esoi_template.csv: stale against its source "
                   "(run `esoi template sync`, then fill the columns it adds)")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
