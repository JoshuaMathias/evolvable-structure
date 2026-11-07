"""Records kept beside the code: where each record belongs, and moving the records there (or back to the structure folder).

The standard is in ``docs/reference/records-beside-code.md``. A repository opts in with ``[records] beside_code`` in
``esoi.toml``, a list of folders or globs (from the repository root) that may hold records next to the code they describe.
Each record then lives once, in one of those folders:

* an implementation row, in the host folder of the file it names in ``filepath`` (the nearest listed folder at or above the
  file's folder);
* a solution row, in the host folder of the lowest folder that holds all of its implementations' code (the folder of the code
  when there is one folder, the folder above when its code spans folders), so a solution's spec and code are in the same
  folder or one link apart;
* a metric row, with its solutions (the lowest folder holding all of them); a problem row, likewise with its solutions; an
  ideal row, with its problems;
* a row that has no code to follow stays where it is.

A row never moves out of its intent: a folder that holds an ``intent.csv`` is a sub-intent and owns the rows in it and below it,
so only rows that already belong to the intent that owns the destination move. ``plan`` lists the moves, ``apply`` makes them,
and both ways are one command: ``esoi records place`` (beside the code) and ``esoi records gather`` (into the structure folder).
Standard library only.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.import_base import import_base
from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of
from esoi.structure.intent_registry.records import FILES
from esoi.structure.intent_registry.tables import ids, read_csv, read_header, write_csv

Row = Dict[str, str]
FILE_OF = {entity: name for entity, (name, _) in FILES.items()}
KEY_OF = {name: key for name, key in FILES.values()}


@dataclass
class Move:
    """One record that belongs in another folder: its file, its id, where it is and where it belongs."""
    file: str
    ident: str
    source: Path
    target: Path


def hosts(config: Config) -> List[Path]:
    """Every folder ``[records] beside_code`` allows to hold records (existing folders that match, outside the structure folder)."""
    patterns = config.records.get("beside_code", []) if isinstance(config.records, dict) else []
    found: List[Path] = []
    for pattern in ([patterns] if isinstance(patterns, str) else patterns):
        for path in sorted(config.root.glob(str(pattern))):
            if path.is_dir() and path != config.structure and config.structure not in path.parents and path not in found:
                found.append(path)
    return found


def code_hosts(config: Config) -> List[str]:
    """Every folder that holds the code an implementation names, and every folder above it below the repository root, as
    paths from the root: the folders a repository of any language could list under ``beside_code`` to keep its records beside
    its code. It reads only the ``filepath`` column, never the code, so it needs no language."""
    root = config.root.resolve()
    found: Set[str] = set()
    for _, folder in intents.folders(config):
        for row in read_csv(folder / "implementations.csv"):
            here = code_folder(config, row.get("filepath", ""))
            while here is not None and here != root and root in here.parents:
                found.add(here.relative_to(root).as_posix())
                here = here.parent
    return sorted(found)


def arm_folder_patterns(config: Config) -> List[str]:
    """The folders (globs from the repository root) that hold the code of arms whose records belong to an intent elsewhere: the
    harness convention ``<evaluation_dir>/*/impls`` and every glob listed under ``[records] arm_folders``."""
    listed = config.records.get("arm_folders", []) if isinstance(config.records, dict) else []
    return [f"{config.evaluation_dir}/*/impls"] + ([listed] if isinstance(listed, str) else [str(p) for p in listed])


def arm_folders(config: Config) -> Dict[Path, List[Tuple[str, Path]]]:
    """``{code folder: [(owning intent id, folder of the intent that holds the row)]}`` for every folder of arms owned by an intent.

    An implementation arm's code may live in an evaluation ``impls`` folder (or one listed under ``[records] arm_folders``) while
    its record belongs to the owning intent; ``esoi records place`` rightly never moves the record out of that intent. Such a folder
    is covered by a README ``esoi readmes`` generates, which lists the arms and links to the owning intent's README. A folder
    qualifies only when it matches those patterns, holds no records of its own, is not at or around the row's folder, and the row
    has a known owning intent: arms of no known owner are not covered."""
    import fnmatch
    root = config.root.resolve()
    patterns = arm_folder_patterns(config)
    holders = {folder.resolve() for _, folder in intents.folders(config)}
    out: Dict[Path, List[Tuple[str, Path]]] = {}
    for row, folder, owner in rows_by_file(config)["implementations.csv"]:
        here = code_folder(config, row.get("filepath", ""))
        if here is None or not owner or here in holders:
            continue
        folder = folder.resolve()
        if here == folder or folder in here.parents or here in folder.parents:
            continue
        rel_here = here.relative_to(root).as_posix() if root in here.parents else ""
        if not any(fnmatch.fnmatchcase(rel_here, pattern) for pattern in patterns):
            continue
        pair = (owner, folder)
        if pair not in out.setdefault(here, []):
            out[here].append(pair)
    return out


