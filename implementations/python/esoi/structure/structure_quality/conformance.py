"""Does an arm really implement its solution's interface: every member, with parameters that match, under a solution id that exists.

A merge once left a whole family of arms carrying the ``@implementation`` decorator and nothing else, and a name-only check lets a Protocol that its
arms barely implement pass. So an arm must define (or inherit from a base the project defines) every public member of the Protocol its solution
declares, a method with parameters that match (each Protocol parameter present by name and in position, every extra parameter optional, async kept),
an attribute under the same name; and the solution id it names must be a solution the project declares (an ``@solution`` or a row of a
``solutions.csv``). A method whose body is only ``pass``, ``...`` or ``raise NotImplementedError`` (after its docstring) is a stub and does not
implement the member, so a fat interface cannot be met by stubbing it. Nothing is imported or run.

An arm passes through when every member it implements is one call of a method of the same name on another object (``self.next.run(data)``) with
its own parameters handed on unchanged: it adds no work of its own (Ousterhout's pass-through method, the sign of a solution split finer than its job).
A call rooted in a name the arm's own unit binds (one of its modules, or a function of one) is the arm's own work, not a pass-through.
"""
from __future__ import annotations

import ast
import csv
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.structure_quality.project import Project

Signature = Tuple[Tuple[str, ...], Tuple[str, ...], bool, bool, bool, int]   # positional names, keyword-only names, takes *args, takes **kwargs, async, required positionals


def decorator_id(node: ast.ClassDef, name: str) -> str:
    """The solution id a ``@solution("id", ...)`` or ``@implementation("id", ...)`` decorator names, or an empty string."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and getattr(dec.func, "id", getattr(dec.func, "attr", "")) == name and dec.args:
            first = dec.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return first.value
    return ""


def is_protocol(node: ast.ClassDef) -> bool:
    return any(getattr(b, "id", getattr(b, "attr", "")) == "Protocol" for b in node.bases)


def signature(node: ast.AST) -> Signature:
    args = node.args
    positional = tuple(a.arg for a in [*args.posonlyargs, *args.args] if a.arg not in ("self", "cls"))
    required = len(positional) - len(args.defaults)
    return positional, tuple(a.arg for a in args.kwonlyargs), args.vararg is not None, args.kwarg is not None, isinstance(node, ast.AsyncFunctionDef), required


def public(name: str) -> bool:
    return not name.startswith("_")


def body_statements(function: ast.AST) -> List[ast.AST]:
    """A function's statements without its docstring and without imports (an import inside a method is how it reaches its own code lazily)."""
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return [s for s in body if not isinstance(s, (ast.Import, ast.ImportFrom))]


def is_stub(function: ast.AST) -> bool:
    """Whether a method only stands in for an implementation: nothing, ``pass``, ``...`` or ``raise NotImplementedError``."""
    for statement in body_statements(function):
        if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and statement.value.value is Ellipsis):
            continue
        raised = getattr(statement, "exc", None) if isinstance(statement, ast.Raise) else None
        raised = raised.func if isinstance(raised, ast.Call) else raised
        if isinstance(raised, ast.Name) and raised.id == "NotImplementedError":
            continue
        return False
    return True


def passes_through(function: ast.AST, own_modules: Set[str]) -> bool:
    """Whether a method is one call of a same-named method on another object with its own parameters handed on unchanged; ``own_modules`` are the
    local names bound to modules of the arm's own unit (a call into them is the arm's own work)."""
    statements = body_statements(function)
    if len(statements) != 1 or not isinstance(statements[0], (ast.Return, ast.Expr)) or not isinstance(statements[0].value, ast.Call):
        return False
    call = statements[0].value
    if not isinstance(call.func, ast.Attribute) or call.func.attr != function.name:
        return False
    owner = call.func.value
    while isinstance(owner, (ast.Attribute, ast.Call)):   # own_runner().assembler.names(...) is rooted in own_runner
        owner = owner.func if isinstance(owner, ast.Call) else owner.value
    if isinstance(owner, ast.Name) and owner.id in own_modules:
        return False
    params = [a.arg for a in [*function.args.posonlyargs, *function.args.args] if a.arg not in ("self", "cls")]
    handed = [a.id for a in call.args if isinstance(a, ast.Name)] + [k.value.id for k in call.keywords if isinstance(k.value, ast.Name)]
    return len(handed) == len(call.args) + len(call.keywords) and sorted(handed) == sorted(params + [a.arg for a in function.args.kwonlyargs])


