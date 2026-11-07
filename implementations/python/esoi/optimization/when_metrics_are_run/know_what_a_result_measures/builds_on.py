"""The foundations a metric builds on (``[builds_on]``): what a consumer component declares, the foundation arm an arm names, and whether a row built on a foundation
is stale because the foundation changed (``stale_reason``). The run that composes the parts is ``esoi.optimization.measurement_harness.foundation_parts``; the
stage gate a consumer inherits is ``esoi.optimization.leaderboard.inherited_gate``. Nothing here knows any particular library.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from esoi.optimization.leaderboard import case_identity
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.code_changed import code_changed_reason
from esoi.runtime.implementation_selection import variants
from esoi.structure.intent_registry import config as config_module
from esoi.structure.intent_registry.config import Config

ON_STALE = ("run", "report")


@dataclass(frozen=True)
class Foundation:
    component: str      # the consumer's component
    name: str           # what the consumer calls this foundation
    root: Path          # the foundation's repository
    target: str         # the foundation's component
    share: float
    on_stale: str = "run"
    arm_prefix: str = ""   # the consumer's arms named <prefix><foundation arm> ARE that foundation arm (they delegate to it without adding code)


def declared(config: Config, component: str = "") -> List[Foundation]:
    """The foundations a component builds on, from ``[builds_on.<component>.<name>]`` (every component when none is named)."""
    out: List[Foundation] = []
    for comp, table in (config.builds_on or {}).items():
        if component and comp != component:
            continue
        for name, entry in (table or {}).items():
            out.append(Foundation(comp, name, (config.root / str(entry.get("repo", ""))).resolve(), str(entry.get("component", "")),
                                  float(entry.get("share", 0)), str(entry.get("on_stale", "run")), str(entry.get("arm_prefix", ""))))
    return out


def problems(config: Config) -> List[str]:
    """What is wrong with the ``[builds_on]`` tables: a missing repository or component, a share outside (0, 1) or shares that leave the
    consumer's own cases nothing, an unknown ``on_stale``, a consumer component that does not exist."""
    out: List[str] = []
    for comp in sorted({f.component for f in declared(config)}):
        mine = declared(config, comp)
        if not (config.evaluation / comp / "score.py").is_file():
            out.append(f"builds_on.{comp}: the consumer has no component {comp} (no {config.evaluation_dir}/{comp}/score.py)")
        if sum(f.share for f in mine) >= 1:
            out.append(f"builds_on.{comp}: the shares add up to {sum(f.share for f in mine):g}, so the consumer's own cases carry nothing (they must stay below 1)")
        for f in mine:
            out.extend(foundation_problems(f, f"builds_on.{comp}.{f.name}"))
    return out


def foundation_problems(f: "Foundation", tag: str) -> List[str]:
    """What is wrong with one declared foundation: its share, its stale policy and whether its results can be read."""
    out: List[str] = []
    if not 0 < f.share < 1:
        out.append(f"{tag}: share {f.share:g} is not between 0 and 1")
    if f.on_stale not in ON_STALE:
        out.append(f"{tag}: on_stale {f.on_stale!r} is not one of {', '.join(ON_STALE)}")
    if not (f.root / config_module.CONFIG_NAME).is_file() and not (f.root / "pyproject.toml").is_file():
        out.append(f"{tag}: {f.root.name} has no esoi configuration, so its results cannot be read")
    elif not (f.root / "evaluation" / "components" / f.target / "score.py").is_file() and not has_score(f):
        out.append(f"{tag}: {f.root.name} has no component {f.target}")
    return out


def has_score(f: Foundation) -> bool:
    try:
        return (load_config(f).evaluation / f.target / "score.py").is_file()
    except config_module.ConfigError:
        return False


def load_config(f: Foundation) -> Config:
    return config_module.load(f.root)


def declared_arms(config: Config, component: str, impl: str) -> Dict[str, str]:
    """{foundation name: foundation arm} an arm names with ``FOUNDATION_ARMS = {...}`` (or ``FOUNDATION_ARM = "x"`` for a single foundation)."""
    path = config.evaluation / component / "impls" / f"{variants.base_of(impl)}.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    found: Dict[str, str] = {}
    names = [f.name for f in declared(config, component)]
    for node in tree.body:
        found.update(assigned_arms(node, names))
    base = variants.base_of(impl)
    for f in declared(config, component):   # a configured prefix names the arm when the module declares nothing for this foundation
        if f.arm_prefix and f.name not in found and base.startswith(f.arm_prefix) and len(base) > len(f.arm_prefix):
            found[f.name] = base[len(f.arm_prefix):]
    return found


def literal_or_none(node: ast.AST) -> Any:
    """The literal value of an expression, or None when it is computed."""
    try:
        return ast.literal_eval(node)
    except ValueError:
        return None


def assigned_arms(node: ast.AST, names: List[str]) -> Dict[str, str]:
    """The foundation arms one module-level statement declares (``FOUNDATION_ARMS`` or the single ``FOUNDATION_ARM``), or none."""
    if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
        return {}
    value = literal_or_none(node.value)
    target = node.targets[0].id
    if target == "FOUNDATION_ARMS" and isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if target == "FOUNDATION_ARM" and isinstance(value, str) and len(names) == 1:
        return {names[0]: value}
    return {}


def identity(f: Foundation, arm: str, git_sha: str, cases_sha: str) -> str:
    return f"{f.name}={f.target}:{arm}@{git_sha}/{cases_sha}"


def parse_identity(cell: str) -> List[Tuple[str, str, str, str, str]]:
    """``(name, component, arm, git_sha, cases_sha)`` for each entry of a row's ``builds_on`` cell."""
    out = []
    for part in (cell or "").split(";"):
        try:
            name, rest = part.split("=", 1)
            target, rest = rest.split(":", 1)
            arm, rest = rest.rsplit("@", 1)
            sha, cases = rest.split("/", 1)
        except ValueError:
            continue
        out.append((name, target, arm, sha, cases))
    return out


def code_reason(fconf: Config, target: str, arm: str, git_sha: str, cases_sha: str) -> str:
    """Why a foundation arm measured at ``git_sha`` on ``cases_sha`` no longer describes the foundation, or an empty string."""
    now = case_identity.cases_digest(target, fconf.evaluation)
    if cases_sha != now:
        return f"the foundation's cases changed (measured on {cases_sha or 'blank'}, now {now})"
    if not git_sha:
        return "the foundation's code has no known commit"
    if git_sha.endswith("-dirty"):
        return "it was measured on uncommitted foundation code"
    return code_changed_reason(fconf, target, {"impl": arm, "git_sha": git_sha})


def stale_reason(config: Config, component: str, row: Dict[str, str]) -> str:
    """Why a composed row no longer counts because a foundation it builds on changed, or an empty string (a row that builds on nothing)."""
    cell = row.get("builds_on", "")
    if not cell:
        return ""
    known = {f.name: f for f in declared(config, component)}
    for name, target, arm, sha, cases in parse_identity(cell):
        f = known.get(name)
        if f is None:
            return f"its row builds on {name!r}, which [builds_on.{component}] no longer declares"
        if why := code_reason(load_config(f), target, arm, sha, cases):
            return f"the foundation {name} changed since this row was composed: {why}"
    return ""
