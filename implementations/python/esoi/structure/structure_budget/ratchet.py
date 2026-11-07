"""The ratchet of rule S39: how a repository's own rule settings moved since a base commit. A trend report, never a failure.

It compares the working tree with a base commit and reports the direction of three things: the waivers of the opt-in rules
S36 to S38 (a waiver set that grew is debt added), the opt-in rules that are enabled (a rule that was on and is now off or
not enabled), and the floors and ceilings of ``[rules.S38]`` (a floor that fell or a ceiling that rose loosens the standard).
The base is, in order: the environment variable ``ESOI_RATCHET_BASE``; ``[rules.S39] base``; the merge-base of HEAD with the
upstream default branch when that is not HEAD itself; HEAD's first parent. A root commit has no base and reports nothing.
Files at the base are read with ``git show <base>:<path>``. Standard library only.
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

RULES = ("S36", "S37", "S38")                 # the opt-in rules whose waivers are counted
OPT_IN = ("S36", "S37", "S38", "S39")
FLOORS = (("code_floor", "precision"), ("coverage_floor", "coverage"), ("min_lift", "min_lift"))
CEILINGS = ("max_fan_out", "max_depth")
DEFAULT_FLOORS = {"code_floor": 1.0, "coverage_floor": 0.0, "min_lift": 1.0}
DEFAULT_CEILINGS = {"max_fan_out": 9, "max_depth": 4}
BASE_ENV = "ESOI_RATCHET_BASE"
NEEDS_HISTORY = ("the full history is needed (a CI checkout with fetch-depth: 0, or `git fetch --unshallow`), so the base "
                 "commit can be read")


@dataclass(frozen=True)
class Trend:
    """One thing compared with the base: its name, the base value and the value now, the direction, and whether that direction
    loosens the standard (``adverse``)."""
    what: str
    base: Any
    now: Any
    direction: str      # grew, shrank, rose, fell, unchanged, enabled, disabled
    adverse: bool = False

    def line(self) -> str:
        return f"S39 {self.what}: {self.base} -> {self.now} ({self.direction})"


def git(root: Path, *args: str) -> Tuple[int, str]:
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return 127, ""
    return done.returncode, done.stdout.strip()


def default_branch(root: Path) -> List[str]:
    code, head = git(root, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    named = [head] if code == 0 and head else []
    return named + ["origin/main", "origin/master", "main", "master"]


def merge_base_with_default(root: Path, head: str) -> Optional[str]:
    """The merge base of HEAD with the first default branch that exists and differs from HEAD."""
    for branch in default_branch(root):
        if git(root, "rev-parse", "--verify", "-q", f"{branch}^{{commit}}")[0] != 0:
            continue
        code, merged = git(root, "merge-base", "HEAD", branch)
        if code == 0 and merged and merged != head:
            return merged
    return None


def resolve_base(root: Path, configured: str = "") -> Tuple[Optional[str], str]:
    """``(base commit, note)``. ``base`` is None with a note: ``root commit`` (nothing to compare), or ``no base: ...``."""
    code, inside = git(root, "rev-parse", "--is-inside-work-tree")
    if code != 0 or inside != "true":
        return None, "no base: trend not computed (this is not a git repository; the ratchet compares with a base commit)"
    code, head = git(root, "rev-parse", "--verify", "-q", "HEAD^{commit}")
    if code != 0:
        return None, "no base: trend not computed (the repository has no commit yet)"
    named = os.environ.get(BASE_ENV, "").strip() or str(configured or "").strip()
    if named:
        code, found = git(root, "rev-parse", "--verify", "-q", f"{named}^{{commit}}")
        if code != 0:
            return None, f"no base: trend not computed (base {named!r} is not in this clone; {NEEDS_HISTORY})"
        return found, ""
    merged = merge_base_with_default(root, head)
    if merged:
        return merged, ""
    shallow = git(root, "rev-parse", "--is-shallow-repository")[1] == "true"
    code, parent = git(root, "rev-parse", "--verify", "-q", "HEAD~1")
    if code == 0 and parent:
        return parent, ""
    if shallow:
        return None, f"no base: trend not computed (shallow clone; {NEEDS_HISTORY})"
    return None, "root commit"


def show(root: Path, base: str, path: str) -> Optional[str]:
    code, text = git(root, "show", f"{base}:./{path}")
    return text if code == 0 else None


def rules_at(text: Optional[str], source: Path) -> Tuple[Dict[str, Any], Set[str]]:
    """``(the [rules] table, the disable list)`` of a configuration file's text."""
    if not text:
        return {}, set()
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}, set()
    if source.name == "pyproject.toml":
        data = data.get("tool", {}).get("esoi", {})
    return data.get("rules", {}) or {}, set(data.get("disable", []) or [])


def waivers_of(text: Optional[str]) -> Set[Tuple[str, str]]:
    if not text:
        return set()
    return {(r.get("rule", ""), r.get("path", "")) for r in csv.DictReader(io.StringIO(text)) if r.get("rule") in RULES}


