"""The interface of Optimizing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import solution


@solution("esoi-optimization", kind="evaluate", entry="review", example=".")
@runtime_checkable
class Optimizing(Protocol):
    """How a project comes to run the implementation the evidence shows is best: one read-only report from each of its parts, in the order the work happens."""

    def review(self, project: str) -> Dict[str, Any]: ...
