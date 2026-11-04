"""Solution coherence of every intent, model-free: the first cascade stage of `metric-solution-coherence`, and rule S38.

Run as ``python3 -m esoi.coherence [root] [--json] [--gate] [--pairs]`` from a project. Standard library plus esoi's own config,
intent discovery and records. It reads the records and the package's Python source; it runs nothing and calls no model.

The hierarchy is the ``uses_solution_ids`` of each solution's SELECTED implementation (the composition that runs; a rival's
uses are an alternative, not the structure). Per intent folder:

  paragraph (M1, S38)  solution_coherence is one paragraph that names every solution of the intent and no solution of another
                       intent no edge reaches; it states every uses edge in one clause (split on . ; : ! ?) that names the user
                       before the used with at least MIN_CLAUSE_WORDS words between them that are not solution names (the words that
                       say how one uses the other); no sentence
                       names more than ``max_names_per_sentence`` solutions (default max_fan_out + 1); and when four or more
                       clauses state edges, no more than half of them share one wording once the names are taken out. A clause
                       that opens with "It" speaks of the first solution the clause before it names (so "card-store keeps the
                       cards. It finds them by meaning through index-by-meaning." states card-store -> index-by-meaning). So a
                       list of names, one sentence that names everything, or one template repeated per edge states nothing.
                       What stays unseen (whether the paragraph reads as one line of thought) is the model-judge stage's.
  roots (M5, S38)      the top intent has one root; a sub-intent's roots are used by the implementation it arises from; every
                       solution is reachable from a root
  diagram (M3, S39)    esoi's generated diagram.md is current and every edge is labelled (the provider's outputs is filled)
  code (M2, S39)       for each uses edge whose two ends both have Python modules (coverage = checkable / all edges), the
                       strongest evidence the code shows in the user's direction:
                         E1  a module of the user imports a module of the used directly           (strong)
                         E2  executable code of a module of the user names the used's id or its interface class: an
                             identifier, attribute, import, annotation, decorator or call argument, or a string literal used as a
                             value. A docstring, a comment and any bare string statement are prose and never count   (strong)
                         E3  the user's implementation class takes a parameter typed with the used's interface: a need the
                             esoi Assembler injects                                               (strong)
                         W1  a module of the user imports one that imports the used               (weak, reported)
                         W2  a module of the user builds an esoi Assembler over a scope that declares the used (weak)
                         W3  a third module imports both ends                                     (weak)
                       Evidence is attributed per solution: in a module several solutions share (one interfaces file holding
                       many arms), a solution's evidence is only what its own classes (declared with ``@implementation`` or
                       ``@solution``) contain, and importing the shared file counts only when the import names the used's class.
                       precision = strong / checkable. The same evidence is scored on every ordered pair of solutions with
                       modules that is NOT a uses edge (the base rate); lift = precision / base rate. A sub-intent's host edges
                       are checked the same way (the host implementation's module against the sub-intent's roots).
  balance (M4, S38)    no implementation uses more than ``max_fan_out`` solutions of its intent; no solution lies more than
                       ``max_depth`` edges below a root

Limits come from the project's esoi.toml ``[rules.S38]``: ``max_fan_out = 9, max_depth = 4``, ``min_lift`` and
``max_names_per_sentence``, and the limits per intent, ``[rules.S38.floors.<intent-id>] precision = .., coverage = ..,
min_lift = .., max_fan_out = .., max_names_per_sentence = ..`` (each defaults to the repository-wide value). An intent that records
no uses edges has an undefined lift, reported as n/a and never failed; the flat
``code_floor`` and ``coverage_floor`` are the floors of an intent with no table of its own. The defaults below apply when absent. ``--gate`` exits 1 unless every intent
passes paragraph, roots, diagram and balance and its precision, coverage and lift are at or above their floors.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from esoi import config as esoi_config
from esoi import intents as esoi_intents

DEFAULTS = {"max_fan_out": 9, "max_depth": 4, "code_floor": 1.0, "coverage_floor": 0.0, "min_lift": 1.0}
MIN_CLAUSE_WORDS = 3          # words between the user and the used, names aside ("a uses b" has one: not enough)
STRONG = ("E1", "E2", "E3")
WEAK = ("W1", "W2", "W3")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


def executable_tokens(text: str, tree, nodes=None) -> List[str]:
    """The names and string values the executable code of a Python module holds: identifiers, attributes, imported names,
    parameter and keyword names, and string literals used as values. Docstrings and any other bare string statement are
    documentation and left out, and so is every comment (a comment is not in the syntax tree). A module that does not parse
    falls back to its text with comment lines removed. ``nodes`` limits the walk to those syntax nodes (one solution's classes in
    a module several solutions share)."""
    if tree is None:
        return [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    walked = [n for top in (nodes if nodes is not None else [tree]) for n in ast.walk(top)]
    prose = {id(n.value) for n in walked if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
             and isinstance(n.value.value, str)}
    out: List[str] = []
    for node in walked:
        if isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(node.name)
        elif isinstance(node, ast.arg):
            out.append(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            out.append(node.arg)
        elif isinstance(node, ast.alias):
            out.append(node.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:
            out.append(node.value)
    return out


def declared_owner(node) -> str:
    """The solution id a class declares through ``@implementation("id", ...)`` or ``@solution("id", ...)``, or ''."""
    for deco in getattr(node, "decorator_list", []):
        if isinstance(deco, ast.Call) and deco.args and isinstance(deco.args[0], ast.Constant) and isinstance(deco.args[0].value, str):
            func = deco.func.attr if isinstance(deco.func, ast.Attribute) else getattr(deco.func, "id", "")
            if func in ("implementation", "solution"):
                return deco.args[0].value
    return ""


def ids(text: str) -> List[str]:
    return [x.strip() for x in (text or "").replace(",", ";").split(";") if x.strip()]


def read(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def position(sid: str, row: Dict[str, str], text: str) -> int:
    """Where ``text`` first names the solution, by id or by name (ignoring case and spacing), or -1."""
    found = re.search(r"(?<![\w@/-])" + re.escape(sid) + r"(?![\w-])", text)
    best = found.start() if found else -1
    name = " ".join((row.get("name") or "").lower().split())
    if name:
        at = " ".join(text.lower().split()).find(name)
        if at >= 0 and (best < 0 or at < best):
            best = at
    return best


def sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def clauses(text: str) -> List[str]:
    return [c for c in re.split(r"(?<=[.;:!?])\s+", text.strip()) if c]


def other_words(clause: str, names: List[str]) -> int:
    """Words of a clause that are not part of a solution id or name it contains."""
    rest = clause
    for n in sorted(names, key=len, reverse=True):
        rest = re.sub(re.escape(n), " ", rest, flags=re.IGNORECASE)
    return len(WORD.findall(rest))


class Code:
    """Modules of the package, their imports, and which solutions each module carries."""

    def __init__(self, cfg, solutions: Dict[str, Dict[str, str]], implementations: List[Dict[str, str]],
                 selected: Dict[str, Dict[str, str]]):
        self.root = cfg.root
        pkg_dir = cfg.root / (cfg.package_dir or cfg.package or "")
        self.files: Dict[str, Path] = {}
        if cfg.package and pkg_dir.is_dir():
            for f in pkg_dir.rglob("*.py"):
                if "__pycache__" not in f.parts:
                    parts = [cfg.package] + list(f.relative_to(pkg_dir).with_suffix("").parts)
                    if parts[-1] == "__init__":
                        parts = parts[:-1]
                    self.files[".".join(parts)] = f
        self.source = {m: f.read_text(encoding="utf-8", errors="replace") for m, f in self.files.items()}
        self.trees = {}
        for m, text in self.source.items():
            try:
                self.trees[m] = ast.parse(text)
            except SyntaxError:
                self.trees[m] = None
        self.tokens = {m: executable_tokens(text, self.trees[m]) for m, text in self.source.items()}
        self.imports: Dict[str, Set[str]] = {m: self.imports_of(m) for m in self.files}
        self.region_nodes: Dict[Tuple[str, str], list] = defaultdict(list)    # (module, solution id) -> the classes it declares there
        for m, tree in self.trees.items():
            for node in (tree.body if tree is not None else []):
                owner = declared_owner(node)
                if owner:
                    self.region_nodes[(m, owner)].append(node)
        self.modules: Dict[str, Set[str]] = defaultdict(set)
        for row in implementations:
            module = self.module_of(row.get("filepath", ""))
            if module:
                self.modules[row["solution_id"]].add(module)
        for m, text in self.source.items():
            for sid in re.findall(r"@implementation\(\s*[\"']([\w.-]+)[\"']", text):
                if sid in solutions:
                    self.modules[sid].add(m)
        self.shared = {m for m in self.files if sum(1 for sid in self.modules if m in self.modules[sid]) > 1}
        self.region_tokens: Dict[Tuple[str, str], List[str]] = {}
        self.region_imports: Dict[Tuple[str, str], Set[str]] = {}
        for (m, sid), nodes in self.region_nodes.items():
            if m in self.shared:
                self.region_tokens[(m, sid)] = executable_tokens(self.source[m], self.trees[m], nodes)
                self.region_imports[(m, sid)] = self.imports_of(m, nodes)
        self.selected_module = {sid: self.module_of(r.get("filepath", "")) for sid, r in selected.items() if r}
        self.interface = {sid: (r.get("interface_name") or "").strip() for sid, r in solutions.items()}
        self.declared = {sid for text in self.source.values() for sid in re.findall(r"@solution\(\s*[\"']([\w.-]+)[\"']", text)}
        self.assemblers = {m for m, text in self.source.items() if "Assembler(" in text or "assemble_defaults(" in text}

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
        is_pkg = self.files[module].name == "__init__.py"
        for node in (n for top in (nodes if nodes is not None else [tree]) for n in ast.walk(top)):
            if isinstance(node, ast.Import):
                out.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = module.split(".")
                    if not is_pkg:
                        parts = parts[:-1]
                    parts = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
                    base = ".".join(parts + ([base] if base else []))
                out.add(base)
                out.update(f"{base}.{a.name}" for a in node.names)
        return {m for m in out if m in self.files}

    def typed_need(self, user: str, used: str) -> bool:
        """The user's selected implementation module has a constructor parameter annotated with the used's interface class."""
        name, module = self.interface.get(used, ""), self.selected_module.get(user, "")
        tree = self.trees.get(module) if module else None
        if not name or tree is None:
            return False
        own = self.region_nodes.get((module, user)) if module in self.shared else None
        for node in (n for top in (own or [tree]) for n in ast.walk(top)):
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for arg in node.args.args + node.args.kwonlyargs:
                    if arg.annotation is not None and name in ast.unparse(arg.annotation).replace("'", "").replace('"', "").split("."):
                        return True
        return False

    def imported_by(self, user: str, module: str, used: str, used_modules: Set[str]) -> bool:
        """``user``'s part of ``module`` imports a module of ``used``. A module the used shares with other solutions counts only when
        the import names a class the used declares there or its interface (importing the shared file says nothing about one arm)."""
        for target in self.own_imports(user, module) & used_modules:
            if target not in self.shared:
                return True
            wanted = {self.interface.get(used, "")} | {getattr(n, "name", "") for n in self.region_nodes.get((target, used), [])}
            if self.names_imported(user, module, target) & (wanted - {""}):
                return True
        return False

    def names_imported(self, user: str, module: str, target: str) -> Set[str]:
        """The names ``user``'s part of ``module`` imports from ``target``."""
        tree = self.trees.get(module)
        nodes = self.region_nodes.get((module, user)) if module in self.shared else None
        out: Set[str] = set()
        for node in (n for top in (nodes or [tree]) for n in (ast.walk(top) if top is not None else [])):
            if isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = module.split(".")
                    if self.files[module].name != "__init__.py":
                        parts = parts[:-1]
                    parts = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
                    base = ".".join(parts + ([base] if base else []))
                if base == target:
                    out.update(a.name for a in node.names)
        return out

    def evidence(self, user: str, used: str) -> str:
        """The strongest evidence that ``user`` uses ``used`` (E1, E2, E3, then W1, W2, W3), '' for none, 'n/a' when either end
        has no module."""
        mu, mc = self.modules.get(user, set()), self.modules.get(used, set())
        if not mu or not mc:
            return "n/a"
        if any(self.imported_by(user, m, used, mc) for m in mu):
            return "E1"
        iface = self.interface.get(used)
        for m in mu:
            if any(position(used, {}, token) >= 0 or (iface and re.search(r"\b" + re.escape(iface) + r"\b", token))
                   for token in self.own_tokens(user, m)):
                return "E2"
        if self.typed_need(user, used):
            return "E3"
        if any(self.imports.get(y, set()) & mc for m in mu for y in self.own_imports(user, m)):
            return "W1"
        if mu & self.assemblers and used in self.declared:
            return "W2"
        for w, imported in self.imports.items():
            if w not in mu and w not in mc and imported & mu and imported & mc:
                return "W3"
        return ""

    def import_edges(self, among: Set[str]) -> Set[Tuple[str, str]]:
        return {(a, b) for a in among for b in among
                if a != b and any(self.imports[m] & self.modules.get(b, set()) for m in self.modules.get(a, set()))}


