"""Validate a name before it is used to find a part: lower case letters, digits, ``_`` and ``-``, never an import path."""
from __future__ import annotations

import re
from typing import Any

from esoi.runtime.assemble_by_name.assembly_errors import AssemblyError


NAME_PATTERN = "^[a-z0-9][a-z0-9_-]*$"
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")


def check_name(name: Any, what: str = "name") -> str:
    """The name, or ``AssemblyError``. A name is lower case letters, digits, ``_`` and ``-``; ``.`` and ``:`` (import
    paths) and path separators never pass, so a name is never mistaken for something to import. A dotted model name such
    as ``gpt-4.1`` is data for ``options``, or an arm named ``gpt-4-1``: no recorded arm name here needs a dot."""
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise AssemblyError(f"{what} {name!r} rejected: a name matches {NAME_PATTERN} (never an import path, so '.' and ':' "
                            f"are refused); remedy: pass one of the names the solution lists with names(solution_id)")
    return name
