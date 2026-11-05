"""Turn a closure's requirements into an install plan, walking the resolution ladder (resolver, alternatives, another arm, isolation, stop) when declarations conflict."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from esoi.runtime.assemble_by_name.environment_needs.checking import MET, check
from esoi.runtime.assemble_by_name.environment_needs.declarations import Binary, Download, Entry, Isolate, Network, Python, SCRIPT_ROLES, ScriptFile
from esoi.runtime.assemble_by_name.installation.command_running import tail
from esoi.runtime.assemble_by_name.installation.conflicts import Conflict, arm_of, find_conflicts, installed_constraints, merged_specs, needs_install
from esoi.runtime.assemble_by_name.installation.plan import Fallback, Isolated, Plan, Substitution
from esoi.runtime.assemble_by_name.installation.resolvers import Resolver


def trial(entries: Sequence[Entry], resolver: Optional[Resolver], with_constraints: bool = True) -> Tuple[List[Conflict], List[str]]:
    """Conflicts of the entries: the offline intersection, then (when a resolver is given) pip's dry run, first with the
    installed versions as constraints and, if that fails, without them. Returns the conflicts and the ladder log lines."""
    log: List[str] = []
    conflicts = find_conflicts(entries)
    if conflicts or resolver is None:
        return conflicts, log
    specs = merged_specs(needs_install(entries))
    if not specs:
        return [], log
    kept = installed_constraints(entries) if with_constraints else []
    outcome = resolver(specs, kept)
    if outcome.code and kept:
        log.append("resolver: failed with the installed versions as constraints; retrying without them")
        outcome = resolver(specs, [])
    if outcome.code:
        return [Conflict("(resolver)", ((" ".join(specs), ()),), tail(outcome.output, {}, 8) or "pip could not resolve the set")], log
    return [], log


def options_for(conflicts: Sequence[Conflict]) -> List[str]:
    """Concrete choices for a person: which range to widen and which arm to deselect, per conflict."""
    out = []
    for one in conflicts:
        for spec, arms in one.pulls:
            if arms:
                out.append(f"widen {one.distribution} {spec or '(any)'} declared by {', '.join(arms)}, or deselect one of those arms "
                           f"(AssemblyConfig names={{...}} / esoi select)")
        if not any(arms for spec, arms in one.pulls):
            out.append(f"run `python -m pip install --dry-run {one.distribution}` to see which requirement pip rejects")
    return list(dict.fromkeys(out))


def alternatives_step(entries: Sequence[Entry], conflicts: Sequence[Conflict], resolver: Optional[Resolver],
                      steps: List[str]) -> Optional[List[Entry]]:
    """Ladder step 2: swap a conflicting declaration for one of its declared alternatives; the first swap that leaves no conflict wins."""
    keys = {re.sub(r"[-_.]+", "-", one.distribution).lower() for one in conflicts}
    for index, entry in enumerate(entries):
        item = entry.requirement
        if not isinstance(item, Python) or item.parsed.key not in keys:
            continue
        for alternative in item.alternatives:
            swapped = list(entries)
            swapped[index] = replace(entry, requirement=replace(item, distribution=alternative, alternatives=()))
            remaining, log = trial(swapped, resolver)
            if not remaining:
                steps.append(f"2. alternatives: {item.module} uses {alternative} instead of {item.distribution}; no conflict")
                return swapped
    steps.append("2. alternatives: none of the declared alternatives resolves the conflict" if any(
        isinstance(e.requirement, Python) and e.requirement.alternatives for e in entries) else "2. alternatives: none declared")
    return None


def isolate_step(entries: Sequence[Entry], conflicts: Sequence[Conflict], project: Path,
                 steps: List[str]) -> Optional[Tuple[List[Entry], List[Isolated]]]:
    """Ladder step 4: move the python requirements of an arm that declares ``isolatable`` into a virtual environment of its own."""
    boundaries: Dict[str, str] = {}
    for entry in entries:
        if isinstance(entry.requirement, Isolate):
            for label in entry.used_by:
                boundaries[arm_of(label)] = entry.requirement.boundary
    pulled = {arm for one in conflicts for spec, arms in one.pulls for arm in arms}
    for arm in sorted(pulled):
        if arm not in boundaries:
            continue
        own = [e for e in entries if isinstance(e.requirement, Python) and arm in {arm_of(label) for label in e.used_by}]
        rest = [e for e in entries if e not in own]
        if not own or find_conflicts(rest):
            continue
        folder = str(project / ".esoi" / "venvs" / re.sub(r"[^A-Za-z0-9_.-]+", "-", arm))
        steps.append(f"4. isolate: {arm} installs in its own environment at {folder} and is reached through its {boundaries[arm]} boundary")
        return rest, [Isolated(arm, boundaries[arm], folder, tuple(merged_specs(own)))]
    steps.append("4. isolate: no conflicting arm declares isolatable(...)")
    return None


def make_plan(entries: Sequence[Entry], environ: Mapping[str, str], resolver: Optional[Resolver] = None,
              fallback: Optional[Fallback] = None, project: Optional[Path] = None, notes: Sequence[str] = ()) -> Plan:
    """The install plan for the entries, with the resolution ladder applied when they conflict (see the module docstring).
    Nothing already satisfied is reinstalled; nothing is changed."""
    steps: List[str] = []
    substitutions: List[Substitution] = []
    isolated: List[Isolated] = []
    current = list(entries)
    conflicts, log = trial(current, resolver)
    steps += log
    steps.append("1. resolver: the merged ranges coexist" if not conflicts else
                 "1. resolver: " + "; ".join(one.text() for one in conflicts))
    if conflicts:
        swapped = alternatives_step(current, conflicts, resolver, steps)
        if swapped is not None:
            current, conflicts = swapped, []
    if conflicts and fallback is not None:
        found = fallback(conflicts, current)
        if found is not None:
            substitutions.append(found[0])
            current = found[1]
            conflicts, log = trial(current, resolver)
            steps.append("3. another arm: " + found[0].text())
        else:
            steps.append("3. another arm: no compatible arm among the seat's alternatives")
    elif conflicts:
        steps.append("3. another arm: not available here (no assembly to choose from)")
    if conflicts:
        moved = isolate_step(current, conflicts, project or Path.cwd(), steps)
        if moved is not None:
            current = moved[0]
            isolated += moved[1]
            conflicts = find_conflicts(current)
    if conflicts:
        steps.append("5. stop: no step resolved the conflict; nothing will be installed")
    scripts: List[Tuple[str, str]] = []
    binaries: List[str] = []
    missing: List[str] = []
    for entry, one in zip(current, check(current, environ)):
        item = entry.requirement
        if isinstance(item, ScriptFile):
            scripts.append((item.role, item.path))
        elif isinstance(item, Binary) and one.status != MET:
            binaries.append(f"{item.name}: {one.remedy}")
        elif one.blocking and not isinstance(item, (Python, Network)):
            missing.append(f"{item.label}: {one.remedy}")
        elif isinstance(item, Download) and one.failing:
            missing.append(f"{item.label}: {one.remedy}")
    order = {role: position for position, (name, role) in enumerate(SCRIPT_ROLES)}
    scripts.sort(key=lambda pair: (str(Path(pair[1]).parent), order.get(pair[0], 9)))
    pip = () if conflicts else tuple(merged_specs(needs_install(current)))
    constraints = tuple(installed_constraints(current)) if pip else ()
    return Plan(pip, constraints, tuple(scripts), tuple(isolated), tuple(substitutions), tuple(steps),
                tuple(one.text() for one in conflicts), tuple(options_for(conflicts)), tuple(binaries), tuple(missing), tuple(notes))
