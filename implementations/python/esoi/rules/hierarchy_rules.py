"""Rule S35: a child that overrides its parent's default says why, in its own records.

Active only where the configuration has a ``[parent]`` table (the parent's records folder or snapshot); a repository without one
is never reported. See ``esoi.hierarchy`` and the guide on hierarchical defaults.
"""
from __future__ import annotations

from .. import hierarchy, variants
from ..select import default_name
from .base import Context, RuleGroup

SUMMARIES = {
    "S35": "Where `[parent]` names the package this one builds on, a solution whose `selected` arm differs from the parent's default "
           "cites in `overrides.csv` (`solution_id`, `reason_ids`) the id of one of its own problem, ideal or metric records, or a "
           "waiver names the pending decision (waive as `<solution>`). An `unconfirmed:` reason does not satisfy it.",
}


def run(ctx: Context) -> list:
    if not ctx.config.parent:
        return []
    try:
        parent = hierarchy.parent_defaults(ctx.config)
        reasons = hierarchy.read_overrides(ctx.config)
    except ValueError as error:
        return [f"S35 esoi.toml: {error}"]
    own = {r.get(key, "") for rows, key in ((ctx.registry.problems, "problem_id"), (ctx.registry.ideals, "ideal_id"),
                                            (ctx.registry.metrics, "metric_id")) for r in rows}
    bad = []
    for row in ctx.every_solution():
        sid = row.get("solution_id", "")
        chosen = variants.base_of(default_name(row, ctx.registry.implementations)).lower()
        if not (sid in parent and chosen and chosen != parent[sid]):
            continue
        cited = [i for i in reasons.get(sid, ()) if i in own]
        missing = [i for i in reasons.get(sid, ()) if i not in own]
        if cited and not missing:
            continue
        if not ctx.waived("S35", sid):
            bad.append(f"S35 {sid}: selected is {chosen} but the parent's default is {parent[sid]}, and "
                       + (f"overrides.csv cites {', '.join(missing)}, which no problem, ideal or metric of this repository has" if missing
                          else "no reason id in overrides.csv names a problem, ideal or metric of this repository")
                       + "; cite one (reason_ids) or waive naming the pending decision")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
