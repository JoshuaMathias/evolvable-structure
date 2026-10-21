"""Declarations in code, read without importing it, and kept in step with the records.

``esoi.runtime`` lets code declare a solution (``@solution("id")``) and its alternatives (``@implementation("id",
"name")``, or ``register("id", "name", target)`` for another package's class). The records still hold the rest of the
intent (problem, ideal, metric, the human text), so the two must agree. This module is the bridge, and it derives
instead of asking for a second copy:

* ``scan`` reads the declarations from the source files of the measured code (``code_paths``) with ``ast``;
* ``drift`` reports what the code declares and the records lack (rule S30), so a new alternative cannot ship unrecorded;
* ``sync`` writes the missing rows, filling only what the code knows (the id, the file, the signature as the solution's
  parameters and outputs, the docstring as its purpose) and never overwriting a cell a person wrote. The text only a
  person can write stays empty, and ``esoi check`` names it.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import intents
from .config import Config
from .records import TEMPLATE_DATA, fields, load_template
from .registry import Registry
from .tables import ids, read_csv, read_header, write_csv

DECORATORS = {"solution", "implementation"}
SKIP_PARTS = {"vendor", "__pycache__", "build", "dist", ".venv"}


@dataclass
class SolutionDecl:
    solution_id: str
    file: str
    line: int
    name: str = ""
    purpose: str = ""
    parameters: str = ""
    outputs: str = ""
    port: str = ""


@dataclass
class ImplementationDecl:
    solution_id: str
    name: str
    file: str
    line: int
    purpose: str = ""

    @property
    def implementation_id(self) -> str:
        return f"{self.solution_id}:{self.name}"


@dataclass
class Declared:
    solutions: Dict[str, SolutionDecl] = field(default_factory=dict)
    implementations: Dict[Tuple[str, str], ImplementationDecl] = field(default_factory=dict)


def title(text: str) -> str:
    words = text.replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:]


def string_arg(node: ast.AST) -> Optional[str]:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def imports_esoi(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "esoi":
            return True
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "esoi" for a in node.names):
            return True
    return False


def decorator_call(node: ast.AST) -> Optional[Tuple[str, ast.Call]]:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    word = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
    return (word, node) if word in DECORATORS else None


def first_paragraph(doc: Optional[str]) -> str:
    return " ".join((doc or "").strip().split("\n\n")[0].split())


def signature(node: ast.AST) -> Tuple[str, str]:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return "", ""
    args = ast.unparse(node.args)
    return args, ast.unparse(node.returns) if node.returns else ""


def scan_file(rel: str, text: str, out: Declared) -> None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    if not imports_esoi(tree):
        return
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for decorator in node.decorator_list:
                found = decorator_call(decorator)
                if not found or not found[1].args or string_arg(found[1].args[0]) is None:
                    continue
                kind, call = found
                sid = string_arg(call.args[0]) or ""
                purpose = first_paragraph(ast.get_docstring(node))
                if kind == "solution":
                    params, returns = signature(node)
                    out.solutions[sid] = SolutionDecl(sid, rel, node.lineno, node.name, purpose, params, returns,
                                                      node.name if isinstance(node, ast.ClassDef) else "")
                else:
                    given = string_arg(call.args[1]) if len(call.args) > 1 else None
                    given = given or next((string_arg(k.value) for k in call.keywords if k.arg == "name"), None)
                    name = (given or node.name).strip().lower()
                    out.implementations[(sid, name)] = ImplementationDecl(sid, name, rel, node.lineno, purpose)
        elif isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            word = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            strings = [string_arg(a) for a in node.args[:2]]
            if word == "register" and len(strings) == 2 and all(strings):
                name = (strings[1] or "").strip().lower()
                out.implementations[(strings[0] or "", name)] = ImplementationDecl(strings[0] or "", name, rel, node.lineno)


def code_files(config: Config) -> List[str]:
    """The Python files of the measured code that lie inside the repository, repository-relative."""
    found: List[str] = []
    for entry in config.code_paths:
        base = (config.root / entry).resolve()
        if not base.is_relative_to(config.root):
            continue
        paths = [base] if base.is_file() else sorted(base.rglob("*.py")) if base.is_dir() else []
        for path in paths:
            rel = path.relative_to(config.root)
            if path.suffix == ".py" and not (set(rel.parts) & SKIP_PARTS):
                found.append(rel.as_posix())
    return sorted(set(found))


def scan(config: Config, files: Optional[List[str]] = None) -> Declared:
    """Every solution and implementation the code declares, found by reading the source (nothing is imported)."""
    out = Declared()
    for rel in files if files is not None else code_files(config):
        path = config.root / rel
        if path.is_file():
            scan_file(rel, path.read_text(encoding="utf-8"), out)
    return out


def drift(config: Config, registry: Registry, declared: Declared) -> List[str]:
    """What the code declares and the records do not say, as S30 lines."""
    solutions = {r.get("solution_id", "") for r in registry.every_solution()}
    records = {r.get("implementation_id", ""): r for r in registry.implementations}
    bad: List[str] = []
    for sid, decl in sorted(declared.solutions.items()):
        if sid not in solutions:
            bad.append(f"S30 {sid}: declared at {decl.file}:{decl.line} but no solutions.csv row has that solution_id "
                       "(`esoi records sync` writes it)")
    for (sid, name), decl in sorted(declared.implementations.items()):
        if sid not in solutions and sid not in declared.solutions and not sid.startswith("@"):
            bad.append(f"S30 {sid}:{name}: declared at {decl.file}:{decl.line} for a solution that is neither declared "
                       "nor in solutions.csv")
            continue
        record = records.get(decl.implementation_id)
        if record is None:   # a record whose id follows no pattern still counts when its path is this file and it is alone there
            alone = [r for r in records.values() if r.get("solution_id") == sid and (r.get("filepath") or "").strip() == decl.file]
            siblings = [d for (s, _), d in declared.implementations.items() if s == sid and d.file == decl.file]
            record = alone[0] if len(alone) == 1 and len(siblings) == 1 else None
        if record is None:
            bad.append(f"S30 {decl.implementation_id}: declared at {decl.file}:{decl.line} but implementations.csv has no "
                       "such record (`esoi records sync` writes it)")
        elif (record.get("filepath") or "").strip().split("::")[0] != decl.file and decl.line:
            bad.append(f"S30 {decl.implementation_id}: declared in {decl.file} but its record's `filepath` says "
                       f"{(record.get('filepath') or '').strip() or 'nothing'} (`esoi records sync` fills an empty filepath; "
                       "a wrong one is yours to correct)")
    return bad


def intent_folder(config: Config, intent_id: Optional[str]) -> Path:
    if not intent_id:
        return config.structure
    for found in intents.discover(config):
        if found.intent_id == intent_id:
            return found.folder
    raise ValueError(f"no intent {intent_id!r} in {config.structure_dir}")


def table_rows(folder: Path, name: str, key: str, template: Dict[str, List[Dict[str, str]]], entity: str):
    path = folder / name
    if path.is_file():
        return read_header(path), read_csv(path)
    extra = {"implementation": ["filepath", "sub_intent", "uses_solution_ids"]}.get(entity, [])
    columns = [key] + fields(template, entity, True) + extra
    return columns, []


def blank(columns: List[str], **given: str) -> Dict[str, str]:
    row = {c: "" for c in columns}
    row.update({k: v for k, v in given.items() if k in columns})
    return row


def sync(config: Config, registry: Registry, declared: Declared, intent_id: Optional[str] = None,
         apply: bool = True) -> List[str]:
    """Write the solution rows and implementation records the code declares and the records lack, into the folder of
    ``intent_id`` (default the top intent). Only cells the code knows are filled; a cell with text is never touched.
    Returns what changed, one line each (and writes nothing when ``apply`` is false)."""
    folder = intent_folder(config, intent_id)
    template = load_template(TEMPLATE_DATA)
    known_solutions = {r.get("solution_id", "") for r in registry.every_solution()}
    known_records = {r.get("implementation_id", "") for r in registry.implementations}
    sol_cols, sol_rows = table_rows(folder, "solutions.csv", "solution_id", template, "solution")
    imp_cols, imp_rows = table_rows(folder, "implementations.csv", "implementation_id", template, "implementation")
    sol_by_id = {r["solution_id"]: r for r in sol_rows}
    done: List[str] = []
    for sid, decl in sorted(declared.solutions.items()):
        if sid in known_solutions:
            continue
        names = sorted(n for s, n in declared.implementations if s == sid)
        row = blank(sol_cols, solution_id=sid, name=title(decl.name or sid), scoped_purpose=decl.purpose,
                    parameters=decl.parameters, outputs=decl.outputs, interface_name=decl.port, implementations=";".join(names),
                    selected=names[0] if len(names) == 1 else "", selected_by="the only implementation declared so far"
                    if len(names) == 1 else "")
        sol_rows.append(row)
        sol_by_id[sid] = row
        done.append(f"solutions.csv: add {sid} (from {decl.file}:{decl.line})")
    for (sid, name), decl in sorted(declared.implementations.items()):
        if decl.implementation_id not in known_records:
            imp_rows.append(blank(imp_cols, implementation_id=decl.implementation_id, solution_id=sid, filepath=decl.file,
                                  name=title(name), description=decl.purpose))
            done.append(f"implementations.csv: add {decl.implementation_id} (from {decl.file}:{decl.line})")
        else:
            record = next((r for r in imp_rows if r.get("implementation_id") == decl.implementation_id), None)
            if record is not None and "filepath" in record and not record["filepath"].strip():
                record["filepath"] = decl.file
                done.append(f"implementations.csv: fill the empty filepath of {decl.implementation_id}")
        row = sol_by_id.get(sid)
        listed = ids(row["implementations"]) if row is not None and "implementations" in row else []
        if row is not None and "implementations" in row and name not in listed \
                and decl.file not in [e.split("::")[0] for e in listed]:
            row["implementations"] = ";".join(listed + [name])
            done.append(f"solutions.csv: list {name} in the implementations of {sid}")
    if apply and done:
        write_csv(folder / "solutions.csv", sol_cols, sol_rows)
        write_csv(folder / "implementations.csv", imp_cols, imp_rows)
    return done
