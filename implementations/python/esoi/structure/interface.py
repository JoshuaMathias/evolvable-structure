"""The interface of Structuring: a Protocol declared with ``@solution``. Importing this module runs nothing."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import solution


@solution("esoi-structure", kind="evaluate", entry="review", example=".")
@runtime_checkable
class Structuring(Protocol):
    """The project's records and code as one true and lean structure: one read-only report from each of its parts, in the order the work happens."""

    def review(self, project: str) -> Dict[str, Any]: ...
