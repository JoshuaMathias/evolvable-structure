"""The interface of Understanding: a Protocol declared with ``@solution``. Importing this module runs nothing."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import solution


@solution("esoi-understanding", kind="evaluate", entry="review", example=".")
@runtime_checkable
class Understanding(Protocol):
    """How ESOI reaches the people and agents who apply it: one read-only report from each of its parts, in the order the work happens."""

    def review(self, project: str) -> Dict[str, Any]: ...
