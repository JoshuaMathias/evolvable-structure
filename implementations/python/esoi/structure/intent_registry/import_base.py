"""The dotted module a ``from ... import`` statement names, with a relative import resolved against the package of the file that holds it."""
from typing import List, Optional


def import_base(package: List[str], level: int, module: Optional[str]) -> str:
    """``module`` as the statement names it (``level`` leading dots) resolved against ``package``, the dotted parts of the importing file's package."""
    base = module or ""
    if not level:
        return base
    parts = package[: max(len(package) - (level - 1), 0)] if level > 1 else package
    return ".".join(parts + ([base] if base else []))
