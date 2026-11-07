"""S54 to S59, opt-in and advisory: where the code and records of this project divide the work badly, from Structure Quality's first stage.

Each rule is one dimension of the balanced number (``esoi.structure.structure_quality``): S54 scope, S55 size and cohesion, S56 coupling, S57 reuse and
duplication, S58 public surface, S59 behavior preserved. They run only where ``[rules.S5x] enabled = true`` and never fail a check: each finding says
the next action, and the fix is at the source (split the part, move the call to the entry point, name the copied code once, add the contract test).
A waiver excuses one key: the path or unit a finding opens with. At most ``SHOWN`` findings of a rule are listed, worst first, then one line counts the rest.
Flow fidelity, the fifth dimension, is rule S38, so it has no rule here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from esoi.structure.structure_check.rules.base import Context, RuleGroup
from esoi.structure.structure_quality.interface import assess

SHOWN = 10
DIMENSION_OF = {"S54": "scope", "S55": "size", "S56": "coupling", "S57": "reuse", "S58": "surface", "S59": "behavior"}
NEXT = {
    "S54": "give each solution one job: make every arm implement every member of its Protocol with matching parameters and a real body, merge a solution whose arms only pass each call on into the one they call, split a folder that declares several unrelated jobs, and split arms that serve different purposes",
    "S55": "split the part at a seam of its own job, not into fragments (a function by step, a module by responsibility, a folder by solution); fragments raise the coupling and navigation cost this rule balances",
    "S56": "call the other unit through its entry point (its interface), move a name only one unit takes out of the shared kernel into that unit, break the cycle by moving the shared part down to a unit both use, and never name a consumer from a library",
    "S57": "write the copied code once in the unit that owns the job and call it from the rest",
    "S58": "export only the names another unit uses, or add the consumer that justifies the name",
    "S59": "add one contract test or one shared case set that runs every arm of the solution, so a refactor cannot delete behavior production uses",
}
SUMMARIES = {
    "S54": "Opt-in advisory, Structure Quality scope: every arm implements every member of its solution's Protocol with matching parameters and more than a stub under a solution id that exists, an arm does work of its own, "
           "a folder declares no more Protocols than its budget, and the arms of one solution share one purpose (waive as the path, unit or solution id a finding opens with).",
    "S55": "Opt-in advisory, Structure Quality size and cohesion: function lines, module lines, complexity per function, folders, intents and depth stay inside their budgets (waive as the path or folder a finding opens with).",
    "S56": "Opt-in advisory, Structure Quality coupling: a unit is called through its entry point or the shared kernel, units form no import cycle, and a library names no consumer the project declares (waive as the path or unit a finding opens with).",
    "S57": "Opt-in advisory, Structure Quality reuse: code copied between files stays under the duplication budget (waive as the path a finding opens with).",
    "S58": "Opt-in advisory, Structure Quality public surface: a unit exports names that other units use (waive as the unit a finding opens with).",
    "S59": "Opt-in advisory, Structure Quality behavior preserved: a solution with several arms has a contract test or shared cases that run every arm (waive as the solution id a finding opens with).",
}


def assess_path(path: Path, stage: int = 1, flow: bool = True) -> Dict[str, Any]:
    """The Structure Quality report of a path, with the coherence gate's report when the path has an ``esoi.toml`` to read it from and ``flow`` is
    true (the flow dimension costs most of the time on a large project; without it the dimension is reported as not measured)."""
    path = Path(path)
    coherence: Optional[Dict[str, object]] = None
    if flow and (path / "esoi.toml").is_file():
        from esoi.structure.structure_check import coherence as coherence_module
        try:
            coherence = coherence_module.check(path, pairs=False)
        except Exception as exc:   # records that cannot be read leave the flow dimension unmeasured; the report says so by showing no score
            coherence = None
            print(f"esoi structure-quality: the flow dimension is not measured ({exc})")
    return assess.assess(str(path), stage, coherence=coherence)


def compare_refs(before: str, after: str, repo: str = ".", stage: int = 1, flow: bool = True) -> Dict[str, Any]:
    """The Structure Quality comparison of two structures, each a folder or a git reference of ``repo`` (see ``esoi.structure.structure_quality.compare``)."""
    from esoi.structure.structure_quality.interface import compare
    return compare.compare(before, after, lambda folder, level: assess_path(folder, level, flow), repo, stage)


def findings(ctx: Context) -> List[str]:
    wanted = [rule for rule in DIMENSION_OF if ctx.config.enabled(rule)]
    if not wanted:
        return []
    report = assess.assess(str(ctx.root), 1)
    out: List[str] = []
    for rule in wanted:
        offenders = [t for t in report["dimensions"][DIMENSION_OF[rule]]["offenders"] if not ctx.waived(rule, t.split(":")[0].split(" ")[0])]
        out += [f"{rule} {t}; next: {NEXT[rule]}" for t in offenders[:SHOWN]]
        if len(offenders) > SHOWN:
            out.append(f"{rule} {len(offenders) - SHOWN} more findings of {DIMENSION_OF[rule]}, worst first above; next: `esoi structure-quality` lists the worst of every dimension")
    return out


def run(ctx: Context) -> List[str]:
    ctx.advisory.extend(findings(ctx))
    return []


GROUP = RuleGroup(SUMMARIES, run)
