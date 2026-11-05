"""Where the source file of a module, class or function lives, shared by script discovery and the import walk."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import ModuleType
from typing import Any, Optional


def source_path(obj: Any) -> Optional[Path]:
    """The source file of a module, class or function (of its class for an instance); None when it has none."""
    try:
        if isinstance(obj, ModuleType):
            raw = getattr(obj, "__file__", None)
        else:
            raw = inspect.getsourcefile(obj if inspect.isclass(obj) or inspect.isroutine(obj) else type(obj))
    except (TypeError, OSError):
        return None
    return Path(raw).resolve() if raw else None