def package_files(config: Config) -> Dict[str, str]:
    """{dotted module name: repository-relative file} of every Python module of the package (``__init__`` is the package itself)."""
    base = config.root / (config.package_dir or config.package or "")
    out: Dict[str, str] = {}
    if not config.package or not base.is_dir():
        return out
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        parts = [config.package] + list(path.relative_to(base).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        out[".".join(parts)] = path.relative_to(config.root).as_posix()
    return out


def import_graph(config: Config) -> Dict[str, Set[str]]:
    """{file: files of the package it imports directly}, read from the syntax trees (nothing is run). A file that does not parse
    imports nothing here."""
    import ast
    modules = package_files(config)
    by_file = {v: k for k, v in modules.items()}
    graph: Dict[str, Set[str]] = {}
    for dotted, rel in modules.items():
        tree = tree_of(config.root / rel)
        if tree is None:
            graph[rel] = set()
            continue
        is_pkg = rel.endswith("__init__.py")
        found: Set[str] = set()
        for node in nodes_of(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = import_base(dotted.split(".") if is_pkg else dotted.split(".")[:-1], node.level, node.module)
                names = [base] + [f"{base}.{a.name}" for a in node.names]
            else:
                continue
            found.update(modules[n] for n in names if n in modules)
        found.discard(rel)
        graph[rel] = found
    return graph


def area_rank(config: Config, folder: Path, areas: List[Path]) -> Optional[int]:
    """The layer rank of an area folder (a folder of records directly under the package): its own when ``layers`` names it, else the
    rank most listed record folders share (an area is not named in ``layers`` until it holds code)."""
    ranks = config.layer_rank
    if folder.name in ranks:
        return ranks[folder.name]
    listed = [ranks[a.name] for a in areas if a.name in ranks]
    if not listed:
        return None
    return max(set(listed), key=lambda rank: (listed.count(rank), rank))   # the rank most record folders share: the areas, not core


def names_solution(config: Config, files: Set[str], solution_id: str, interface: str) -> bool:
    """Whether the executable code of ``files`` names the solution: its id or its interface class (an identifier, annotation,
    imported name or a string used as a value; a docstring or comment never counts), as an area wires its members by name
    through typed needs rather than by importing them."""
    import ast
    import re
    from esoi.structure.structure_check import coherence_code_evidence, coherence_paragraph
    for rel in sorted(files):
        path = config.root / rel
        if not rel.endswith(".py") or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for token in coherence_code_evidence.executable_tokens(text, tree):
            if coherence_paragraph.position(solution_id, {}, token) >= 0 or (interface and re.search(r"\b" + re.escape(interface) + r"\b", token)):
                return True
    return False


def shared_layer_reaches(config: Config, spec: Path, code_file: str, graph: Dict[str, Set[str]], intent_files: Set[str],
                         solution_id: str = "", interface: str = "") -> bool:
    """Whether ``code_file`` sits in a layer of the package that is shared infrastructure of the intent at ``spec`` (a layer ranked
    below the area folders by ``layers``) and is imported by that intent's code (or named by its executable code through the solution's id or interface class, as an area wires
    its members by typed need): the spec folder's modules and the code of the implementations its rows name. Code in a layer at or above the area, or one the intent's code never imports, does not reach."""
    package = (config.root / (config.package_dir or config.package or "")).resolve()
    spec = spec.resolve()
    if not config.package or package not in spec.parents or spec == package:
        return False
    code = (config.root / code_file).resolve()
    if package not in code.parents:
        return False
    layer = code.relative_to(package).parts[0]
    ranks = config.layer_rank
    areas = [p for p in package.iterdir() if p.is_dir() and any((p / n).is_file() for n in ("intent.csv", "solutions.csv", "implementations.csv"))]
    mine = area_rank(config, package / spec.relative_to(package).parts[0], areas)
    if layer not in ranks or mine is None or ranks[layer] >= mine:
        return False
    if any(code_file in graph.get(g, ()) for g in intent_files):
        return True
    return bool(solution_id) and names_solution(config, intent_files, solution_id, interface)


def host_for(allowed: Set[Path], folder: Optional[Path], root: Path) -> Optional[Path]:
    """The nearest folder at or above ``folder`` that may hold records, else None."""
    if folder is None:
        return None
    for candidate in [folder, *folder.parents]:
        if candidate in allowed:
            return candidate
        if candidate == root:
            break
    return None


def code_folder(config: Config, filepath: str) -> Optional[Path]:
    """The folder of the code an implementation row names (``path`` or ``path::name``), None when it names none or lies outside."""
    entry = (filepath or "").split("::")[0].strip()
    if not entry or entry.startswith("@"):
        return None
    path = (config.root / entry).resolve().parent
    return path if config.root.resolve() in [path, *path.parents] else None


def root_relative_file(config: Config, filepath: str) -> str:
    """The repository-relative file an implementation's ``filepath`` names ('' when it names none): the part before ``::``."""
    return (filepath or "").partition("::")[0].strip()


def common(folders: List[Path]) -> Optional[Path]:
    """The lowest folder that holds every one of ``folders`` (None for none)."""
    return Path(os.path.commonpath([str(f) for f in folders])) if folders else None


def rows_by_file(config: Config) -> Dict[str, List[Tuple[Row, Path, str]]]:
    """``{file name: [(raw row, folder, owning intent id)]}`` across the tree, in reading order."""
    out: Dict[str, List[Tuple[Row, Path, str]]] = {name: [] for name in KEY_OF}
    for intent_id, folder in intents.folders(config):
        for name in KEY_OF:
            out[name] += [(row, folder, intent_id) for row in read_csv(folder / name)]
    return out


def code_targets(config: Config, held, allowed: Set[Path], root: Path) -> Tuple[Dict[Tuple[str, str], Path], Dict[str, Path]]:
    """Where each implementation and solution belongs beside its code: the wanted folders by ``(file, id)``, and the solutions' folders by id."""
    want: Dict[Tuple[str, str], Path] = {}
    impl_dirs: Dict[str, List[Path]] = {}
    for row, folder, _ in held["implementations.csv"]:
        here = code_folder(config, row.get("filepath", ""))
        if here is not None:
            impl_dirs.setdefault(row.get("solution_id", "").strip(), []).append(here)
            target = host_for(allowed, here, root)
            if target is not None:
                want[("implementations.csv", row.get("implementation_id", "").strip())] = target
    solution_at: Dict[str, Path] = {}
    for row, folder, _ in held["solutions.csv"]:
        sid = row.get("solution_id", "").strip()
        target = host_for(allowed, common(impl_dirs.get(sid, [])), root)
        if target is not None:
            solution_at[sid] = target
            want[("solutions.csv", sid)] = target
    return want, solution_at


def linked_targets(held, allowed: Set[Path], root: Path, owner_here, solution_at: Dict[str, Path]) -> Dict[Tuple[str, str], Path]:
    """Where each problem, metric and ideal belongs: with the solutions it serves, and an ideal with the problems it opposes."""
    want: Dict[Tuple[str, str], Path] = {}

    def where_solutions(cell: str, fallback: Path) -> Optional[Path]:
        places = [solution_at.get(s, owner_here["solutions.csv"].get(s, (fallback, ""))[0].resolve()) for s in ids(cell)]
        return host_for(allowed, common(places), root) if places else None

    problem_at: Dict[str, Path] = {}
    for row, folder, _ in held["problems.csv"]:
        target = where_solutions(row.get("solution_ids", ""), folder)
        if target is not None:
            problem_at[row.get("problem_id", "").strip()] = target
            want[("problems.csv", row.get("problem_id", "").strip())] = target
    for row, folder, _ in held["metrics.csv"]:
        target = where_solutions(row.get("solution_ids", ""), folder)
        if target is not None:
            want[("metrics.csv", row.get("metric_id", "").strip())] = target
    for row, folder, _ in held["ideals.csv"]:
        places = [problem_at[p] for p in ids(row.get("problem_ids", "")) if p in problem_at]
        target = host_for(allowed, common(places), root) if len(places) == len(ids(row.get("problem_ids", ""))) and places else None
        if target is not None:
            want[("ideals.csv", row.get("ideal_id", "").strip())] = target
    return want


def plan(config: Config, mode: str = "beside") -> List[Move]:
    """The records that are not in the folder they belong in. ``mode`` is ``beside`` (next to their code) or ``gather`` (all of
    the top intent's records in the structure folder)."""
    if mode not in ("beside", "gather"):
        raise ValueError(f"unknown placement {mode!r}; choose beside or gather")
    held = rows_by_file(config)
    walked = intents.discover_in_structure(config)
    named = intents.named_folders(config, walked, intents.beside_folders(config))
    root = config.root.resolve()
    allowed = {p.resolve() for p in set(hosts(config)) | set(intents.beside_folders(config))}
    owner_here = {name: {row.get(KEY_OF[name], "").strip(): (folder, owner) for row, folder, owner in found}
                  for name, found in held.items()}
    top = next((i for i in walked if i.is_top), None)
    want: Dict[Tuple[str, str], Path] = {}
    if mode == "beside":
        want, solution_at = code_targets(config, held, allowed, root)
        want.update(linked_targets(held, allowed, root, owner_here, solution_at))

    def destination(name: str, ident: str) -> Optional[Path]:
        folder, owner = owner_here[name][ident]
        if mode == "gather":
            return config.structure if owner == (top.intent_id if top else "") else folder
        return want.get((name, ident))

    moves: List[Move] = []
    for name, found in held.items():
        for row, folder, owner in found:
            ident = row.get(KEY_OF[name], "").strip()
            target = destination(name, ident) if ident else None
            if target is None or target.resolve() == folder.resolve():
                continue
            if intents.owner_of(config, target, named) != owner and target.resolve() != config.structure.resolve():
                continue   # a row never leaves the intent that owns it
            moves.append(Move(name, ident, folder, target))
    return moves


def apply(config: Config, moves: List[Move]) -> int:
    """Make the moves: each record leaves its file (a file left empty is removed) and is appended to the destination's file."""
    removed: Dict[Tuple[Path, str], Set[str]] = {}
    carried: Dict[Tuple[Path, str], List[Row]] = {}
    headers: Dict[Tuple[Path, str], List[str]] = {}
    for move in moves:
        removed.setdefault((move.source, move.file), set()).add(move.ident)
    for (folder, name), gone in removed.items():
        headers[(folder, name)] = read_header(folder / name)
    for move in moves:
        row = next(r for r in read_csv(move.source / move.file) if r.get(KEY_OF[move.file], "").strip() == move.ident)
        carried.setdefault((move.target, move.file), []).append(row)
        columns = headers.get((move.source, move.file)) or read_header(move.source / move.file)
        have = headers.setdefault((move.target, move.file), read_header(move.target / move.file) if (move.target / move.file).is_file() else [])
        have += [c for c in columns if c not in have]
    for (folder, name), gone in removed.items():
        keep = [r for r in read_csv(folder / name) if r.get(KEY_OF[name], "").strip() not in gone]
        if keep:
            write_csv(folder / name, headers[(folder, name)], keep)
        else:
            (folder / name).unlink()
    for (folder, name), rows in carried.items():
        write_csv(folder / name, headers[(folder, name)], read_csv(folder / name) + rows)
    return len(moves)


def run_cli(config: Config, mode: str, do_apply: bool, say=print) -> int:
    """``esoi records place|gather [--apply]``: list the records that are not where the layout puts them, or move them and
    write the README of every folder that now holds records."""
    if not config.intent_mode:
        say("no intents here (the legacy layout), so there is nothing to place")
        return 0
    if mode == "beside" and not hosts(config):
        say("no folder is listed under [records] beside_code in esoi.toml, so nothing can be placed beside the code")
        return 1
    moves = plan(config, mode)
    for move in moves:
        say(f"{move.ident}: {move.file} from {relative_to_root(config, move.source)} to {relative_to_root(config, move.target)}")
    if not moves:
        say("every record is already where the layout puts it")
        return 0
    if not do_apply:
        say(f"{len(moves)} record(s) would move (dry run; add --apply)")
        return 0
    apply(config, moves)
    from esoi.understanding.readable_records import readme
    from esoi.structure.intent_registry import registry
    say(f"moved {len(moves)} record(s)")
    readme.write(config, registry.load(config), say=lambda text: None)
    say("wrote the READMEs; commit the moved records with them")
    return 0


def relative_to_root(config: Config, folder: Path) -> str:
    try:
        return Path(folder).resolve().relative_to(config.root.resolve()).as_posix() or "."
    except ValueError:
        return str(folder)
