"""What implements a solution, read from the records, the declarations and the ownership map; never hand-kept.

An implementation record points to what implements it with its ``filepath`` cell, and what it points to says which form it is
(no new field; the standard is ``docs/reference/records-beside-code.md``):

* **code**: a source file (a declared class or function, or any language's file; ``path`` or ``path::symbol``);
* **reference**: a registry file that lists the files, services or practices that implement the solution: a CSV whose
  ``filepath``, ``path``, ``paths``, ``file`` or ``files`` column holds repository paths (``;`` separated), or a markdown
  or text file whose relative links name them;
* **registry row**: ``registry.csv::row-id``, a real-world system (an external service, an organization, a process) recorded as one row
  of a registry; the row's id must exist, and its path cells, if any, are listed.

``implemented_by`` gives the files that implement a solution: the files its implementations name, the files the code declares it in,
the paths its reference registries list, and the files of the components that the ownership map (``components.csv``) assigns it.
``problems`` reports a listed path that does not resolve, a registry row that does not exist, and code that declares a solution
but is missing from the registry that lists its implementations. Standard library only; reads text, never imports it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import RECORD_FILES
from esoi.structure.intent_registry.tables import glob_re, ids, read_csv, repo_files

REFERENCE_SUFFIXES = {".csv", ".tsv", ".md", ".txt"}
PATH_COLUMNS = ("filepath", "path", "paths", "file", "files")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s#]+)")
CAP = 8   # files a generated page lists before it says how many more there are


@dataclass
class Form:
    """One implementation's form: ``code``, ``reference``, ``registry-row`` or ``none``; the file it names, the paths it lists, and
    what is wrong with it."""
    kind: str
    file: str = ""
    listed: List[str] = field(default_factory=list)
    wrong: List[str] = field(default_factory=list)


def form_of(config: Config, filepath: str) -> Form:
    """Classify an implementation's ``filepath`` and read what a reference or registry row lists."""
    entry, _, symbol = (filepath or "").partition("::")
    entry = entry.strip()
    if not entry:
        return Form("none")
    path = (config.root / entry)
    if path.suffix.lower() not in REFERENCE_SUFFIXES:
        return Form("code", entry)
    if not path.is_file():
        return Form("reference", entry, wrong=[f"{entry} does not exist"])
    if symbol.strip() and path.suffix.lower() in (".csv", ".tsv"):
        row = next((r for r in read_csv(path) if symbol.strip() in [v.strip() for v in list(r.values())[:1]]), None)
        if row is None:
            return Form("registry-row", entry, wrong=[f"{symbol.strip()} is not a row of {entry}"])
        return Form("registry-row", entry, cells_of(row))
    if path.suffix.lower() in (".csv", ".tsv"):
        return Form("reference", entry, [p for row in read_csv(path) for p in cells_of(row)])
    text = path.read_text(encoding="utf-8", errors="ignore")
    base = path.parent
    listed = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target):
            continue
        listed.append((base / target).resolve().relative_to(config.root.resolve()).as_posix() if (base / target).resolve().is_relative_to(config.root.resolve()) else target)
    return Form("reference", entry, listed)


def cells_of(row: Dict[str, str]) -> List[str]:
    """The repository paths one registry row lists (the cells of its path columns, ``;`` separated)."""
    return [p for column in PATH_COLUMNS for p in ids(row.get(column, ""))]


def unresolved(config: Config, form: Form) -> List[str]:
    """The paths a form lists that are not files or folders of the repository."""
    return [p for p in form.listed if "*" not in p and not (config.root / p).exists()]


def component_files(config: Config, registry, solution_id: str, files: Optional[List[str]] = None) -> List[str]:
    """The files the ownership map assigns to a solution: those matched by the ``path`` globs of every component that names it."""
    files = repo_files(config.root) if files is None else files
    patterns = [glob_re(p.strip()) for c in registry.components if solution_id in ids(c.get("solutions", ""))
                for p in c.get("path", "").split(";") if p.strip()]
    generated = {"README.md", "diagram.md", "intent.csv", *RECORD_FILES}   # what the library writes or reads as records is not an implementation
    return sorted(f for f in files if f.rsplit("/", 1)[-1] not in generated and any(p.match(f) for p in patterns))


def implementing_rows(registry, solution_id: str) -> List[Dict[str, str]]:
    return [r for r in registry.implementations if r.get("solution_id", "").strip() == solution_id]


def implemented_by(config: Config, registry, solution_id: str, declared=None, files: Optional[List[str]] = None) -> List[str]:
    """The files that implement a solution, sorted: what its implementations name (a reference file with what it lists), the files the
    code declares it in, and the files of its components. Only files that exist."""
    found: Set[str] = set()
    for row in implementing_rows(registry, solution_id):
        form = form_of(config, row.get("filepath", ""))
        if form.file:
            found.add(form.file)
        found.update(p for p in form.listed if (config.root / p).is_file())
    for (sid, _), decl in (getattr(declared, "implementations", {}) or {}).items():
        if sid == solution_id:
            found.add(decl.file)
    found.update(component_files(config, registry, solution_id, files))
    return sorted(f for f in found if (config.root / f).is_file())


def problems(config: Config, registry, declared=None) -> List[Tuple[str, str]]:
    """``(key, finding)`` for each deviation: a listed path that does not resolve or a registry row that is missing (key: the
    implementation id), and code that declares a solution but that no registry of its implementations lists (key: the solution id)."""
    out: List[Tuple[str, str]] = []
    listed_by: Dict[str, Set[str]] = {}
    has_registry: Dict[str, str] = {}
    for row in registry.implementations:
        form = form_of(config, row.get("filepath", ""))
        ident, sid = row.get("implementation_id", ""), row.get("solution_id", "").strip()
        for wrong in form.wrong:
            out.append((ident, f"S40 {ident}: its reference is wrong, {wrong}; next: fix the `filepath` of the record or the row it names"))
        for path in unresolved(config, form):
            out.append((ident, f"S40 {ident}: {form.file} lists {path}, which does not resolve; next: correct or remove that entry"))
        if form.kind in ("reference", "registry-row"):
            listed_by.setdefault(sid, set()).update(form.listed)
            has_registry[sid] = form.file
    for (sid, _), decl in sorted((getattr(declared, "implementations", {}) or {}).items()):
        if sid in has_registry and decl.file not in listed_by.get(sid, set()):
            out.append((sid, f"S40 {sid}: {decl.file} declares it but {has_registry[sid]} does not list it; next: add {decl.file} to {has_registry[sid]}"))
    return out
