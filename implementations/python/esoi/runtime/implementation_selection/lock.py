"""Pin the selected implementations, see what a newer release would change, and move on your schedule.

By default a consumer follows the latest selections: when the metric picks a better implementation and a new release ships it,
the consumer gets it. That is the point of ESOI, and it is the default. A consumer with production end users can instead record
the selections it runs with in a lock file and decide when to move::

    from esoi import lock

    lock.write(assembler, "esoi.lock.json")                      # record the current selection of every solution
    changes = lock.diff(assembler, "esoi.lock.json")             # what would change, with evidence and requirement changes
    lock.update(assembler, "esoi.lock.json", safe=True)          # move only what adds no unmet requirement
    parts.assemble(AssemblyConfig(lock="esoi.lock.json"))        # build with the locked arms

The lock is a layer between the consumer's own selections and the package defaults (``AssemblyConfig.lock``, shown as ``lock``
by ``explain``). It holds, per solution, the selected arm with the scope that chose it, the verdict and p-value of the evidence
at that time, and the requirements of the arm's closure (``esoi.runtime.assemble_by_name.environment_needs``); and the version of each package in the chain.
A locked arm that the package no longer lists raises ``LockError`` naming the remedy.

``diff`` reports, per solution whose latest selection differs from the lock, the old arm, the new arm, the verdict and p, and the
requirement changes between the two closures (variables and API keys, python packages, binaries, services, downloads), each
added requirement with whether the current environment already meets it (no values are ever printed). ``update`` moves the lock
to the latest selections; with ``safe=True`` (or ``"update": "safe"`` in the lock file) it moves only the solutions whose new
closure adds no unmet requirement and leaves the rest locked. ``status`` is the plan an AI agent acts on: stable exit codes and a
versioned JSON listing each blocked update, its unmet requirements, the remedy steps in order and the one command that applies
it once they are resolved.

Standard library and ``esoi`` only. No variable's value ever appears in anything this module returns.
"""
from __future__ import annotations

import importlib.metadata
import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi.optimization.leaderboard.interface import lock_evidence_attach_evidence, lock_evidence_records_evidence
from esoi.runtime.assemble_by_name.interface import Assembler, AssemblyConfig, lock_file_CACHE, lock_file_SCHEMA, lock_file_locked_arm, lock_file_read, MET, check, members_pairs, Entry, gather, identity
from esoi.structure.intent_registry.interface import LockError

read, locked_arm, CACHE, SCHEMA = lock_file_read, lock_file_locked_arm, lock_file_CACHE, lock_file_SCHEMA
records_evidence, attach_evidence = lock_evidence_records_evidence, lock_evidence_attach_evidence

__all__ = ["LockError", "Change", "Result", "SCHEMA", "STATUS_SCHEMA", "DEFAULT_FILE", "write", "update", "diff", "status", "read",
           "latest", "locked_arm", "records_evidence", "EXIT_CURRENT", "EXIT_ERROR", "EXIT_SAFE", "EXIT_BLOCKED"]

STATUS_SCHEMA = "esoi.runtime.implementation_selection.lock.status/1"
DEFAULT_FILE = "esoi.lock.json"
POLICIES = ("latest", "safe")
EXIT_CURRENT, EXIT_ERROR, EXIT_SAFE, EXIT_BLOCKED = 0, 2, 3, 4   # esoi lock --status


# the latest selections

@dataclass
class Selected:
    """The latest selection of one solution: the record the lock stores, and the requirement entries it came from."""
    record: Dict[str, Any]
    entries: List[Entry] = field(default_factory=list)


def neutral(config: Optional[AssemblyConfig]) -> AssemblyConfig:
    """The configuration with only the package defaults left: no lock, no consumer names, selections or environ choices."""
    return replace(config or AssemblyConfig(), lock=None, names={}, selections={}, selection_environ={}, reasons={})


def requirement_record(entry: Entry) -> Dict[str, Any]:
    item = entry.requirement
    return {"id": ":".join(identity(item)), "kind": item.kind, "label": item.label, "required": bool(item.required)}


def package_versions(assembler: Assembler) -> Dict[str, str]:
    out = {}
    for one in assembler.chain():
        try:
            out[one.scope] = importlib.metadata.version(one.scope)
        except importlib.metadata.PackageNotFoundError:
            out[one.scope] = "unversioned"
    return out


