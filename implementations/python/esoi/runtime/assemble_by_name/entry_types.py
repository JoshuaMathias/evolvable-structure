"""The values the one-line entry raises and returns about a target: ``EntryError``, ``Reason``, ``Pending`` and ``Target``."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple


class EntryError(LookupError):
    """The id names nothing reachable, or what it names declares no entry; the message says what to declare. ``code`` is
    ``no-entry`` when the cause is a missing declaration, else ``fail``."""

    def __init__(self, message: str, code: str = "fail"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Reason:
    """One blocked seat and what it needs: ``kind`` is ``key`` (a variable or account), ``install`` (a package or a program), ``network`` (network access, unmet under ``ESOI_OFFLINE=1``),
    ``option`` (a constructor argument to pass), ``provided`` (no arm: pass your own object), ``load`` (the arm cannot be
    imported) or ``needs`` (it waits on another seat, which has its own reason)."""
    seat: str
    arm: str
    kind: str
    need: str
    waits: Tuple[str, ...] = ()   # for kind "needs": the seats it waits on, whose own reasons settle it


class Pending(RuntimeError):
    """The solution cannot run until the caller sets something. ``lines`` name each key, install or option, one per seat;
    ``reasons`` carry the same as structured ``Reason`` records, so nothing has to read the text."""

    def __init__(self, solution_id: str, lines: Sequence[str], reasons: Sequence[Reason] = ()):
        self.solution_id, self.lines, self.reasons = solution_id, tuple(lines), tuple(reasons)
        super().__init__(f"{solution_id} cannot run yet: " + " | ".join(self.lines))


@dataclass(frozen=True)
class Target:
    """What one id reaches: the solution whose entry runs, the arm forced for it (a sub-intent is one arm), and the level."""
    id: str
    solution_id: str
    level: str          # "solution" or "intent"
    arm: str = ""
