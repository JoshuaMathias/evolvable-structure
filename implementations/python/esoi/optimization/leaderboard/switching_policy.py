"""How one solution is judged: the project and solution switching requirements (alpha, minimum cases, required stage, required significance) and the holdout fraction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from esoi.optimization.leaderboard import stats
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import Registry, first_arm
from esoi.optimization.leaderboard.results_log import Row


ALPHA = stats.ALPHA


@dataclass(frozen=True)
class Policy:
    """How one solution is judged. The default: a rival with a higher result on the authoritative metric replaces the selected arm,
    and the verdict says whether that lead is significant (two-sided paired test, ``alpha`` 0.05 divided by the looks at the pair, Holm across rivals) or a best guess.
    A project or a solution may opt into a stricter policy: ``require_significance`` (the selected arm stays until a rival is
    significantly better), a lower ``alpha``, a minimum number of shared cases (``min_cases``) and a cascade stage that must have been
    reached (``require_stage``, applied when promoting). ``origin`` says which level (``project`` or ``solution``) set each
    requirement, so a verdict can name it."""
    alpha: float = ALPHA
    min_cases: int = 0
    require_stage: str = ""
    require_significance: bool = False
    origin: Tuple[Tuple[str, str], ...] = ()
    holdout: float = 0.0   # [selection] holdout: the share of each case set kept out of the choice; claims are computed on it alone

    def source(self, key: str) -> str:
        return dict(self.origin).get(key, "configuration")


STRICTER_KEYS = ("alpha", "min_cases", "require_stage", "require_significance", "best_guess_switch")


def policy_for(config: Config, solution_id: str, component: str = "", per_case: Optional[List[Row]] = None) -> Policy:
    """The solution's policy from ``[switching]`` (the project) and ``[switching.<solution id>]`` (the solution, which overrides the
    project) in the configuration. Only stricter requirements count: an ``alpha`` above 0.05 is read as 0.05 and a negative
    ``min_cases`` as none. ``best_guess_switch = false`` is a deprecated alias of ``require_significance = true``; ``true`` changes
    nothing. ``component`` and ``per_case`` are accepted for older callers and unused."""
    table = getattr(config, "switching", {}) or {}
    project = {k: v for k, v in table.items() if k in STRICTER_KEYS}
    solution = table.get(solution_id, {}) if isinstance(table.get(solution_id), dict) else {}
    chosen, origin = {}, []
    for level, found in (("project", project), ("solution", solution)):
        for key, value in found.items():
            if key == "best_guess_switch":
                key, value = "require_significance", not bool(value)
            if key in STRICTER_KEYS:
                chosen[key] = value
                origin.append((key, level))
    return Policy(alpha=min(float(chosen.get("alpha", ALPHA)), ALPHA), min_cases=max(int(chosen.get("min_cases", 0)), 0),
                  require_stage=str(chosen.get("require_stage", "")),
                  require_significance=bool(chosen.get("require_significance", False)), origin=tuple(origin),
                  holdout=holdout_fraction(config))


def holdout_fraction(config: Config) -> float:
    """``[selection] holdout`` as a fraction between 0 and 1 (0, the default, keeps no case out: every claim is on the cases the choice used)."""
    table = getattr(config, "selection", None)
    try:
        value = float(table.get("holdout", 0)) if isinstance(table, dict) else 0.0
    except (TypeError, ValueError):
        return 0.0
    return value if 0 < value < 1 else 0.0


def policies(config: Config, registry: Registry, per_case: Optional[List[Row]]) -> Dict[str, Policy]:
    """``{component: Policy}`` for every evaluated solution."""
    out: Dict[str, Policy] = {}
    for row in registry.solutions:
        component, _ = first_arm(config, row.get("metric_command", ""))
        if component:
            out.setdefault(component, policy_for(config, row["solution_id"], component, per_case))
    return out
