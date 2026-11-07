"""Each Python file parsed once and each tree walked once per run, shared by every reader of source (the rules, the import scan, the
declaration scan, the coherence evidence and the structure quality scorer), so a check that asks many questions of the same files pays
for reading them once. A tree is remembered by the file's path, modification time and size, so an edited file is read again; the
remembered trees live as long as the process."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TREES: Dict[Tuple[str, int, int], Optional[ast.Module]] = {}
WALKS: Dict[int, Tuple[ast.AST, Tuple[ast.AST, ...]]] = {}   # id of a tree -> (the tree, kept so the id stays its own, every node in walk order)
STATS = {"parses": 0}   # the performance guard test reads it: files parsed


def tree_of(path: Path) -> Optional[ast.Module]:
    """The syntax tree of a Python file, parsed the first time it is asked for and again only after the file changes; None when the file
    cannot be read or does not parse."""
    path = Path(path)
    try:
        info = path.stat()
    except OSError:
        return None
    key = (str(path), info.st_mtime_ns, info.st_size)
    if key not in TREES:
        try:
            STATS["parses"] += 1
            TREES[key] = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            TREES[key] = None
    return TREES[key]


def first_string(call: ast.Call) -> Optional[str]:
    """The string a call's first argument is written as, or None when it has no such argument."""
    first = call.args[0] if call.args else None
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


def decorator_calls(node: ast.AST, *names: str) -> List[ast.Call]:
    """The decorators of a function or class written as a call of one of ``names`` (``@name(...)`` or ``@module.name(...)``), in order."""
    return [deco for deco in getattr(node, "decorator_list", ())
            if isinstance(deco, ast.Call) and getattr(deco.func, "id", getattr(deco.func, "attr", "")) in names]


def nodes_of(tree: ast.AST) -> Tuple[ast.AST, ...]:
    """Every node of a tree in ``ast.walk`` order, walked the first time and reused after."""
    held = WALKS.get(id(tree))
    if held is None or held[0] is not tree:
        held = (tree, tuple(ast.walk(tree)))
        WALKS[id(tree)] = held
    return held[1]