def selected_record(sid: str, row: Dict[str, str], every_impl: List[Dict[str, str]]) -> Dict[str, str]:
    from esoi.records import match_implementations
    mine = {r["implementation_id"]: r for r in every_impl if r.get("solution_id") == sid}
    chosen = (row.get("selected") or "").strip()
    if not chosen:
        return {}
    hit = match_implementations(sid, [chosen], mine)[0].get(chosen, "")
    return mine.get(hit, {})


def limits(cfg, intent_id: str = "") -> Dict[str, float]:
    """The limits of one intent: its own ``[rules.S38.floors.<intent-id>]`` table (``precision``, ``coverage``, ``min_lift``,
    ``max_fan_out``, ``max_names_per_sentence``), else the repository-wide values, else the defaults."""
    out = dict(DEFAULTS)
    for key in ("max_fan_out", "max_depth", "min_lift", "code_floor", "coverage_floor"):
        out[key] = cfg.option("S38", key, out[key])
    own = (cfg.option("S38", "floors", {}) or {}).get(intent_id, {})
    if "precision" in own:
        out["code_floor"] = own["precision"]
    if "coverage" in own:
        out["coverage_floor"] = own["coverage"]
    for key in ("min_lift", "max_fan_out"):   # a justified, written limit of one intent; the repository-wide value is the default
        if key in own:
            out[key] = own[key]
    out["max_names_per_sentence"] = own.get("max_names_per_sentence",
                                            cfg.option("S38", "max_names_per_sentence", out["max_fan_out"] + 1))
    return out


