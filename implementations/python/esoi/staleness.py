"""What a recorded result measures, so that it goes stale only when that changed.

A row of the results log is pinned to a commit. The rule that says whether the code changed since then is a choice between
alternatives, measured like any other (the ``staleness_precision`` component):

* ``repo_wide``: any file of ``code_paths`` or of the evaluation folder changed. The baseline: safe, and every component's rows
  go stale on every commit.
* ``component_paths``: only the files the arm's solution and implementation own in the ownership map (``components.csv`` path
  globs mapped to solutions, the implementation records' files, the beside-code folder of a solution whose code is alone in it,
  the component's evaluation folder and the fixtures shared by all of them). A file of ``code_paths`` that no component owns
  counts for every arm (never silently fresh). A component with no ownership entry falls back to ``repo_wide``.
* ``import_closure``: for a Python arm, the files of the repository that its implementation module imports, transitively,
  found by reading the source (no execution), plus the component's evaluation folder. A changed file that is not Python is
  judged by ``component_paths``. When the arm is not Python, or the scan meets a dynamic import it cannot read, it falls
  back to ``component_paths``.

``rule_for`` picks the rule: ``staleness_rule`` in ``esoi.toml``, else the arm the repository's records select for the
solution ``know-what-a-result-measures``, else ``DEFAULT_RULE`` (the arm the staleness precision metric selected). Standard library only; nothing is run or imported from the
measured code.
"""
from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import Config, DEFAULT_STALENESS_RULE, STALENESS_RULES

RULES = STALENESS_RULES
DEFAULT_RULE = DEFAULT_STALENESS_RULE
SOLUTION_ID = "know-what-a-result-measures"
DYNAMIC_CALLS = {"import_module", "__import__", "run_module", "spec_from_file_location", "load_source"}
PARSED: Dict[Tuple[str, int, int], Optional[ast.Module]] = {}
INDEXES: Dict[str, Tuple[tuple, "Index"]] = {}


@dataclass
class Index:
    """The ownership map of one repository as the stale rules read it."""
    components: List[Tuple[str, List[re.Pattern], Set[str]]] = field(default_factory=list)   # (id, path patterns, solution ids)
    solutions: List[Dict[str, str]] = field(default_factory=list)
    implementations: List[Dict[str, str]] = field(default_factory=list)
    selected: str = ""


@dataclass
class Scope:
    """What one arm measures under a rule, and how a changed path is judged against it."""
    rule: str                      # the rule that is in force for this arm after any fallback
    requested: str                 # the rule the repository asked for
    note: str = ""                 # why the rule fell back, when it did
    own: List[Tuple[re.Pattern, str]] = field(default_factory=list)       # patterns the arm owns, with the owning component
    others: List[Tuple[re.Pattern, str]] = field(default_factory=list)    # patterns other components own
    evaluation: str = ""           # the evaluation folder, from the root
    component: str = ""
    closure: Optional[Set[str]] = None


