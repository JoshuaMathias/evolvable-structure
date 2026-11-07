"""The dotted module a ``from ... import`` statement names, with a relative import resolved against the package of the file that holds it, and every module name an import statement may refer to."""
import ast
from typing import List, Optional


def import_base(package: List[str], level: int, module: Optional[str]) -> str:
    """``module`` as the statement names it (``level`` leading dots) resolved against ``package``, the dotted parts of the importing file's package."""
    base = module or ""
    if not level:
        return base
    parts = package[: max(len(package) - (level - 1), 0)] if level > 1 else package
    return ".".join(parts + ([base] if base else []))


def statement_modules(node: ast.AST, package: List[str]) -> List[str]:
    """Every module name one import statement may refer to (``import a.b``: ``a.b``; ``from x import y``: ``x`` and ``x.y``, since ``y`` may be a
    module; a star import adds nothing for the star), relative imports resolved against ``package``. Any other node names none."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        base = import_base(package, node.level, node.module)
        return [base] + [f"{base}.{alias.name}" for alias in node.names if alias.name != "*"]
    return []