def reaches(uses: Dict[str, List[str]], start: str, goal: str) -> bool:
    seen, stack = set(), [start]
    while stack:
        x = stack.pop()
        for t in uses.get(x, ()):
            if t == goal:
                return True
            if t not in seen:
                seen.add(t)
                stack.append(t)
    return False


def check(root: Path, pairs: bool = True) -> Dict[str, object]:
    cfg = esoi_config.load(root)
    lim = limits(cfg)
    found = esoi_intents.discover(cfg)
    overall = lim
    every_solution: Dict[str, Dict[str, str]] = {}
    every_impl: List[Dict[str, str]] = []
    home: Dict[str, str] = {}
    for intent_id, folder in esoi_intents.folders(cfg):
        for r in read(folder / "solutions.csv"):
            every_solution[r["solution_id"]] = r
            home[r["solution_id"]] = intent_id
        every_impl += read(folder / "implementations.csv")
    impl_by_id = {r["implementation_id"]: r for r in every_impl}
    selected = {sid: selected_record(sid, r, every_impl) for sid, r in every_solution.items()}
    uses = {sid: [t for t in ids(rec.get("uses_solution_ids", "")) if t != sid] for sid, rec in selected.items()}
    code = Code(cfg, every_solution, every_impl, selected)
    edges_all = {(a, b) for a in uses for b in uses[a] if b in every_solution}
    base = Counter()
    if pairs:
        with_code = [s for s in every_solution if code.modules.get(s)]
        for a in with_code:
            for b in with_code:
                if a != b and (a, b) not in edges_all:
                    base[code.evidence(a, b)] += 1
    base_n = sum(base.values())
    base_rate = round(sum(base[k] for k in STRONG) / base_n, 3) if base_n else None
    report = []
    for intent in found:
        lim = limits(cfg, intent.intent_id)   # the floors of this intent
        mine = sorted(s for s, h in home.items() if h == intent.intent_id)
        inner = {(a, b) for a in mine for b in uses[a] if b in mine}
        used_inside = {b for _, b in inner}
        roots = [s for s in mine if s not in used_inside]
        host_sid, host_uses = "", set()
        if not intent.is_top:
            host = impl_by_id.get(intent.row.get("implements", "").strip(), {})
            host_sid, host_uses = host.get("solution_id", ""), set(ids(host.get("uses_solution_ids", "")))
        problems: Dict[str, List[str]] = defaultdict(list)
        if intent.is_top and len(roots) != 1:
            problems["roots"].append(f"{len(roots)} roots, the top intent has one: {', '.join(roots)}")
        if not intent.is_top:
            loose = [r for r in roots if r not in host_uses]
            if loose:
                problems["roots"].append(f"roots not used by {intent.row.get('implements')}: {', '.join(loose)}")
        depth = {r: 0 for r in roots}
        stack = list(roots)
        while stack:
            x = stack.pop()
            for t in uses[x]:
                if t in mine and depth.get(t, -1) < depth[x] + 1 and depth[x] + 1 <= len(mine):
                    depth[t] = depth[x] + 1
                    stack.append(t)
        unreached = [s for s in mine if s not in depth]
        if unreached:
            problems["roots"].append(f"unreachable from a root: {', '.join(unreached)}")
        para = (intent.row.get("solution_coherence") or "").strip()
        stated: Dict[str, str] = {}
        if not para:
            problems["paragraph"].append("solution_coherence is empty")
        else:
            if re.search(r"\n\s*\n", para):
                problems["paragraph"].append("more than one paragraph")
            missing = [s for s in mine if position(s, every_solution[s], para) < 0]
            if missing:
                problems["paragraph"].append(f"names {len(mine) - len(missing)} of {len(mine)} solutions; missing: {', '.join(missing)}")
            allowed = set(mine) | {b for a in mine for b in uses[a]} | host_uses | {host_sid} | {
                s for s in every_solution if any(h in mine for h in uses[s])}
            stray = [s for s in every_solution if s not in allowed and position(s, {}, para) >= 0]
            if stray:
                problems["paragraph"].append(f"names solutions of other intents no edge reaches: {', '.join(stray)}")
            crowded = []
            for s in sentences(para):
                n = sum(1 for sid in every_solution if position(sid, every_solution[sid], s) >= 0)
                if n > lim["max_names_per_sentence"]:
                    crowded.append(f"{n} in \"{s[:60]}...\"")
            if crowded:
                problems["paragraph"].append(f"sentences naming more than {lim['max_names_per_sentence']} solutions: {'; '.join(crowded)}")
            parts = clauses(para)
            subject: List[str] = []     # a clause opening with "It" speaks of the first solution the clause before it names
            for i, c in enumerate(parts):
                named_at = sorted((position(sid, every_solution[sid], c), sid) for sid in mine
                                  if position(sid, every_solution[sid], c) >= 0)
                if re.match(r"^\s*It\b", c) and i and subject[i - 1]:
                    subject.append(subject[i - 1])
                else:
                    subject.append(named_at[0][1] if named_at else "")
            subject_any: List[str] = []
            for i, c in enumerate(parts):
                every_named = sorted((position(sid, every_solution[sid], c), sid) for sid in every_solution
                                     if position(sid, every_solution[sid], c) >= 0)
                subject_any.append(subject_any[i - 1] if re.match(r"^\s*It\b", c) and i and subject_any[i - 1]
                                   else (every_named[0][1] if every_named else ""))
            for a, b in sorted(inner):
                for i, c in enumerate(parts):
                    pa, pb = position(a, every_solution[a], c), position(b, every_solution[b], c)
                    if pa < 0 and re.match(r"^\s*It\b", c) and subject[i] == a:
                        pa = 0
                    if 0 <= pa < pb or (pa == 0 and pb > 0):
                        names = [x for x in (a, b, every_solution[a].get("name", ""), every_solution[b].get("name", "")) if x]
                        named_here = [sid for sid in every_solution if position(sid, {}, c) >= 0]
                        if other_words(c[max(pa, 0):pb], names + named_here) >= MIN_CLAUSE_WORDS:   # the words that join them
                            stated[f"{a}->{b}"] = c
                            break
            skeletons = Counter(tuple(w.lower() for w in WORD.findall(re.sub("|".join(re.escape(x) for x in sorted(
                [sid for sid in every_solution if position(sid, {}, c) >= 0], key=len, reverse=True)) or "$^", " ", c)))
                for c in set(stated.values()))
            if len(set(stated.values())) >= 4 and skeletons and skeletons.most_common(1)[0][1] * 2 > len(set(stated.values())):
                problems["paragraph"].append(f"templated: {skeletons.most_common(1)[0][1]} of {len(set(stated.values()))} clauses "
                                             f"that state edges share the words {' '.join(skeletons.most_common(1)[0][0])!r}")
            walk = {s: list(t) for s, t in uses.items()}
            if host_sid:
                walk.setdefault(host_sid, []).extend(host_uses)
            claimed = []
            for i, c in enumerate(parts):
                named_at = sorted((position(sid, every_solution[sid], c), sid) for sid in every_solution
                                  if position(sid, every_solution[sid], c) >= 0)
                if re.match(r"^\s*It\b", c) and i and subject_any[i - 1]:
                    first, start = subject_any[i - 1], 0
                elif named_at:
                    start, first = named_at[0]
                else:
                    continue
                for at, sid in named_at:
                    if sid == first or at <= start:
                        continue
                    names = [x for x in (first, sid, every_solution[first].get("name", ""), every_solution[sid].get("name", "")) if x]
                    named_here = [other for other in every_solution if position(other, {}, c) >= 0]
                    if other_words(c[max(start, 0):at], names + named_here) >= MIN_CLAUSE_WORDS and not reaches(walk, first, sid):
                        claimed.append(f"{first}->{sid} in \"{c[:80]}\"")
            if claimed:
                problems["paragraph"].append("states a relation the records do not hold (no uses path from the first to the second): "
                                             + "; ".join(dict.fromkeys(claimed)))
            unstated = sorted(f"{a}->{b}" for a, b in inner if f"{a}->{b}" not in stated)
            if unstated:
                problems["paragraph"].append("uses edges not stated user first in one clause with words of its own: "
                                             + ", ".join(unstated))
        all_edges = {(b, a) for r in every_impl if r.get("solution_id") in mine
                     for a in [r["solution_id"]] for b in ids(r.get("uses_solution_ids", "")) if b in mine and b != a}
        unlabelled = sorted({b for b, _ in all_edges if not (every_solution[b].get("outputs") or "").strip()})
        if unlabelled:
            problems["diagram"].append(f"edges with no label (the provider's outputs is empty): {', '.join(unlabelled)}")
        try:
            from esoi import diagram as esoi_diagram
            from esoi.registry import load as load_registry
            page = intent.folder / esoi_diagram.FILE
            want_text = esoi_diagram.render(load_registry(cfg), intent)
            if want_text and (not page.is_file() or page.read_text(encoding="utf-8") != want_text):
                problems["diagram"].append(f"{page.relative_to(cfg.root)} is not current (run `esoi diagram`)")
        except ImportError:
            problems["diagram"].append("this esoi has no `esoi diagram` (template version 4 and later)")
        checked = set(inner) | ({(host_sid, r) for r in roots if r in host_uses} if host_sid else set())
        verdicts = {f"{a}->{b}": code.evidence(a, b) for a, b in sorted(checked)}
        checkable = {e: v for e, v in verdicts.items() if v != "n/a"}
        strong = [e for e, v in checkable.items() if v in STRONG]
        precision = round(len(strong) / len(checkable), 3) if checkable else None
        coverage = round(len(checkable) / len(verdicts), 3) if verdicts else None
        lift = round(precision / base_rate, 2) if precision is not None and base_rate else None
        if precision is not None and precision < lim["code_floor"]:
            problems["code"].append(f"precision {precision} below the floor {lim['code_floor']}; not shown by strong evidence: "
                                    + ", ".join(f"{e} ({v or 'none'})" for e, v in checkable.items() if v not in STRONG))
        if coverage is not None and coverage < lim["coverage_floor"]:
            problems["code"].append(f"coverage {coverage} below the floor {lim['coverage_floor']}: edges with an end that has no code: "
                                    + ", ".join(e for e, v in verdicts.items() if v == "n/a"))
        if lift is not None and lift < lim["min_lift"]:
            problems["code"].append(f"lift {lift} below {lim['min_lift']}: the evidence fires on non-edges as often as on edges")
        reach = {}
        for s in mine:
            out, st = set(), [s]
            while st:
                x = st.pop()
                for t in uses.get(x, ()):
                    if t not in out:
                        out.add(t)
                        st.append(t)
            reach[s] = out
        code_edges = code.import_edges(set(mine))
        on_path = [e for e in code_edges if e[1] in reach[e[0]] or e[0] in reach[e[1]]]
        fan = {s: len([t for t in uses[s] if t in mine]) for s in mine}
        wide = [f"{s} ({n})" for s, n in fan.items() if n > lim["max_fan_out"]]
        deep = [f"{s} ({d})" for s, d in depth.items() if d > lim["max_depth"]]
        if wide:
            problems["balance"].append(f"fan-out above {lim['max_fan_out']}: {', '.join(wide)}")
        if deep:
            problems["balance"].append(f"deeper than {lim['max_depth']}: {', '.join(deep)}")
        report.append(dict(
            intent=intent.intent_id, solutions=len(mine), uses_edges=len(inner), roots=roots,
            max_fan_out=max(fan.values() or [0]), max_depth=max(depth.values() or [0]),
            paragraph_words=len(para.split()), paragraph_ok=not problems["paragraph"] and not problems["roots"],
            diagram_ok=not problems["diagram"], code_edges=len(verdicts), code_edges_checkable=len(checkable),
            code_edges_strong=len(strong), evidence=dict(Counter(verdicts.values())), code_precision=precision,
            code_coverage=coverage, code_lift=lift,
            code_lift_note="n/a (no recorded edges)" if not verdicts else "", code_import_edges=len(code_edges),
            code_recall=round(len(on_path) / len(code_edges), 3) if code_edges else None,
            verdicts=verdicts, wide={s: n for s, n in fan.items() if n > lim["max_fan_out"]},
            deep={s: d for s, d in depth.items() if d > lim["max_depth"]}, problems={k: v for k, v in problems.items() if v}))
    n = len(report) or 1
    summary = dict(
        intents=len(report), limits=overall, m1_paragraph_share=round(sum(r["paragraph_ok"] for r in report) / n, 3),
        m2_precision=[r["code_precision"] for r in report], m2_coverage=[r["code_coverage"] for r in report],
        m2_base_rate=base_rate, m2_base_pairs=base_n, m2_base_evidence=dict(base), m2_lift=[r["code_lift"] for r in report],
        m3_diagram_share=round(sum(r["diagram_ok"] for r in report) / n, 3),
        m4_max_fan_out=max([r["max_fan_out"] for r in report] or [0]), m4_max_depth=max([r["max_depth"] for r in report] or [0]),
        roots=sum(len(r["roots"]) for r in report), passed=all(not r["problems"] for r in report))
    return dict(summary=summary, intents=report)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="esoi.coherence", description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gate", action="store_true", help="exit 1 unless every intent passes")
    ap.add_argument("--no-pairs", action="store_true", help="skip the base rate over non-edges (faster)")
    args = ap.parse_args(argv)
    out = check(Path(args.root), pairs=not args.no_pairs)
    if args.json:
        print(json.dumps(out, indent=1))
    else:
        for r in out["intents"]:
            print(f"{r['intent']}: {r['solutions']} solutions, {r['uses_edges']} uses edges, roots {len(r['roots'])}, fan-out "
                  f"{r['max_fan_out']}, depth {r['max_depth']}, paragraph {'ok' if r['paragraph_ok'] else 'FAIL'} "
                  f"({r['paragraph_words']} words), diagram {'ok' if r['diagram_ok'] else 'FAIL'}, code: {r['code_edges_strong']} of "
                  f"{r['code_edges_checkable']} checkable edges strong (precision {r['code_precision']}, coverage {r['code_coverage']}, "
                  f"lift {r['code_lift_note'] or r['code_lift']}), evidence {r['evidence']}")
            for k, v in r["problems"].items():
                for line in v:
                    print(f"  {k}: {line}")
        print("summary:", json.dumps(out["summary"]))
    return 1 if args.gate and not out["summary"]["passed"] else 0


if __name__ == "__main__":
    sys.exit(main())