def members_of(node: ast.ClassDef) -> Tuple[Dict[str, ast.AST], Set[str]]:
    """The public methods (name to definition) and the public attributes (annotated or assigned names, and ``self.x = ...`` in any method) of a class body."""
    methods: Dict[str, ast.AST] = {}
    attributes: Set[str] = set()
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and public(item.name):
            methods[item.name] = item
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and public(item.target.id):
            attributes.add(item.target.id)
        elif isinstance(item, ast.Assign):
            attributes |= {t.id for t in item.targets if isinstance(t, ast.Name) and public(t.id)}
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(item):
                if isinstance(sub, (ast.Assign, ast.AnnAssign)):
                    for target in (sub.targets if isinstance(sub, ast.Assign) else [sub.target]):
                        if isinstance(target, ast.Attribute) and getattr(target.value, "id", "") == "self" and public(target.attr):
                            attributes.add(target.attr)
    return methods, attributes


def protocol_members(node: ast.ClassDef, index: Optional[Dict[str, ast.ClassDef]] = None) -> Dict[str, Optional[ast.AST]]:
    """Each public member a Protocol declares: a method's definition, or None for an attribute. With ``index`` (class name to definition) the members
    of the base Protocols it extends count too, so a Protocol that only extends another (``class CardKeeping(CardStore, Protocol)``) is not read as empty."""
    methods, attributes = inherited_members(node, index, {node.name}) if index is not None else members_of(node)
    return {**{a: None for a in attributes}, **methods}


def inherited_members(node: ast.ClassDef, index: Dict[str, ast.ClassDef], seen: Set[str]) -> Tuple[Dict[str, ast.AST], Set[str]]:
    """The members of a class and of every base class the project defines by name (an arm may take its members from a base); the nearest definition wins."""
    methods, attributes = members_of(node)
    for base in node.bases:
        name = getattr(base, "id", getattr(base, "attr", ""))
        if name in index and name not in seen and name != "Protocol":
            more_methods, more_attributes = inherited_members(index[name], index, seen | {name})
            methods = {**more_methods, **methods}
            attributes |= more_attributes
    return methods, attributes


def mismatch(want: ast.AST, have: ast.AST) -> str:
    """Why an arm's method does not fit the Protocol's, or an empty string when it does."""
    w, h = signature(want), signature(have)
    if w[4] != h[4]:
        return "async differs"
    for position, name in enumerate(w[0]):
        if position < len(h[0]):
            if h[0][position] != name:
                return f"parameter {position + 1} is {h[0][position]}, the interface has {name}"
        elif not h[2] and not h[3] and name not in h[1]:
            return f"parameter {name} is missing"
    for name in w[1]:
        if name not in h[0] + h[1] and not h[3]:
            return f"keyword parameter {name} is missing"
    if h[5] > len(w[0]):
        return "takes more required parameters than the interface passes"
    extra_keywords = [a.arg for a, d in zip(have.args.kwonlyargs, have.args.kw_defaults) if d is None and a.arg not in w[1]]
    return f"requires keyword parameter {extra_keywords[0]}" if extra_keywords else ""


def declared_solutions(projects: List[Project], protocols: Set[str]) -> Set[str]:
    """Solution ids the project and the libraries it adopts from declare: every ``@solution`` and every id column of a ``solutions.csv``."""
    found = set(protocols)
    for project in projects:
        for relative in project.named["solutions.csv"]:
            with (project.root / relative).open(newline="", encoding="utf-8") as handle:
                found |= {row.get("id", "") for row in csv.DictReader(handle) if row.get("id")}
    return found


def arm_problems(arm: ast.ClassDef, protocols: List[Dict[str, Optional[ast.AST]]], index: Dict[str, ast.ClassDef]) -> Tuple[List[str], int]:
    """``(problems, members)``: what one arm lacks of its solution's interface, measured against the Protocol it comes closest to (the smallest share of members lacking) when the project and
    an adopted library both declare one for the id (a bare name for a missing member, ``name: reason`` for a method whose parameters do not match),
    and how many members that Protocol declares (the whole against which the lack is a share)."""
    methods, attributes = inherited_members(arm, index, {arm.name} if index.get(arm.name) is arm else set())
    closest = min(protocols, key=lambda protocol: len(protocol_problems(protocol, methods, attributes)) / max(len(protocol), 1))
    return protocol_problems(closest, methods, attributes), len(closest)


def protocol_problems(protocol: Dict[str, Optional[ast.AST]], methods: Dict[str, ast.AST], attributes: Set[str]) -> List[str]:
    problems = []
    for name, want in sorted(protocol.items()):
        if want is None:
            if name not in attributes and name not in methods:
                problems.append(name)
        elif name not in methods:
            problems.append(name)
        elif is_stub(methods[name]):
            problems.append(f"{name}: a stub that implements nothing")
        else:
            why = mismatch(want, methods[name])
            if why:
                problems.append(f"{name}: {why}")
    return problems
