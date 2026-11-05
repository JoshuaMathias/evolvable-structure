"""Variants: the same implementation with other parameters, named ``base@key=value,key=value`` (keys sorted).

A variant is a name, not a new file. The same string is the ``impl`` cell of a results row, the ``--impl`` argument, a
``using=`` value, a ``selected`` cell and an entry of a circumstance's selection, so the comparability and verdict code, which
works on ``impl`` strings, needs no change. ``base`` is resolved as any implementation name is, and the parameters are
passed to it as keyword arguments (``build(meter, **params)`` for a harness wrapper, ``implementation(**params, **args)``
for a declared one). ``true`` and ``false`` are passed as booleans, a whole number as an int, a decimal as a float; any
other value stays text. Keys start with a letter and use ``a-z``, ``0-9`` and ``_``; values use ``a-z``, ``0-9``, ``_``, ``.``
and ``-``. Keys are sorted and values written as the value they read as, so ``k=01`` and ``k=1`` are one arm. Standard
library only.

    split("fast_edit@edit_format=auto,lines=400")   # ("fast_edit", {"edit_format": "auto", "lines": 400})
    canonical("fast_edit@lines=0400,edit_format=auto")   # "fast_edit@edit_format=auto,lines=400"
"""
from __future__ import annotations

import re
from typing import Any, Dict, Tuple

MARK = "@"
KEY = re.compile(r"^[a-z][a-z0-9_]*$")
VALUE = re.compile(r"^[a-z0-9_.\-]+$")


def coerce(value: str) -> Any:
    """``true`` / ``false`` as a bool, ``12`` / ``-3`` as an int, ``1.5`` as a float, else the text (never ``nan`` or ``1_0``)."""
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return float(value) if re.fullmatch(r"-?\d+\.\d+", value) else value


def spell(value: Any) -> str:
    """The one spelling of a coerced value in a name."""
    return str(value).lower() if isinstance(value, bool) else str(value)


def words(name: str) -> Tuple[str, Dict[str, str]]:
    """``(base, parameters as written)``. Raises ``ValueError`` for a malformed or repeated parameter, so a typo in a name
    fails loudly."""
    base, mark, text = str(name).strip().partition(MARK)
    found: Dict[str, str] = {}
    for part in (p for p in text.split(",") if mark and p):
        key, equals, value = (piece.strip() for piece in part.partition("="))
        if not (equals and KEY.match(key) and VALUE.match(value)):
            raise ValueError(f"{part!r} in {name!r} is not key=value (key a-z0-9_ from a letter, value a-z0-9_.-)")
        if key in found:
            raise ValueError(f"{key} is given twice in {name!r}")
        found[key] = value
    if mark and not found:
        raise ValueError(f"{name!r} has {MARK} but no parameter")
    return base, found


def split(name: str) -> Tuple[str, Dict[str, Any]]:
    """``(base, parameters)`` of an implementation name, a number passed as a number; no ``@`` means no parameters."""
    base, found = words(name)
    return base, {key: coerce(value) for key, value in found.items()}


def canonical(name: str) -> str:
    """The name with its parameters in key order, so one variant has one spelling in every record."""
    base, found = split(name)
    return base + (MARK + ",".join(f"{k}={spell(found[k])}" for k in sorted(found)) if found else "")


def base_of(name: str) -> str:
    return str(name).partition(MARK)[0].strip()
