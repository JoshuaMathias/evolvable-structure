"""Rule S47: a metric that builds on a foundation metric (``[builds_on]``, ``esoi.foundation``) keeps its declaration readable and inherits the
foundation's gates without loosening them.

* the ``[builds_on.<component>.<name>]`` tables name an existing foundation repository and component, a share between 0 and 1 (all shares
  below 1) and a known ``on_stale``;
* a cascade stage with ``inherits=<stage>`` names a stage the foundation's metric has, and a gate or floor written beside it is the same or
  stricter than the foundation's (``cascade.loosens``);
* the consumer's ``[balance.<component>.source_access]`` limits (read budget, allowed scopes, no full scan) are the same or tighter than the
  foundation's (``access.loosening``).

A consumer that must be looser has a different purpose than its foundation, and the finding says to build a metric of its own instead. A waiver
excuses one key: the consumer component.
"""
from __future__ import annotations

from .. import access, cascade, foundation, registry as registry_module
from ..config import ConfigError
from .base import Context, RuleGroup

SUMMARIES = {
    "S47": "A metric that builds on a foundation (`[builds_on.<component>.<name>]`) declares a readable foundation and shares below 1, every `inherits=` stage "
           "exists in the foundation's cascade, and its gates (a stage's gate or floor, the `source_access` read limits) are the same or tighter than the "
           "foundation's, never looser (waive as the consumer component).",
}


def run(ctx: Context) -> list:
    bad = [f"S47 builds_on: {line}" for line in foundation.problems(ctx.config)]
    for f in foundation.declared(ctx.config):
        if ctx.waived("S47", f.component):
            continue
        try:
            fconf = foundation.load_config(f)
            floor = access.loosening(ctx.config.balance.get(f.component), fconf.balance.get(f.target))
            theirs = [s for m in registry_module.load(fconf).metrics
                      if f.target in [c for c, _ in registry_module.harness_arms(fconf, m.get("command", ""))]
                      for s in cascade.load_stages(fconf, m)[0]]
        except (ConfigError, ValueError) as exc:
            bad.append(f"S47 {f.component}: the foundation {f.name} cannot be read ({exc})")
            continue
        bad.extend(f"S47 {f.component}: source_access of the consumer is looser than the foundation {f.name}'s: {why}" for why in floor)
        for metric in ctx.registry.metrics:
            if f.component not in [c for c, _ in ctx.harness_arms(metric.get("command", ""))]:
                continue
            for stage in cascade.load_stages(ctx.config, metric)[0]:
                if not stage.inherited:
                    continue
                match = next((s for s in theirs if s.name == stage.inherits), None)
                if match is None:
                    bad.append(f"S47 {metric.get('metric_id', '')}: stage {stage.name} inherits {stage.inherits!r}, which the foundation {f.name} has no stage of")
                elif why := cascade.loosens(stage, match):
                    bad.append(f"S47 {metric.get('metric_id', '')}: stage {stage.name} loosens the inherited gate: {why}; tighten it or drop the gate")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
