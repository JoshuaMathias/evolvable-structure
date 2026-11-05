"""A need that is built on first use: the ``Lazy[Protocol]`` annotation and the stand-in that builds the part on the first attribute read."""
from __future__ import annotations

import threading
from typing import Any, Callable, Generic, TypeVar


Need = TypeVar("Need")


class Lazy(Generic[Need]):
    """Annotate a constructor parameter ``Lazy[Protocol]`` when the part is needed only on some paths. It is still a need of the
    solution (uses edges, coherence), but ``assemble`` hands over a stand-in and builds the part when the first attribute is read, and
    ``pending_needs`` and ``closure`` do not count it: an answer path that never touches the part never asks for what it needs.
    A part that cannot be built raises ``AssemblyError`` at that first use."""


class LazyNeed:
    """The stand-in for one ``Lazy`` need: the real part is built once, on the first attribute read, and every read goes to it."""

    def __init__(self, label: str, build: Callable[[], Any]):
        self.label, self.build, self.lock, self.part = label, build, threading.Lock(), None

    def resolved(self) -> Any:
        """The built part, building it now if this is the first use."""
        with self.lock:
            if self.part is None:
                self.part = self.build()
            return self.part

    def __getattr__(self, name: str) -> Any:
        if name in ("label", "build", "lock", "part"):    # not yet set: never recurse into the build
            raise AttributeError(name)
        return getattr(self.resolved(), name)

    def __repr__(self) -> str:
        return f"<lazy {self.label}>"
