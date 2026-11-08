"""From a change, a candidate or a request to one generated prompt per solution it concerns, and one per parent level.

Which solutions a text concerns is Solution Relevance's answer (``esoi.understanding.solution_relevance``); the parent of each is
added after them, so the scope above each relevant solution gets its own pass too. No model is called here: a caller runs one pass
per returned prompt.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence

from esoi.runtime.implementation_selection.declare import implementation, solution

from esoi.understanding.solution_consideration import solution_prompt
from esoi.understanding.solution_relevance.relevance import DEFAULT_LIMIT, ranked as relevance_ranked


def with_parents(network: solution_prompt.Network, ranked: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The ranked solutions with the parent of each added after them (once), marked ``role`` ``parent``."""
    out = [{**s, "role": "solution"} for s in ranked]
    seen = {s["solution_id"] for s in out}
    for found in list(out):
        parent = solution_prompt.parent_of(network, found["solution_id"])
        if parent and parent not in seen and parent in network.solutions:
            seen.add(parent)
            out.append({"solution_id": parent, "score": 0.0, "via": [found["solution_id"]], "role": "parent"})
    return out


def classify(network: solution_prompt.Network, index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT,
             arm: str = "", parents: bool = True) -> List[Dict[str, Any]]:
    """The solutions a text concerns, best first, then their parents."""
    found = relevance_ranked(index, text, limit, arm)
    return with_parents(network, found) if parents else [{**s, "role": "solution"} for s in found]


def consider(network: solution_prompt.Network, index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT,
             budget: int = solution_prompt.DEFAULT_BUDGET, arm: str = "", only: Sequence[str] = ()) -> Dict[str, Any]:
    """One prompt per relevant solution and per parent level, as plain data a caller runs one pass each with. ``only`` names the
    solutions directly instead of classifying the text."""
    found = ([{"solution_id": s, "score": 0.0, "via": [], "role": "solution"} for s in only] if only
             else classify(network, index, text, limit, arm))
    if only:
        found = with_parents(network, found)
    prompts = []
    for item in found:
        made = solution_prompt.prompt(network, item["solution_id"], text, budget, item["role"])
        prompts.append({**made, "score": item["score"], "reached_by": item["via"]})
    return {"input": text, "arm": "named" if only else (arm or "selected"), "index_digest": index.get("digest", ""), "budget": budget,
            "prompts": prompts}


@solution("solution-consideration", kind="event", example={"project": ".", "solution_id": ""})
def consider_solution(project: str, solution_id: str = "", task: str = "", budget: int = 0) -> Dict[str, Any]:
    """The prompt for one solution's own consideration in the repository at ``project`` (the first solution when none is named)."""


@implementation("solution-consideration", "network_tiered")
def network_tiered(project: str, solution_id: str = "", task: str = "", budget: int = 0) -> Dict[str, Any]:
    """Every record connected to the solution, by tier within the budget: definition, results and selection first, then problems,
    ideals, metric, findings, evidence and implementations, then the parent, children, dependencies and dependents."""
    from esoi.structure.intent_registry import config as config_module
    config = config_module.load(Path(project))
    network = solution_prompt.load(config, stale=False)
    sid = solution_id or next(iter(network.solutions), "")
    return solution_prompt.prompt(network, sid, task, solution_prompt.budget_of(config, budget))