def latest(assembler: Assembler, config: Optional[AssemblyConfig] = None, solutions: Sequence[str] = ()) -> Dict[str, Selected]:
    """The selection each solution would have now with no lock and no consumer choices, with the evidence of the scope that chose
    it and the requirements of the arm's closure. A solution with no default arm (the consumer supplies it) is left out."""
    base = neutral(config)
    assembler.prepare()
    chain = [one.scope for one in assembler.chain()]
    wanted = list(solutions or base.solutions or assembler.visible())
    out: Dict[str, Selected] = {}
    for sid in wanted:
        assembler.check_solution(sid)
        winner = assembler.layers(sid, None, base).winner
        if winner is None:
            continue
        out[sid] = selected_from(assembler, base, sid, winner, chain)
    return out


def selected_from(assembler: Assembler, base: AssemblyConfig, sid: str, winner: Any, chain: List[str]) -> Selected:
    """The ``Selected`` record for a solution's winning layer: its arm, evidence and the requirements of its closure."""
    holder = next((one for one in assembler.chain() if one.scope == winner.scope), assembler)
    found = dict(holder.packaged().evidence.get(sid, {}))
    entries = gather(members_pairs(assembler.closure(base, None, (sid,))))
    return Selected({"arm": winner.name, "scope": winner.scope or assembler.scope, "chain": chain,
                     "verdict": found.get("verdict", ""), "p": found.get("p"),
                     "evidence": found.get("detail") or f"the default of {winner.scope or assembler.scope} ({winner.source}); no results recorded for it",
                     "requirements": [requirement_record(e) for e in entries]}, entries)


def dump(path: Any, data: Mapping[str, Any]) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    CACHE.clear()


def write(assembler: Assembler, path: Any = DEFAULT_FILE, config: Optional[AssemblyConfig] = None, solutions: Sequence[str] = (),
          update_policy: Optional[str] = None) -> Dict[str, Any]:
    """Record the current selection of every solution (or of ``solutions``) in ``path`` and return what was written. An existing
    lock's ``update`` policy is kept unless ``update_policy`` (``"latest"`` or ``"safe"``) is given."""
    chosen = latest(assembler, config, solutions)
    policy = update_policy
    if policy is None and Path(path).is_file():
        try:
            policy = read(path).get("update")
        except LockError:
            policy = None
    if policy not in (None, *POLICIES):
        raise LockError(f"update policy {policy!r} is not one of {', '.join(POLICIES)}")
    data: Dict[str, Any] = {"schema": SCHEMA, "scope": assembler.scope, "packages": package_versions(assembler),
                            "solutions": {sid: item.record for sid, item in sorted(chosen.items())}}
    if policy:
        data["update"] = policy
    dump(path, data)
    return data


# what would change

def added_line(a: Dict[str, Any]) -> str:
    """The report line for one added requirement."""
    return f"    + {a['label']}{'' if a['required'] else ' (optional)'}: {a['status']}" + (f"; {a['remedy']}" if a.get("remedy") and a["status"] != MET else "")


@dataclass
class Change:
    """One solution whose latest selection differs from the lock. ``added`` and ``removed`` are the requirement changes between the
    two closures; each added one carries ``status`` (met, unmet or unknown in the current environment) and the ``remedy``."""
    solution: str
    old_arm: str
    new_arm: str
    verdict: str = ""
    p: Optional[float] = None
    evidence: str = ""
    added: List[Dict[str, Any]] = field(default_factory=list)
    removed: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def unmet(self) -> List[Dict[str, Any]]:
        return [a for a in self.added if a.get("failing")]

    @property
    def safe(self) -> bool:
        """Whether the new closure adds no unmet requirement."""
        return not self.unmet

    def to_dict(self) -> Dict[str, Any]:
        return {"solution": self.solution, "old_arm": self.old_arm, "new_arm": self.new_arm, "verdict": self.verdict, "p": self.p,
                "evidence": self.evidence, "safe": self.safe, "requirements_added": self.added, "requirements_removed": self.removed}

    def lines(self) -> List[str]:
        move = f"{self.old_arm or '(not locked)'} -> {self.new_arm or '(no longer selected)'}"
        p = f", p={self.p:.3g}" if self.p is not None else ""
        out = [f"{self.solution}: {move}  [{self.verdict or 'no verdict'}{p}]" + ("" if self.safe else "  BLOCKED by unmet requirements")]
        if self.evidence:
            out.append(f"    evidence: {self.evidence}")
        out.extend(added_line(a) for a in self.added)
        for r in self.removed:
            out.append(f"    - {r['label']}")
        return out


