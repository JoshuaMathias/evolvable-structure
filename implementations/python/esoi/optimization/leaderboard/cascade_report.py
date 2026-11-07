"""``esoi cascade [SOLUTION]``: print each stage, every implementation's result per stage, the implementation the cascade chooses and the next stage worth running."""
from __future__ import annotations

import datetime
from typing import Callable, List, Optional

from esoi.optimization.leaderboard import arm_selection, results_log
from esoi.optimization.leaderboard.results_log import Row
from esoi.optimization.leaderboard.cascade_stages import Stage, expectation_notes, load_stages
from esoi.optimization.leaderboard.stage_standings import decide, next_stage, standings


def run_command(component: str, impl: str, stage: Stage) -> str:
    """The ``esoi run`` line that records a result for this stage. It is a suggestion: a stage with ``real=yes`` calls a
    model, so it needs the metric run policy's estimate, budget and approval first."""
    flag = f" --sample {stage.sample[len('sample:'):]}" if stage.sample.startswith("sample:") else ""
    pick = " (choose the sample size)" if stage.sample == "sample" else ""
    return f"esoi run {component} --impl {impl}{flag} --record{pick}"


def describe(row: Optional[Row]) -> str:
    return "not run" if row is None else f"{row.get('passed', '?')}/{row.get('cases', '?')} on {row.get('date', '?')}"


def public_lines(config, registry, solution_id: str, graded, stages: List[Stage], say: Callable[[str], None]) -> None:
    """The graded public evidence of each implementation of a solution, labelled as such. It is not a result: it is never in the
    standings, never chooses an implementation, and a ``public`` stage reads it only to say whether it is satisfied."""
    if not graded:
        return
    from esoi.optimization.when_metrics_are_run.public_evidence import evidence_grading, evidence_records
    stage = next((s for s in stages if s.public), None)
    for impl, keys in evidence_records.implementation_candidates(config, registry, solution_id).items():
        found = evidence_grading.lines_for_implementation(graded, keys)
        if not found:
            continue
        met, why = evidence_grading.public_stage_met(found)
        gate = f" [public stage {'satisfied' if met else 'not satisfied'}: {why}]" if stage else ""
        say(f"  public evidence for {impl} (others' measurements, not our result){gate}")
        for estimate in found:
            say(f"    {estimate.line()}")
            if estimate.needs_own_run:
                say(f"      to settle it: {estimate.settle}")


def report_standings(config, stages, standing, component: str, chosen: str, say: Callable[[str], None]) -> int:
    """Print each implementation's result per stage and the cascade's choice; returns 1 when the choice differs from the selected one."""
    for impl, s in sorted(standing.items()):
        say(f"  {impl}: " + "; ".join(f"{stage.name} {describe(s.rows.get(i))}"
                                       + (f" (expired: {s.expired[i][1]})" if i in s.expired else "")
                                       for i, stage in enumerate(stages) if not stage.unrun))
    decision = decide(stages, standing, config.evaluation)
    for note in decision.notes:
        say(f"  note: {note}")
    if not decision.winner:
        return 0
    say(f"  chosen by the cascade: {decision.winner} (latest stage run: {stages[decision.stage].name}; "
        f"selected in the records: {chosen or 'none'})")
    return int(bool(chosen and chosen != decision.winner))


def report_next_stages(config, stages, standing, component: str, chosen: str, say: Callable[[str], None]) -> None:
    """Print, per implementation, the next stage worth running and the command for it."""
    from esoi.runtime.consumer_check import foundation
    selected = standing.get(chosen)
    for impl, s in sorted(standing.items()):
        gate = foundation.inherited_gate(config, component, impl) if any(st.inherited for st in stages) else None
        index, why = next_stage(stages, s, selected, config.evaluation, gate)
        if index is None:
            say(f"  next for {impl}: nothing ({why})")
            continue
        extra = f"; also check: {stages[index].when}" if stages[index].when else ""
        say(f"  next for {impl}: {stages[index].name} ({why}): {run_command(component, impl, stages[index])}{extra}")


def report_metric(config, loaded, metric: dict, stages, errors, owners: List[str], graded, history: dict, today, say: Callable[[str], None]) -> int:
    """Print one metric's cascade; returns 1 when its choice differs from the selected implementation."""
    from esoi.optimization.measurement_harness import interface as harness
    from esoi.structure.intent_registry import registry as registry_module
    say(f"{metric.get('metric_id', '')}: {' > '.join(s.name for s in stages) or '(no valid stage)'}")
    for line in errors:
        say(f"  problem: {line}")
    for line in expectation_notes(stages):
        say(f"  note: {line}")
    for owner in owners:
        public_lines(config, loaded, owner, graded, stages, say)
    component, chosen = next(iter(registry_module.harness_arms(config, metric.get("command", ""))), ("", ""))
    owner = next((s for s in loaded.solutions if s["solution_id"] in owners), None)
    if owner is not None and component:
        chosen = arm_selection.selected_arm(config, owner, component, loaded)[1] or chosen
    if not stages or not component or component not in history:
        say("  no results yet: every stage is not run" if stages else "  fix the list to read it")
        return 0
    standing = standings(stages, history[component], today, lambda row: harness.stale_reason(config, component, row, True), config.evaluation)
    behind = report_standings(config, stages, standing, component, chosen, say)
    report_next_stages(config, stages, standing, component, chosen, say)
    return behind


def run_cli(config, solution: str = "", strict: bool = False, say: Callable[[str], None] = print,
            today: Optional[datetime.date] = None) -> int:
    """``esoi cascade [SOLUTION]``: each stage, every implementation's result per stage (a stage not run says so), which
    implementation the cascade chooses against the selected one, and the next stage worth running. With ``strict`` it
    exits 1 when the chosen implementation is not the selected one."""
    from esoi.optimization.when_metrics_are_run.public_evidence import evidence_grading, evidence_records
    from esoi.structure.intent_registry import registry as registry_module
    from esoi.structure.intent_registry.tables import ids
    loaded = registry_module.load(config)
    history = results_log.all_results(config.results_path)
    evidence_rows = evidence_records.load_for(config)
    graded = evidence_grading.estimates(evidence_rows, today) if evidence_rows else {}
    found, behind = 0, 0
    for metric in loaded.metrics:
        stages, errors = load_stages(config, metric)
        owners = ids(metric.get("solution_ids", ""))
        if not stages and not errors or (solution and solution not in owners):
            continue
        found += 1
        behind += report_metric(config, loaded, metric, stages, errors, owners, graded, history, today, say)
    if solution and not found:
        say(f"no cascading conditionals are recorded for {solution}")
    return 1 if strict and behind else 0
