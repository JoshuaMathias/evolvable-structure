"""How many cases an evaluation component holds, for the solutions that are judged by labelled cases."""
from typing import Dict

from esoi.optimization.measurement_harness import case_loading
from esoi.structure.intent_registry.registry import load_project


def count_cases(project: str, component: str) -> Dict[str, int]:
    """``{"cases": n}``: the labelled cases of ``component`` in the project at ``project``; none when the project does not carry the component."""
    config, _ = load_project(project)
    try:
        return {"cases": len(case_loading.load_cases(component, config))}
    except (ImportError, FileNotFoundError):
        return {"cases": 0}
