"""How hard one function is to read whole, beyond its length: McCabe's cyclomatic complexity, counted on the function's own body.

The count is one plus each branch point (``if``, a loop, an ``except``, a ``with``, a conditional expression, a comprehension clause, an
``assert``, a ``match`` case) plus each extra operand of ``and`` or ``or``. A nested function, class or lambda is its own function and is left
out of its parent's count. On the four repositories measured on 2026-11-05 the rank correlation of this count with function length was 0.70
to 0.81, and 1.5 to 3.2 percent of functions were very complex (over 20) while under the length budget, which is why it is a part of the size
dimension and not a stand-in for length. Nothing is imported or run.
"""
from __future__ import annotations

import ast
from typing import Iterator

BRANCHES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.IfExp, ast.comprehension, ast.Assert, ast.match_case)
OWN_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def own_nodes(function: ast.AST) -> Iterator[ast.AST]:
    """The nodes of a function's body that belong to it, not to a function, class or lambda defined inside it."""
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        if isinstance(node, OWN_SCOPES):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def cyclomatic(function: ast.AST) -> int:
    count = 1
    for node in own_nodes(function):
        if isinstance(node, BRANCHES):
            count += 1
        elif isinstance(node, ast.BoolOp):
            count += len(node.values) - 1
    return count
