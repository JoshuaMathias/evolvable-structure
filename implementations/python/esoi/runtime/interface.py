"""The interface of RuntimeServing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import solution


@solution("esoi-runtime", kind="evaluate", entry="review", example="structure-check")
@runtime_checkable
class RuntimeServing(Protocol):
    """How a better measurement changes what runs inside other people's programs: one read-only report from each of its parts, in the order the work happens."""

    def review(self, solution_id: str = "structure-check") -> Dict[str, Any]: ...