def effective(rules: Dict[str, Any], intent: str) -> Dict[str, float]:
    table = rules.get("S38", {}) or {}
    out = dict(DEFAULT_FLOORS)
    out.update({k: table[k] for k in out if k in table})
    own = (table.get("floors", {}) or {}).get(intent, {})
    for flat, key in FLOORS:
        if key in own:
            out[flat] = own[key]
    return out


def effective_ceiling(rules: Dict[str, Any], intent: str, key: str) -> float:
    table = rules.get("S38", {}) or {}
    own = (table.get("floors", {}) or {}).get(intent, {})
    fan = own.get("max_fan_out", table.get("max_fan_out", DEFAULT_CEILINGS["max_fan_out"]))
    default = fan + 1 if key == "max_names_per_sentence" else fan
    if key == "max_names_per_sentence":
        return own.get(key, table.get(key, default))
    return own.get(key, table.get(key, DEFAULT_CEILINGS[key]))


def waiver_trends(config: Any, root: Path, base: str, was_on: Set[str]) -> List[Trend]:
    """The waivers of each rule that was enabled at the base, now against then."""
    from esoi.structure.intent_registry import intents
    folders = [i.folder for i in intents.discover(config)] if config.intent_mode else [config.structure]
    now: Set[Tuple[str, str]] = set()
    before: Set[Tuple[str, str]] = set()
    for folder in folders:
        rel = str(folder.relative_to(root)) + "/waivers.csv"
        if (folder / "waivers.csv").is_file():
            now |= waivers_of((folder / "waivers.csv").read_text(encoding="utf-8"))
        before |= waivers_of(show(root, base, rel))
    out: List[Trend] = []
    for rule in RULES:
        if rule not in was_on:
            continue   # the commit that first enables a rule sets its baseline
        a = sorted(p for r, p in before if r == rule)
        b = sorted(p for r, p in now if r == rule)
        direction = "grew" if len(b) > len(a) or set(b) - set(a) else "shrank" if len(b) < len(a) else "unchanged"
        added = sorted(set(b) - set(a))
        out.append(Trend(f"waivers of {rule}" + (f" (new: {', '.join(added[:8])}{'...' if len(added) > 8 else ''})" if added else ""),
                         len(a), len(b), direction, adverse=bool(added)))
    return out


def intent_limit_trends(base_rules: Dict[str, Any], config: Any, names: Set[str]) -> List[Trend]:
    """The floors, and the ceilings written for one intent, that changed since the base."""
    out: List[Trend] = []
    for intent in sorted(names):
        old, new = effective(base_rules, intent), effective(config.rules, intent)
        for flat, key in FLOORS:
            if old[flat] != new[flat]:
                out.append(Trend(f"floor {key} of {intent}", old[flat], new[flat], "rose" if new[flat] > old[flat] else "fell",
                                 adverse=new[flat] < old[flat]))
    for intent in sorted(names):   # a ceiling written for one intent in its floors table
        for key in ("max_fan_out", "max_names_per_sentence"):
            written = [((r.get("S38", {}) or {}).get("floors", {}) or {}).get(intent, {}) for r in (base_rules, config.rules)]
            if not any(key in w for w in written):
                continue
            old = effective_ceiling(base_rules, intent, key)
            new = effective_ceiling(config.rules, intent, key)
            if old != new:
                out.append(Trend(f"ceiling {key} of {intent}", old, new, "rose" if new > old else "fell", adverse=new > old))
    return out


def coherence_trends(base_rules: Dict[str, Any], config: Any) -> List[Trend]:
    """The floors and ceilings of [rules.S38] that changed since the base."""
    from esoi.structure.intent_registry import intents
    names = set((base_rules.get("S38", {}).get("floors", {}) or {})) | set((config.option("S38", "floors", {}) or {}))
    names |= {i.intent_id for i in intents.discover(config)} if config.intent_mode else set()
    out = intent_limit_trends(base_rules, config, names)
    for key in CEILINGS:
        old = (base_rules.get("S38", {}) or {}).get(key, DEFAULT_CEILINGS[key])
        new = config.option("S38", key, DEFAULT_CEILINGS[key])
        if old != new:
            out.append(Trend(f"ceiling {key}", old, new, "rose" if new > old else "fell", adverse=new > old))
    return out


def trend(config: Any) -> Tuple[List[Trend], str]:
    """The trend of the working tree against the base: ``(trends, note)``. ``note`` is non-empty when no trend could be computed."""
    root = Path(config.root)
    base, note = resolve_base(root, config.option("S39", "base", ""))
    if base is None:
        return [], ("" if note == "root commit" else note)
    source = Path(config.source) if config.source else root / "esoi.toml"
    base_rules, base_disabled = rules_at(show(root, base, str(source.relative_to(root))) if source.is_absolute() else None, source)
    was_on = {r for r in OPT_IN if bool((base_rules.get(r, {}) or {}).get("enabled", False)) and r not in base_disabled}
    out = [Trend(f"rule {rule} enabled", "yes", "no", "disabled", adverse=True)
           for rule in OPT_IN if rule in was_on and not config.enabled(rule)]
    out += waiver_trends(config, root, base, was_on)
    if "S38" in was_on:
        out += coherence_trends(base_rules, config)
    return out, ""
