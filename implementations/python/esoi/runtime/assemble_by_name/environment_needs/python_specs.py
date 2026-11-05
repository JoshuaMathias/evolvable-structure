"""Parse a Python requirement line (name, extra, version range, marker) and decide whether an environment marker applies here."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple


REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[([^\]]*)\])?\s*([^;]*?)\s*(?:;\s*(.*?))?\s*$")


@dataclass(frozen=True)
class Parsed:
    """A pip requirement string taken apart: ``name[extras]specifier; marker``."""
    name: str
    extras: Tuple[str, ...] = ()
    specifier: str = ""
    marker: str = ""

    @property
    def key(self) -> str:
        return re.sub(r"[-_.]+", "-", self.name).lower()

    def spec(self) -> str:
        return self.name + (f"[{','.join(sorted(self.extras))}]" if self.extras else "") + self.specifier


def parse_requirement(text: str, extra: Optional[str] = None) -> Parsed:
    """``name[extras]specifier; marker`` from a distribution string plus the owning package's ``extra``. An unparseable string
    keeps its text as the name so pip reports it."""
    found = REQUIREMENT.match(text or "")
    if not found:
        return Parsed(text.strip(), (extra,) if extra else ())
    extras = [one.strip() for one in (found.group(2) or "").split(",") if one.strip()] + ([extra] if extra else [])
    return Parsed(found.group(1), tuple(dict.fromkeys(extras)), (found.group(3) or "").replace(" ", ""), found.group(4) or "")


def packaging_parts() -> Optional[Tuple[Any, Any]]:
    """``(SpecifierSet, Marker)`` from ``packaging`` when it is installed, else None."""
    try:
        from packaging.markers import Marker
        from packaging.specifiers import SpecifierSet
        return SpecifierSet, Marker
    except ImportError:
        return None


def marker_applies(marker: str) -> bool:
    """Whether an environment marker (``python_version``, ``sys_platform``, ...) holds here; true when it cannot be evaluated."""
    parts = packaging_parts()
    if not marker or parts is None:
        return True
    try:
        return bool(parts[1](marker).evaluate())
    except Exception:
        return True
