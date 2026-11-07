"""Rules about generated files and the intent records: S8, S17, S26 and S27.

S8 the generated component index matches components.csv, S17 the tracker tabs match the registry (checked only
when a tracker folder exists), S26 the intent records fill every template field and link as the template says
(rules R1 to R4 of ``esoi.structure.intent_registry.records``), S27 the committed template copy matches its source (skipped where the
source is not reachable).
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from esoi.structure.intent_registry.template_sync import template as template_module
from esoi.understanding.review_tracker.interface import build, columns, extras, tracker_stale
from esoi.structure.intent_registry import intents
from esoi.understanding.readable_records.interface import readme_pages
from esoi.structure.intent_registry.records import check_headers, check_records, overall_ids, tables_of
from esoi.structure.structure_check.rules.base import Context, RuleGroup

TRACKER_DUPLICATE_HINT = {
    "implementations": "two implementations of one solution get the same record id; give their paths or names "
                       "(`path::name`) or their implementations.csv ids a difference",
    "solutions": "a solution_id repeats in solutions.csv", "problems": "a problem_id repeats in problems.csv",
    "ideals": "an ideal_id repeats in ideals.csv or collides with a principle", "metrics": "a metric_id repeats in metrics.csv"}

KEYS = {"problem": "problem_id", "ideal": "ideal_id", "solution": "solution_id", "implementation": "implementation_id",
        "metric": "metric_id"}

SUMMARIES = {
    "S8": "COMPONENTS.md matches components.csv, and each intent folder's README.md and diagram.md match its records (esoi check "
          "--write-docs regenerates them).",
    "S17": "The tracker tabs match what the registry and the results log now produce (only tracking_* columns are "
           "hand-edited). Checked when the tracker folder exists.",
    "S26": "The intent records fill every field of the evolvable-structure template and link as it says "
           "(a problem is not a task, every problem has a solution and an ideal, links agree both ways), and "
           "parent links resolve (in the legacy layout, to the overall network; in the intent layout, anywhere in the tree). "
           "A records file carries no other column than the template's fields, technical columns (ids, links, file paths, "
           "commands) and the fields the specification's owner approved under `[records] approved_fields` in esoi.toml (R7).",
    "S27": "The committed template copy equals the source it was parsed from (skipped when the source is not reachable).",
}


def render_components_doc(components: List[Dict[str, str]], structure_dir: str) -> str:
    lines = [
        "# Components",
        "",
        f"Generated from `{structure_dir}/components.csv` by `esoi check --write-docs`.",
        "Edit the CSV, never this file. The rules are listed by `esoi rules`.",
        "",
        "| Component | Handle | Layer | Role | Serves |",
        "|---|---|---|---|---|",
    ]
    for r in components:
        def cell(key: str) -> str:
            return r.get(key, "").replace("|", "/").replace(";", ", ")
        lines.append(f"| {cell('name').strip() or r['component_id']} | `{r['component_id']}` | {r['layer']} | {cell('role')} | {cell('solutions')} |")
    return "\n".join(lines) + "\n"


def generated_page_problems(ctx: Context) -> List[str]:
    """S8 for the components document, the folder pages and the diagrams that are out of date."""
    bad: List[str] = []
    config = ctx.config
    doc = config.structure / "COMPONENTS.md"
    if not doc.exists() or doc.read_text(encoding="utf-8") != render_components_doc(ctx.components, config.structure_dir):
        bad.append(f"S8 {config.structure_dir}/COMPONENTS.md: out of date (run `esoi check --write-docs`)")
    if config.intent_mode:
        for page, text in readme_pages(config, ctx.registry, ctx.results, written_arm_pages_only=True):
            if not page.exists() or page.read_text(encoding="utf-8") != text:
                bad.append(f"S8 {page.relative_to(config.root)}: out of date (run `esoi readmes`)")
        from esoi.understanding.readable_records.interface import stale
        bad.extend(f"S8 {path.relative_to(config.root)}: out of date (run `esoi diagram` or `esoi check --write-docs`)"
                   for path in stale(config, ctx.registry))
    return bad


def tracker_problems(ctx: Context) -> List[str]:
    """S18 for a tracker tab with a repeated id, and S17 for a tab that is out of date."""
    config = ctx.config
    if not config.tracker_dir.is_dir():
        return []
    bad: List[str] = []
    template = ctx.template
    cols = columns(template, extras(config))
    for tab, rows in build(config, ctx.registry, template).items():
        key = cols[tab][0]
        for ident, n in Counter(r[key] for r in rows).items():
            if n > 1:
                bad.append(f"S18 tracker {tab}: id {ident} appears {n} times ({TRACKER_DUPLICATE_HINT.get(tab, 'the ids of one tab must be unique')})")
    for tab in tracker_stale(config, ctx.registry, template):
        bad.append(f"S17 {config.structure_dir}/tracker/{tab}.csv: out of date (run `esoi tracker build`)")
    return bad


def intent_record_problems(ctx: Context, pending: set, adopted: set) -> List[str]:
    """S26 for the records of the intent layout, checked as one set across the tree."""
    config = ctx.config
    bad: List[str] = []
    if config.overall:
        bad.append(f"S26 {config.overall}: `overall` is the legacy layout and is ignored beside {config.structure_dir}/intent.csv; "
                   "remove it from the configuration")
    tree = tables_of(ctx.registry)
    for _, folder in intents.folders(config):
        bad += [f"S26 {line}" for line in check_headers(folder, ctx.template, label=str(folder.relative_to(config.root)),
                                                            approved=config.approved_fields, metric_command=config.metric_command)]
    every = {entity: {r.get(key, "") for r in tree[entity]} - {""} for entity, key in KEYS.items()}
    return bad + [f"S26 {line}" for line in check_records(
        config.structure, ctx.template, pending, overall=every, tables=tree, retired={"overall_solution_ids"}, scope="the intent tree",
        require_parent=bool(config.option("S26", "require_parent", False)), approved=config.approved_fields, metric_command=config.metric_command, adopted=adopted)]


def legacy_record_problems(ctx: Context, pending: set, adopted: set) -> List[str]:
    """S26 for the records of the legacy layout: the overall network, then the detailed records linked up to it."""
    config = ctx.config
    bad: List[str] = []
    overall = None
    if config.overall:
        folder = config.root / config.overall
        if folder.is_dir():
            overall = overall_ids(folder)
            bad += [f"S26 overall network {line}" for line in
                    check_records(folder, ctx.template, interface_required=False, require_command=False,
                                  approved=config.approved_fields, metric_command=config.metric_command)]
        else:
            bad.append(f"S26 {config.overall}: overall network folder not found")
    return bad + [f"S26 {line}" for line in check_records(
        config.structure, ctx.template, pending, overall=overall,
        require_parent=bool(config.option("S26", "require_parent", False)), approved=config.approved_fields, metric_command=config.metric_command, adopted=adopted)]


def run(ctx: Context) -> List[str]:
    config = ctx.config
    bad = generated_page_problems(ctx) + tracker_problems(ctx)
    pending = {r["solution_id"] for r in ctx.every_solution() if ctx.waived("S26", r["solution_id"])}
    adopted = {r.get("solution_id", "") for r in ctx.registry.adopted}
    bad += intent_record_problems(ctx, pending, adopted) if config.intent_mode else legacy_record_problems(ctx, pending, adopted)
    if template_module.stale_against_source(config):
        bad.append(f"S27 {config.structure_dir}/esoi_template.csv: stale against its source "
                   "(run `esoi template sync`, then fill the columns it adds)")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