def environment(config: Optional[AssemblyConfig], environ: Optional[Mapping[str, str]]) -> Dict[str, str]:
    if environ is not None:
        return dict(environ)
    given = dict(config.consumer_environ) if config is not None and config.consumer_environ else {}
    return given or dict(os.environ)


def diff(assembler: Assembler, source: Any, config: Optional[AssemblyConfig] = None, solutions: Sequence[str] = (),
         environ: Optional[Mapping[str, str]] = None) -> List[Change]:
    """The solutions whose latest selection differs from the lock, in solution order. A solution the lock lacks has no old arm;
    one the package no longer selects has no new arm. Requirement changes compare the lock's recorded closure with the new one."""
    data = read(source)
    now = latest(assembler, config, solutions)
    env = environment(config, environ)
    out: List[Change] = []
    for sid in sorted(set(data["solutions"]) | set(now)):
        if solutions and sid not in solutions:
            continue
        old, new = data["solutions"].get(sid), now.get(sid)
        if old and new and old["arm"] == new.record["arm"]:
            continue
        added, removed = requirement_changes(old, new, env)
        record = new.record if new else {}
        out.append(Change(sid, (old or {}).get("arm", ""), record.get("arm", ""), record.get("verdict", ""), record.get("p"),
                          record.get("evidence", ""), added, removed))
    return out