def glob_pattern(text: str) -> re.Pattern:
    """A path glob as a regular expression: ``**`` crosses folders, ``*`` and ``?`` stay in one; a plain folder owns what is in it."""
    out, i = "", 0
    while i < len(text):
        if text.startswith("**", i):
            out, i = out + ".*", i + 2
        elif text[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif text[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(text[i]), i + 1
    return re.compile(out + r"(?:/.*)?$")


def cells(text: str) -> List[str]:
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def normal(name: str) -> str:
    return name.split(":")[-1].split("::")[0].strip().lower().replace("-", "_")


def signature(config: Config) -> tuple:
    from . import intents
    found = []
    for _, folder in intents.folders(config):
        for name in ("components.csv", "implementations.csv", "solutions.csv", "metrics.csv"):
            path = folder / name
            if path.is_file():
                info = path.stat()
                found.append((str(path), info.st_mtime_ns, info.st_size))
    return tuple(found)


def index_of(config: Config) -> Index:
    """The ownership map, read once per state of the records."""
    from .registry import load
    key = signature(config)
    cached = INDEXES.get(str(config.root))
    if cached and cached[0] == key:
        return cached[1]
    registry = load(config)
    found = Index(solutions=list(registry.solutions), implementations=list(registry.implementations))
    for row in registry.components:
        patterns = [glob_pattern(p) for p in cells(row.get("path", ""))]
        found.components.append((row.get("component_id", ""), patterns, set(cells(row.get("solutions", "")))))
    for row in found.solutions:
        if row.get("solution_id") == SOLUTION_ID:
            found.selected = normal(row.get("selected", ""))
    INDEXES[str(config.root)] = (key, found)
    return found


def rule_for(config: Config) -> str:
    """The rule in force: the configuration, else the records' selected arm, else the library default."""
    if config.staleness_rule:
        return config.staleness_rule
    chosen = index_of(config).selected
    return chosen if chosen in RULES else DEFAULT_RULE


def arm_solutions(config: Config, index: Index, component: str, impl: str) -> List[str]:
    """The solutions whose metric runs this arm (or, when no command names the arm, any arm of the component)."""
    from .registry import harness_arms
    exact, loose = [], []
    for row in index.solutions:
        arms = harness_arms(config, row.get("metric_command", ""))
        if (component, impl) in arms:
            exact.append(row["solution_id"])
        elif any(comp == component for comp, _ in arms):
            loose.append(row["solution_id"])
    return exact or loose


def implementation_files(index: Index, solutions: List[str]) -> List[str]:
    files = []
    for row in index.implementations:
        if row.get("solution_id") in solutions:
            path = (row.get("filepath") or "").partition("::")[0].strip()
            if path and not path.startswith("@") and path not in files:
                files.append(path)
    return files


def beside_folders(config: Config, index: Index, solutions: List[str]) -> List[str]:
    """The beside-code folder of a solution, when the records live beside the code and its code is alone in that folder."""
    from . import besidecode
    allowed = set(besidecode.hosts(config))
    if not allowed:
        return []
    root = config.root.resolve()
    found = []
    for sid in solutions:
        folders = [besidecode.code_folder(config, r.get("filepath", "")) for r in index.implementations if r.get("solution_id") == sid]
        folders = [f for f in folders if f is not None]
        host = besidecode.host_for(allowed, besidecode.common(folders), root) if folders else None
        if host is None or host == root:
            continue
        shared = False
        for r in index.implementations:
            where = besidecode.code_folder(config, r.get("filepath", ""))
            if r.get("solution_id") not in solutions and where is not None and host in [where, *where.parents]:
                shared = True
        if not shared:
            found.append(host.relative_to(root).as_posix())
    return found


def search_roots(config: Config) -> List[Path]:
    roots = [config.root / p for p in config.python_path] + [config.evaluation, config.root]
    return [r.resolve() for r in roots if r.is_dir()]


def parse(path: Path) -> Optional[ast.Module]:
    info = path.stat()
    key = (str(path), info.st_mtime_ns, info.st_size)
    if key not in PARSED:
        try:
            PARSED[key] = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            PARSED[key] = None
    return PARSED[key]


def module_files(roots: List[Path], dotted: str) -> List[Path]:
    """The files that importing ``dotted`` runs inside the repository: the module and the ``__init__`` of each package above it."""
    parts = dotted.split(".")
    for root in roots:
        target = root.joinpath(*parts)
        if target.with_suffix(".py").is_file():
            main = target.with_suffix(".py")
        elif (target / "__init__.py").is_file():
            main = target / "__init__.py"
        else:
            continue
        found = [root.joinpath(*parts[:i], "__init__.py") for i in range(1, len(parts))]
        return [p for p in found if p.is_file()] + [main]
    return []


def import_names(tree: ast.Module, here: Path, roots: List[Path]) -> Optional[Set[str]]:
    """Every module a file imports, as dotted names from a search root; ``None`` when it imports one by a name it computes."""
    names: Set[str] = set()
    base: Optional[List[str]] = None
    for root in roots:
        if root in here.parents:
            base = list(here.parent.relative_to(root).parts)
            break
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix: List[str] = []
            if node.level:
                if base is None or node.level - 1 > len(base):
                    continue
                prefix = base[:len(base) - (node.level - 1)]
            module = ".".join(prefix + ([node.module] if node.module else [])) if (node.level or node.module) else ""
            if module:
                names.add(module)
                names.update(f"{module}.{alias.name}" for alias in node.names)
            elif node.level:
                names.update(".".join(prefix + [alias.name]) for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
            if called in DYNAMIC_CALLS:
                if called in ("spec_from_file_location", "load_source") or not node.args:
                    return None
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str) and not first.value.startswith("."):
                    names.add(first.value)
                else:
                    return None
    return names


def closure_of(config: Config, starts: List[Path]) -> Optional[Set[str]]:
    """The repository files the start files import, transitively, from their source; ``None`` when a file cannot be read or imports
    a module by a computed name."""
    roots = search_roots(config)
    root = config.root.resolve()
    seen: Dict[Path, None] = {}
    queue = [p.resolve() for p in starts]
    while queue:
        here = queue.pop()
        if here in seen or not here.is_file():
            continue
        if here.suffix != ".py":
            return None
        seen[here] = None
        tree = parse(here)
        if tree is None:
            return None
        names = import_names(tree, here, roots)
        if names is None:
            return None
        for dotted in names:
            queue.extend(p for p in module_files(roots, dotted) if p not in seen and root in p.parents)
    return {p.relative_to(root).as_posix() for p in seen}


def start_files(config: Config, index: Index, component: str, impl: str, solutions: List[str]) -> Optional[List[Path]]:
    """The modules an arm runs from: its scorer and implementation file, or the file the records name for a declared implementation."""
    folder = config.evaluation / component
    starts = [folder / "score.py", folder / "__init__.py"]
    wrapper = folder / "impls" / f"{impl}.py"
    if wrapper.is_file():
        return starts + [wrapper, folder / "impls" / "__init__.py"]
    named = [r for r in index.implementations if r.get("solution_id") in solutions]
    mine = [r for r in named if normal(r.get("implementation_id", "")) == normal(impl)] or named
    files = [(r.get("filepath") or "").partition("::")[0].strip() for r in mine]
    files = [f for f in files if f and not f.startswith("@")]
    if not files or any(not f.endswith(".py") for f in files):
        return None
    return starts + [config.root / f for f in files]


def scope_for(config: Config, component: str, impl: str, rule: Optional[str] = None) -> Scope:
    """What the arm measures under the rule (or the one in force), with the fallbacks written down."""
    rule = rule or rule_for(config)
    impl = impl.partition(":")[0] if ":" in impl and "/" not in impl else impl
    root = config.root.resolve()
    evaluation = config.evaluation.resolve().relative_to(root).as_posix() if config.evaluation.resolve().is_relative_to(root) else config.evaluation_dir
    scope = Scope(rule="repo_wide", requested=rule, evaluation=evaluation, component=component)
    if rule == "repo_wide":
        return scope
    index = index_of(config)
    solutions = arm_solutions(config, index, component, impl)
    owners = [(cid, pats) for cid, pats, sols in index.components if sols & set(solutions)]
    if not solutions or not owners:
        scope.note = "the ownership map has no entry for it, so the whole repository's code counts"
        return scope
    own_ids = {cid for cid, _ in owners}
    scope.own = [(pat, cid) for cid, pats in owners for pat in pats]
    for path in implementation_files(index, solutions):
        scope.own.append((glob_pattern(path), "the implementation record"))
    for path in beside_folders(config, index, solutions):
        scope.own.append((glob_pattern(path), "its records folder"))
    scope.others = [(pat, cid) for cid, pats, _ in index.components if cid not in own_ids for pat in pats]
    scope.rule = "component_paths"
    if rule == "import_closure":
        starts = start_files(config, index, component, impl, solutions)
        scope.closure = closure_of(config, starts) if starts else None
        if scope.closure is None:
            scope.note = "its imports cannot be read statically (not Python, or a computed import), so its component's files count"
        else:
            scope.rule = "import_closure"
    return scope


def first_match(patterns: List[Tuple[re.Pattern, str]], path: str) -> str:
    return next((label for pattern, label in patterns if pattern.match(path)), "")


def judge(config: Config, scope: Scope, path: str) -> Tuple[bool, str]:
    """``(counts, why)`` for one changed path under the scope: whether the arm measures it, and who owns it or why it counts."""
    if scope.rule == "repo_wide":
        return True, "the whole repository's code counts"
    inside = scope.evaluation + "/"
    if path.startswith(inside):
        rest = path[len(inside):]
        if rest.startswith(scope.component + "/"):
            return True, f"in the evaluation folder of {scope.component}"
        if "/" not in rest:
            imported = scope.closure is None or path in scope.closure or not path.endswith(".py")
            return imported, "a fixture shared by every evaluation" if imported else "a shared fixture the arm does not import"
        return False, f"in the evaluation folder of {rest.split('/')[0]}"
    exists = (config.root / path).is_file()
    if scope.rule == "import_closure" and scope.closure is not None and path.endswith(".py") and exists:
        return (path in scope.closure), ("imported by the arm" if path in scope.closure else "not imported by the arm")
    owner = first_match(scope.own, path)
    if owner:
        return True, f"owned by {owner}"
    other = first_match(scope.others, path)
    if other:
        return False, f"owned by component {other}"
    return True, "owned by no component, so it counts for every arm"


def measured_paths(config: Config) -> List[str]:
    from .harness import own_code_paths
    return [*own_code_paths(config), config.evaluation_dir, f":(exclude){config.results}", f":(exclude){config.per_case}",
            f":(exclude){config.runs_log}"]


def changed_files(config: Config, sha: str) -> Optional[List[str]]:
    """Tracked files of the measured code folders and the evaluation folder that differ from the working tree since ``sha``, a
    rename listed under both names; ``None`` when the commit is not known here."""
    base = sha.removesuffix("-dirty")
    done = subprocess.run(["git", "diff", "--name-only", "--no-renames", base, "--", *measured_paths(config)],
                          cwd=config.root, capture_output=True, text=True)
    return done.stdout.split("\n") and [p for p in done.stdout.split("\n") if p] if done.returncode == 0 else None


def explain(config: Config, component: str, impl: str, sha: str, rule: Optional[str] = None) -> Optional[Dict[str, List[str]]]:
    """``{"counts": [...], "ignored": [...], "rule": [rule in force, fallback note]}``, each file as ``path (why)``, for the files
    changed since ``sha``; ``None`` when the commit is unknown."""
    changed = changed_files(config, sha)
    if changed is None:
        return None
    scope = scope_for(config, component, impl, rule)
    out: Dict[str, List[str]] = {"counts": [], "ignored": [], "rule": [scope.rule, scope.note]}
    for path in changed:
        counts, why = judge(config, scope, path)
        out["counts" if counts else "ignored"].append(f"{path}, {why}")
    return out


def dirty_counts(config: Config, component: str, impl: str) -> bool:
    """Whether uncommitted tracked changes touch what the arm measures (the ``-dirty`` mark of a recorded row)."""
    done = subprocess.run(["git", "diff", "--name-only", "--no-renames", "HEAD", "--", *measured_paths(config)],
                          cwd=config.root, capture_output=True, text=True)
    paths = [p for p in done.stdout.split("\n") if p]
    if not paths:
        return False
    scope = scope_for(config, component, impl)
    return any(judge(config, scope, path)[0] for path in paths)


def count_stale(config: Config, rule: str) -> Dict[str, str]:
    """``{component/impl: reason}`` for every latest whole-run row that the rule calls stale because measured code changed (a row
    stale for another reason is left out); how a rule would judge the rows now, whatever the repository configured."""
    from . import leaderboard
    from .harness import stale_reason
    saved = config.staleness_rule
    config.staleness_rule = rule
    try:
        found: Dict[str, str] = {}
        for comp, arms in leaderboard.latest_results(config.results_path, whole=True).items():
            for impl, row in arms.items():
                if not stale_reason(config, comp, row, False) and (why := stale_reason(config, comp, row, True)):
                    found[f"{comp}/{impl}"] = why
        return found
    finally:
        config.staleness_rule = saved


def explain_cli(config: Config, component: str, say=print, rule: str = "") -> int:
    """``esoi stale --explain COMPONENT [--rule RULE]``: for each recorded arm of the component, the rule in force, the files changed
    since its row's commit that count and who owns them, and the ones that are ignored and who owns those."""
    from . import leaderboard
    arms = leaderboard.latest_results(config.results_path, whole=True).get(component)
    if not arms:
        say(f"{component}: no recorded result, so nothing can be stale (a selected arm with no row is advice from esoi check)")
        return 0
    for impl, row in sorted(arms.items()):
        sha = row.get("git_sha", "")
        found = explain(config, component, impl, sha, rule or None) if sha else None
        if found is None:
            say(f"{component}/{impl}: recorded at {sha or 'no commit'}, which is not known here, so no file can be compared")
            continue
        say(f"{component}/{impl}: recorded at {sha}; rule {found['rule'][0]}" + (f" ({found['rule'][1]})" if found["rule"][1] else ""))
        for line in found["counts"]:
            say(f"  counts: {line}")
        for line in found["ignored"]:
            say(f"  ignored: {line}")
        if not found["counts"]:
            say("  nothing it measures changed")
    return 0
