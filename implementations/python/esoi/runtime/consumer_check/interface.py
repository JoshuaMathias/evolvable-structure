"""The interface of ConsumerChecking: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Any, Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution


@solution("consumer-check", kind="event", entry="known_ids", example="esoi")
@runtime_checkable
class ConsumerChecking(Protocol):
    """The solution ids a consumer's registry may name for a library: how many the library defines."""

    def known_ids(self, library: str) -> Dict[str, Any]: ...


@implementation("consumer-check", "consumer-command")
class ConsumerCommand:
    """The consumer check that reads the library's own records or selection snapshot."""

    def known_ids(self, library: str) -> Dict[str, Any]:
        from esoi.runtime.consumer_check import consumer
        ids, full = consumer.known_solution_ids(consumer.Options(library=library))
        return {"solutions": len(ids), "from_records": full}
