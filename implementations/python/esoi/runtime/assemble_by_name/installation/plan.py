"""The data of an install plan: the pip set, the scripts to run, the substitutions made and the arms isolated in their own environment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from esoi.runtime.assemble_by_name.environment_needs.declarations import Entry
from esoi.runtime.assemble_by_name.installation.conflicts import Conflict


@dataclass(frozen=True)
class Substitution:
    """A seat whose selected arm cannot coexist with the others here, and the arm used instead (a circumstance, not a default)."""
    solution_id: str
    selected: str
    using: str
    because: str

    def text(self) -> str:
        return f"{self.solution_id}: selected {self.selected}; using {self.using} here because {self.because}"


@dataclass(frozen=True)
class Isolated:
    """An arm installed in a virtual environment of its own, reached through its declared process boundary."""
    arm: str
    boundary: str
    folder: str
    specs: Tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    """What installing the closure would do, in order, and everything the ladder decided.

    ``pip`` is the one requirement set for the current environment; ``constraints`` the installed versions to keep;
    ``scripts`` are ``(role, path)`` in the order install.sh, requirements.txt, install.py per implementation; ``isolated`` arms
    get their own environments; ``substitutions`` name arms used instead of the selected ones; ``steps`` is the ladder log;
    ``conflicts`` is non-empty only when no step worked (then nothing is installed); ``binaries`` and ``missing`` are for a person."""
    pip: Tuple[str, ...] = ()
    constraints: Tuple[str, ...] = ()
    scripts: Tuple[Tuple[str, str], ...] = ()
    isolated: Tuple[Isolated, ...] = ()
    substitutions: Tuple[Substitution, ...] = ()
    steps: Tuple[str, ...] = ()
    conflicts: Tuple[str, ...] = ()
    options: Tuple[str, ...] = ()
    binaries: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.pip or self.scripts or self.isolated)

    @property
    def coherent(self) -> bool:
        return not self.conflicts

    @property
    def adjusted(self) -> bool:
        """True when the selected arms did not coexist as declared and the ladder had to act (or failed): what CI should flag."""
        return bool(self.conflicts or self.substitutions or self.isolated or any("instead of" in step for step in self.steps))


Fallback = Callable[[Sequence[Conflict], Sequence[Entry]], Optional[Tuple[Substitution, List[Entry]]]]