def requirement_changes(old: Optional[Dict[str, Any]], new: Optional[Selected], env: Mapping[str, str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """``(added, removed)`` requirement records between the lock's recorded closure and the new one; each added one carries its status."""
    known = {r["id"]: r for r in (old or {}).get("requirements", [])}
    entries = new.entries if new else []
    added = []
    for entry, one in zip(entries, check(entries, env) if new else []):
        rec = requirement_record(entry)
        if rec["id"] not in known:
            added.append({**rec, "status": one.status, "remedy": one.remedy, "failing": one.failing,
                          "used_by": list(entry.used_by), "secret": bool(getattr(entry.requirement, "secret", False)) or entry.requirement.kind == "api"})
    fresh = {requirement_record(e)["id"] for e in entries}
    return added, [r for rid, r in known.items() if rid not in fresh]


@dataclass
class Result:
    """What ``update`` did: the changes it applied, the ones it left locked because they add an unmet requirement, and the lock."""
    moved: List[Change]
    blocked: List[Change]
    data: Dict[str, Any]


def update(assembler: Assembler, path: Any = DEFAULT_FILE, config: Optional[AssemblyConfig] = None, solutions: Sequence[str] = (),
           safe: Optional[bool] = None, environ: Optional[Mapping[str, str]] = None) -> Result:
    """Move the lock to the latest selections (every solution, or ``solutions``). ``safe=True`` moves only the solutions whose new
    closure adds no unmet requirement and leaves the rest locked (they are in ``blocked`` with their remedies); ``safe=None`` follows
    the lock file's ``"update"`` policy (``"latest"`` when it has none)."""
    data = read(path)
    changes = diff(assembler, path, config, solutions, environ)
    policy_safe = data.get("update") == "safe" if safe is None else safe
    moved = [c for c in changes if c.safe or not policy_safe]
    blocked = [c for c in changes if c not in moved]
    if moved:
        now = latest(assembler, config, [c.solution for c in moved if c.new_arm])
        table = dict(data["solutions"])
        for change in moved:
            if change.new_arm:
                table[change.solution] = now[change.solution].record
            else:
                table.pop(change.solution, None)
        data = {**data, "solutions": dict(sorted(table.items())), "packages": package_versions(assembler)}
        dump(path, data)
    return Result(moved, blocked, data)


# the plan an AI agent acts on

def command(base: str, package: str, file: str, solution: str = "") -> str:
    """An ``esoi lock`` command line that names the same package and lock file as the caller."""
    return " ".join(x for x in (base, f"--package {package}" if package else "", f"--file {file}" if file != DEFAULT_FILE else "",
                                f"--solution {solution}" if solution else "") if x)


def environment_step(a: Dict[str, Any]) -> Dict[str, Any]:
    """The step that sets one unmet variable; a secret is a person's to obtain."""
    return {"action": "set-environment", "command": None, "human": bool(a.get("secret")), "requirement": a["id"],
            "detail": a["remedy"] or a["label"],
            "note": "a key is a person's to obtain: ask them, using the signup link in the detail" if a.get("secret") else ""}


def install_step(unmet: List[Dict[str, Any]], solution: str, package: str) -> List[Dict[str, Any]]:
    """The one step that installs the unmet python packages, or none."""
    if not any(a["kind"] == "python" for a in unmet):
        return []
    install = "esoi install" + (f" --package {package}" if package else "") + f" --solution {solution} --yes"
    return [{"action": "install-packages", "command": install, "human": False,
             "detail": "; ".join(a["remedy"] for a in unmet if a["kind"] == "python" and a["remedy"])}]


def remedy_steps(unmet: List[Dict[str, Any]], solution: str, package: str) -> List[Dict[str, Any]]:
    """The steps that meet the unmet requirements: packages, binaries, services, environment, then anything else."""
    steps: List[Dict[str, Any]] = []
    steps.extend(install_step(unmet, solution, package))
    for kind, action in (("binary", "install-binary"), ("service", "start-service")):
        steps.extend({"action": action, "command": None, "human": False, "detail": a["remedy"] or a["label"]} for a in unmet if a["kind"] == kind)
    steps.extend(environment_step(a) for a in unmet if a["kind"] in ("env", "api"))
    steps.extend({"action": "resolve", "command": None, "human": False, "detail": a["remedy"] or a["label"]}
                 for a in unmet if a["kind"] not in ("python", "binary", "service", "env", "api"))
    return steps


def steps_for(change: Change, package: str, file: str) -> List[Dict[str, Any]]:
    """The ordered remedy steps for one update: install what is missing, start services, set variables (asking a person for a key),
    apply the update, then verify."""
    steps = remedy_steps(change.unmet, change.solution, package)
    steps.append({"action": "apply", "command": command("esoi lock --update", package, file, change.solution), "human": False,
                  "detail": f"move {change.solution} from {change.old_arm or 'unlocked'} to {change.new_arm or 'unselected'}"})
    steps.append({"action": "verify", "command": "esoi requirements --check" + (f" --package {package}" if package else "") +
                  f" --solution {change.solution}", "human": False, "detail": "then run the consumer's own tests"})
    for number, step in enumerate(steps, 1):
        step["order"] = number
    return steps


def update_item(change: Change, package: str, file: str) -> Dict[str, Any]:
    """One available update as the plan lists it: the change, whether it is blocked, its unmet requirements, steps and apply command."""
    item = change.to_dict()
    item["blocked"] = not change.safe
    item["unmet"] = [{"id": a["id"], "label": a["label"], "kind": a["kind"], "remedy": a["remedy"]} for a in change.unmet]
    item["steps"] = steps_for(change, package, file)
    item["apply"] = command("esoi lock --update", package, file, change.solution)
    return item


def status(assembler: Assembler, source: Any, config: Optional[AssemblyConfig] = None, solutions: Sequence[str] = (),
           environ: Optional[Mapping[str, str]] = None, package: str = "", file: str = DEFAULT_FILE) -> Tuple[int, Dict[str, Any]]:
    """``(exit code, plan)``. Exit 0: up to date. 3: updates are available and every one is safe. 4: updates are available and at
    least one is blocked by an unmet requirement. The plan (schema ``esoi.runtime.implementation_selection.lock.status/1``) lists every update, its requirement
    changes, and for a blocked one the unmet requirements, the remedy steps in order and the single command that applies it."""
    changes = diff(assembler, source, config, solutions, environ)
    updates = [update_item(change, package, file) for change in changes]
    blocked = any(u["blocked"] for u in updates)
    code = EXIT_BLOCKED if blocked else EXIT_SAFE if updates else EXIT_CURRENT
    state = "blocked" if blocked else "safe-updates" if updates else "up-to-date"
    plan = {"schema": STATUS_SCHEMA, "lock": str(source) if not isinstance(source, Mapping) else "mapping", "state": state, "exit": code,
            "updates": updates}
    if any(not u["blocked"] for u in updates):
        plan["apply_safe"] = command("esoi lock --update --safe", package, file)
    return code, plan
