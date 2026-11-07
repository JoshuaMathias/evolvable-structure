"""Code evidence of a uses edge (M2, rule S38): the modules, imports, documents and executable tokens that show one solution uses another (E1 to E5, W1 to W3)."""
from __future__ import annotations

import ast
import os
import posixpath
import re
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry.import_base import import_base, statement_modules
from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of
from esoi.structure.intent_registry.tables import glob_re
from esoi.structure.structure_check.coherence_paragraph import position
from esoi.structure.structure_check.coherence_records import ids

DOCUMENT_SUFFIXES = (".md", ".markdown", ".mdx")
SKIPPED_FOLDERS = {"node_modules", "__pycache__", "venv", "site-packages", "dist", "build"}
FENCE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$|^[ \t]*(```|~~~).*\Z", re.S | re.M)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
INLINE_CODE = re.compile(r"(`+)[^`\n]*?\1")
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)")
REFERENCE_LINK = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*<?(\S+?)>?(?:[ \t]+.*)?$", re.M)
INCLUDE = re.compile(r"\{\{#include\s+([^\s}:]+)[^}]*\}\}|\{%[-\s]*include\s+[\"']?([^\s\"'%]+)|^[ \t]*!include[ \t]+(\S+)", re.M)


def document_entries(cell: str) -> List["tuple[str, str]"]:
    """The ``(document path, solution id)`` pairs of a components.csv ``documents`` cell: ``path=solution-id`` entries separated by
    ``;``. An entry with no ``=`` comes back with an empty solution id so a rule can name it."""
    out = []
    for entry in ids(cell):
        path, _, solution = entry.partition("=")
        out.append((path.strip(), solution.strip()))
    return out


def dotted_name(package: str, pkg_dir: Path, file: Path) -> str:
    """The dotted module name of a source file in the package folder (a package's ``__init__`` is the package itself)."""
    parts = [package] + list(file.relative_to(pkg_dir).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def annotated_with(arg: ast.arg, names: List[str]) -> bool:
    """Whether a parameter's annotation names one of the given classes."""
    if arg.annotation is None:
        return False
    return bool(set(names) & set(ast.unparse(arg.annotation).replace("'", "").replace('"', "").split(".")))


def walk_tops(tops) -> List[ast.AST]:
    """Every syntax node under the given top nodes."""
    return [n for top in tops for n in nodes_of(top)]


def node_token(node: ast.AST, prose: Set[int]) -> Optional[str]:
    """The name or string value one syntax node contributes to the executable tokens, or None."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) and id(node) not in prose else None
    return name_token(node)


def name_token(node: ast.AST) -> Optional[str]:
    """The identifier a name-bearing syntax node contributes, or None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.alias)):
        return node.name
    if isinstance(node, (ast.arg, ast.keyword)):
        return node.arg or None
    if isinstance(node, ast.ImportFrom):
        return node.module or None
    return None


def executable_tokens(text: str, tree, nodes=None) -> List[str]:
    """The names and string values the executable code of a Python module holds: identifiers, attributes, imported names,
    parameter and keyword names, and string literals used as values. Docstrings and any other bare string statement are
    documentation and left out, and so is every comment (a comment is not in the syntax tree). A module that does not parse
    falls back to its text with comment lines removed. ``nodes`` limits the walk to those syntax nodes (one solution's classes in
    a module several solutions share)."""
    if tree is None:
        return [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    walked = walk_tops(nodes if nodes is not None else [tree])
    prose = {id(n.value) for n in walked if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
             and isinstance(n.value.value, str)}
    tokens = [node_token(node, prose) for node in walked]
    return [t for t in tokens if t is not None]


def document_targets(text: str) -> List[str]:
    """The relative targets a markdown document links to or includes: inline and reference links, images, and include directives
    (``{{#include path}}``, ``{% include path %}``, ``!include path``). Fenced code, inline code and HTML comments are not links
    (they show a link, or hold one out of use), so nothing in them counts; URLs and bare anchors are left out. Targets come back
    as written, with any ``#fragment`` or ``?query`` removed."""
    text = HTML_COMMENT.sub(" ", FENCE.sub(" ", text))
    text = INLINE_CODE.sub(" ", text)
    found = INLINE_LINK.findall(text) + REFERENCE_LINK.findall(text)
    found += [x for groups in INCLUDE.findall(text) for x in groups if x]
    out: List[str] = []
    for target in found:
        target = re.split(r"[#?]", target.strip(), maxsplit=1)[0]
        if target and not re.match(r"^([A-Za-z][A-Za-z0-9+.-]*:|//)", target):
            out.append(target)
    return out


def declared_owner(node) -> str:
    """The solution id a class declares through ``@implementation("id", ...)`` or ``@solution("id", ...)``, or ''."""
    for deco in getattr(node, "decorator_list", []):
        if isinstance(deco, ast.Call) and deco.args and isinstance(deco.args[0], ast.Constant) and isinstance(deco.args[0].value, str):
            func = deco.func.attr if isinstance(deco.func, ast.Attribute) else getattr(deco.func, "id", "")
            if func in ("implementation", "solution"):
                return deco.args[0].value
    return ""


class Code:
    """Modules of the package, their imports, and which solutions each module carries."""

    def __init__(self, cfg, solutions: Dict[str, Dict[str, str]], implementations: List[Dict[str, str]],
                 selected: Dict[str, Dict[str, str]], components: List[Dict[str, str]] = ()):
        self.root = cfg.root
        self.read_package(cfg)
        self.imports: Dict[str, Set[str]] = {m: self.imports_of(m) for m in self.files}
        self.index_regions()
        self.map_modules(solutions, implementations)
        self.shared = {m for m in self.files if sum(1 for sid in self.modules if m in self.modules[sid]) > 1}
        self.read_regions()
        self.owned = self.ownership(cfg, components)
        self.documents = self.document_files(cfg)
        self.document_owners = self.document_ownership(cfg, components, selected)
        self.links: Dict[str, Set[str]] = {d: self.links_of(d) for d in self.document_owners}
        self.read_declarations(solutions, selected)

    def read_declarations(self, solutions: Dict[str, Dict[str, str]], selected: Dict[str, Dict[str, str]]) -> None:
        """What the solutions and selected implementations declare: selected modules, interface names, @solution ids, assemblers."""
        self.selected_module = {sid: self.module_of(r.get("filepath", "")) for sid, r in selected.items() if r}
        self.interface: Dict[str, List[str]] = {sid: ids(r.get("interface_name") or "") for sid, r in solutions.items()}   # every name of the cell, never the cell as one string
        self.declared = {sid for text in self.source.values() for sid in re.findall(r"@solution\(\s*[\"']([\w.-]+)[\"']", text)}
        self.assemblers = {m for m, text in self.source.items() if "Assembler(" in text or "assemble_defaults(" in text}

    def read_package(self, cfg) -> None:
        """Find the package's modules and read their source, syntax trees and executable tokens."""
        pkg_dir = cfg.root / (cfg.package_dir or cfg.package or "")
        self.files: Dict[str, Path] = {}
        if cfg.package and pkg_dir.is_dir():
            for f in pkg_dir.rglob("*.py"):
                if "__pycache__" not in f.parts:
                    self.files[dotted_name(cfg.package, pkg_dir, f)] = f
        self.source = {m: f.read_text(encoding="utf-8", errors="replace") for m, f in self.files.items()}
        self.trees = {m: tree_of(self.files[m]) for m in self.source}
        self.tokens = {m: executable_tokens(text, self.trees[m]) for m, text in self.source.items()}

    def index_regions(self) -> None:
        """Index the classes each module declares for a solution: (module, solution id) to the class nodes."""
        self.region_nodes: Dict[Tuple[str, str], list] = defaultdict(list)    # (module, solution id) -> the classes it declares there
        for m, tree in self.trees.items():
            for node in (tree.body if tree is not None else []):
                owner = declared_owner(node)
                if owner:
                    self.region_nodes[(m, owner)].append(node)

    def map_modules(self, solutions, implementations) -> None:
        """Map each solution to the modules its implementation records and ``@implementation`` declarations name."""
        self.modules: Dict[str, Set[str]] = defaultdict(set)
        for row in implementations:
            module = self.module_of(row.get("filepath", ""))
            if module:
                self.modules[row["solution_id"]].add(module)
        for m, text in self.source.items():
            for sid in re.findall(r"@implementation\(\s*[\"']([\w.-]+)[\"']", text):
                if sid in solutions:
                    self.modules[sid].add(m)

    def read_regions(self) -> None:
        """Tokens and imports of each solution's own classes, in the modules several solutions share."""
        self.region_tokens: Dict[Tuple[str, str], List[str]] = {}
        self.region_imports: Dict[Tuple[str, str], Set[str]] = {}
        for (m, sid), nodes in self.region_nodes.items():
            if m in self.shared:
                self.region_tokens[(m, sid)] = executable_tokens(self.source[m], self.trees[m], nodes)
                self.region_imports[(m, sid)] = self.imports_of(m, nodes)

    def ownership(self, cfg, components) -> Dict[str, Set[str]]:
        """{module: solutions its components.csv rows list}, by the same path globs the structure check uses. The package's own
        ``__init__`` is left out: every ``from . import x`` reaches it, so it says nothing about one solution."""
        out: Dict[str, Set[str]] = defaultdict(set)
        relative = {m: f.relative_to(self.root).as_posix() for m, f in self.files.items() if m != cfg.package}   # once per file, not once per row and pattern
        for row in components or ():
            patterns = [glob_re(p) for p in ids(row.get("path", ""))]
            owners = set(ids(row.get("solutions", "")))
            if not owners:
                continue
            for m, rel in relative.items():
                if any(rx.match(rel) for rx in patterns):
                    out[m] |= owners
        return out

    def document_files(self, cfg) -> Dict[str, Path]:
        """{posix path from the root: file} of every markdown document of the project (hidden and vendored folders left out)."""
        out: Dict[str, Path] = {}
        for folder, names, files in os.walk(self.root):
            names[:] = [n for n in names if not n.startswith(".") and n not in SKIPPED_FOLDERS]
            for name in files:
                if name.lower().endswith(DOCUMENT_SUFFIXES):
                    path = Path(folder) / name
                    out[path.relative_to(self.root).as_posix()] = path
        return out

    def document_ownership(self, cfg, components, selected) -> Dict[str, Set[str]]:
        """{document: solutions that own it}. A document is a solution's when a ``components.csv`` row names it in its ``documents``
        cell (``path=solution-id``: the row's path owns the file, this says whose document it is) or when the solution's selected
        implementation names it as its ``filepath``: the document is the implementation. A folder a component owns as a whole
        (``docs/**``) makes no document anyone's. Only documents that exist are counted."""
        out: Dict[str, Set[str]] = defaultdict(set)
        for row in components or ():
            for path, solution in document_entries(row.get("documents", "")):
                if solution and path in self.documents:
                    out[path].add(solution)
        for sid, row in selected.items():
            rel = ((row or {}).get("filepath") or "").strip().split("::")[0]
            if rel in self.documents:
                out[rel].add(sid)
        return out

    def links_of(self, document: str) -> Set[str]:
        """The documents ``document`` links to or includes, as paths from the root, from its actual markdown links."""
        text = self.documents[document].read_text(encoding="utf-8", errors="replace")
        folder = posixpath.dirname(document)
        out: Set[str] = set()
        for target in document_targets(text):
            target = urllib.parse.unquote(target)
            path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else posixpath.join(folder, target))
            if not path.startswith("..") and path != document:
                out.add(path)
        return out

    def documents_of(self, solution: str) -> Set[str]:
        return {d for d, owners in self.document_owners.items() if solution in owners}

    def linked(self, user: str, used: str) -> bool:
        """A document that only ``user`` owns links to or includes a document that only ``used`` owns. Both ends must be one
        solution's alone: a document several solutions own (a whole ``docs/**`` folder, say) does not say which of them a link
        means, so it is no evidence on either side."""
        mine = {d for d in self.documents_of(user) if self.document_owners[d] == {user}}
        theirs = {d for d in self.documents_of(used) if self.document_owners[d] == {used}}
        return any(self.links[d] & theirs for d in mine)

    def owned_by(self, solution: str) -> Set[str]:
        return {m for m, owners in self.owned.items() if solution in owners}

    def module_of(self, filepath: str) -> str:
        filepath = (filepath or "").strip().split("::")[0]
        if not filepath.endswith(".py"):
            return ""
        full = (self.root / filepath).resolve()
        for m, f in self.files.items():
            if f.resolve() == full:
                return m
        return ""

    def own_tokens(self, solution: str, module: str) -> List[str]:
        """The executable tokens of ``solution`` in ``module``: the whole module, or, in a module several solutions share, only
        the classes that solution declares there (a module shared by solutions with no class of this one is scored whole)."""
        return self.region_tokens.get((module, solution), self.tokens[module])

    def own_imports(self, solution: str, module: str) -> Set[str]:
        return self.region_imports.get((module, solution), self.imports[module])

    def imports_of(self, module: str, nodes=None) -> Set[str]:
        tree = self.trees.get(module)
        if tree is None:
            return set()
        out: Set[str] = set()
        package = module.split(".") if self.files[module].name == "__init__.py" else module.split(".")[:-1]
        for node in walk_tops(nodes if nodes is not None else [tree]):
            out.update(statement_modules(node, package))
        return {m for m in out if m in self.files}

    def typed_need(self, user: str, used: str) -> bool:
        """The user's selected implementation module has a constructor parameter annotated with the used's interface class."""
        names, module = self.interface.get(used, []), self.selected_module.get(user, "")
        tree = self.trees.get(module) if module else None
        if not names or tree is None:
            return False
        own = self.region_nodes.get((module, user)) if module in self.shared else None
        inits = (n for n in walk_tops(own or [tree]) if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        return any(annotated_with(arg, names) for node in inits for arg in node.args.args + node.args.kwonlyargs)

    def imported_by(self, user: str, module: str, used: str, used_modules: Set[str]) -> bool:
        """``user``'s part of ``module`` imports a module of ``used``. A module the used shares with other solutions counts only when
        the import names a class the used declares there or its interface (importing the shared file says nothing about one arm)."""
        for target in self.own_imports(user, module) & used_modules:
            if target not in self.shared:
                return True
            wanted = set(self.interface.get(used, [])) | {getattr(n, "name", "") for n in self.region_nodes.get((target, used), [])}
            if self.names_imported(user, module, target) & (wanted - {""}):
                return True
        return False

    def names_imported(self, user: str, module: str, target: str) -> Set[str]:
        """The names ``user``'s part of ``module`` imports from ``target``."""
        tree = self.trees.get(module)
        nodes = self.region_nodes.get((module, user)) if module in self.shared else None
        out: Set[str] = set()
        package = module.split(".") if self.files[module].name == "__init__.py" else module.split(".")[:-1]
        for node in walk_tops([top for top in (nodes or [tree]) if top is not None]):
            if isinstance(node, ast.ImportFrom) and import_base(package, node.level, node.module) == target:
                out.update(a.name for a in node.names)
        return out

    def names_interface(self, user: str, used: str, modules: Set[str]) -> bool:
        """Executable code of a module of the user names the used's id or its interface class."""
        named = [re.compile(r"\b" + re.escape(name) + r"\b") for name in self.interface.get(used, [])]
        return any(position(used, {}, token) >= 0 or any(pattern.search(token) for pattern in named)
                   for m in modules for token in self.own_tokens(user, m))

    def weak_evidence(self, user: str, used: str, mu: Set[str], mc: Set[str]) -> str:
        """The weak evidence (W1 to W3) that ``user`` uses ``used``, or ''."""
        if any(self.imports.get(y, set()) & mc for m in mu for y in self.own_imports(user, m)):
            return "W1"
        if mu & self.assemblers and used in self.declared:
            return "W2"
        return "W3" if self.bridged_by_third(mu, mc) else ""

    def bridged_by_third(self, mu: Set[str], mc: Set[str]) -> bool:
        """Whether a module outside both sets imports from each of them."""
        return any(w not in mu and w not in mc and imported & mu and imported & mc for w, imported in self.imports.items())

    def evidence(self, user: str, used: str) -> str:
        """The strongest evidence that ``user`` uses ``used`` (E1 to E5, then W1, W2, W3), '' for none, 'n/a' when either end
        has no module."""
        mu, mc = self.modules.get(user, set()), self.modules.get(used, set())
        if not (mu or self.documents_of(user)) or not (mc or self.documents_of(used)):
            return "n/a"
        if self.linked(user, used):
            return "E5"
        if not mu or not mc:
            return ""
        return self.import_evidence(user, used, mu, mc) or self.weak_evidence(user, used, mu, mc)

    def import_evidence(self, user: str, used: str, mu: Set[str], mc: Set[str]) -> str:
        """The import-based evidence (E1 to E4) that ``user`` uses ``used``, or ''."""
        if any(self.imported_by(user, m, used, mc) for m in mu):
            return "E1"
        if self.names_interface(user, used, mu):
            return "E2"
        if self.typed_need(user, used):
            return "E3"
        return "E4" if any(self.through_owned(user, m, used, mc) for m in mu) else ""

    def through_owned(self, user: str, module: str, used: str, used_modules: Set[str]) -> bool:
        """``user``'s part of ``module`` imports a module that only the user's component owns, and that module imports one that only
        the used's component owns (or one the used implements in a file no other solution shares). components.csv is the record that
        says whose a module is; a module owned by several solutions, a chain through someone else's module and the package
        ``__init__`` are not evidence, because there the import does not say which solution is meant."""
        mine = self.owned_by(user)
        theirs = {m for m in self.owned_by(used) if self.owned[m] == {used}} | {m for m in used_modules if m not in self.shared}
        theirs -= self.owned_by(user)
        return any(self.imports.get(x, set()) & theirs for x in self.own_imports(user, module) if x in mine and x != module)

    def import_edges(self, among: Set[str]) -> Set[Tuple[str, str]]:
        return {(a, b) for a in among for b in among
                if a != b and any(self.imports[m] & self.modules.get(b, set()) for m in self.modules.get(a, set()))}
