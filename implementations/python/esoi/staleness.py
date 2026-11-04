"""What a recorded result measures, so that it goes stale only when that changed.

A row of the results log is pinned to a commit. The rule that says whether the code changed since then is a choice between
alternatives, measured like any other (the ``staleness_precision`` component):

* ``repo_wide``: any file of ``code_paths`` or of the evaluation folder changed. The baseline: safe, and every component's rows
  go stale on every commit.
* ``component_paths``: only the files the arm's solution and implementation own in the ownership map (``components.csv`` path
  globs mapped to solutions, the implementation records' files, the beside-code folder of a solution whose code is alone in it,
  the component's evaluation folder and the fixtures shared by all of them). A file of ``code_paths`` that no component owns
  counts for every arm (never silently fresh). A component with no ownership entry falls back to ``repo_wide``.
* ``import_closure``: a result goes stale only when the arm's OWN code changes. For a Python arm that is its implementation
  module (the wrapper in ``impls/`` or the file its record names) and the helper code it imports, transitively, found by reading
  the source (no execution), that belongs to no implementation of any solution. Not in it, whatever the arm imports: test files
  and shared fixtures (``tests/``, ``test_*.py``, ``conftest.py``, everything else in the evaluation folder), the scorer and its
  datasets, a package ``__init__``, and any file another implementation owns (another arm of the component, or another
  solution's code: that solution's own recorded selection answers for it). A changed file that is not Python is judged by
  ``component_paths``, except that anything in the evaluation folder that is not the arm's file is not its code. When the arm
  is not Python, or the scan meets a dynamic import it cannot read, it falls back to ``component_paths`` plus the files the
  scan did find, still without tests, fixtures, scorers and datasets (a module that is loaded only by a computed name and that
  another component owns is not seen: see ``docs/how-to/choose-when-a-result-is-stale.md``).

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
NAMES: Dict[tuple, Optional[Tuple[Set[str], bool]]] = {}   # (path, mtime, size, roots) -> what the file imports
SCOPES: Dict[tuple, Tuple[tuple, "Scope"]] = {}   # (root, component, arm, rule) -> (stat of every file the scan read, scope)


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
    closure: Optional[Set[str]] = None   # the files the static scan found
    complete: bool = False               # whether the scan saw every import (else the files it found only add to the component's)
    own_files: Set[str] = field(default_factory=set)   # the arm's own implementation files (import_closure)
    foreign: Set[str] = field(default_factory=set)     # files other implementations own (import_closure): never this arm's code


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


MODULES: Dict[tuple, List[Path]] = {}


def module_files(roots: List[Path], dotted: str) -> List[Path]:
    """Cached for the run of the process: a module that appears or disappears mid-run is seen by the next process."""
    key = (tuple(map(str, roots)), dotted)
    if key not in MODULES:
        MODULES[key] = find_module_files(roots, dotted)
    return MODULES[key]


def find_module_files(roots: List[Path], dotted: str) -> List[Path]:
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


def import_names(tree: ast.Module, here: Path, roots: List[Path]) -> Tuple[Set[str], bool]:
    """``(names, complete)``: every module a file imports, as dotted names from a search root, and whether it imports none by a name it
    computes (the names found are returned either way)."""
    names: Set[str] = set()
    complete = True
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
                first = node.args[0] if node.args else None
                if called not in ("spec_from_file_location", "load_source") and isinstance(first, ast.Constant) \
                        and isinstance(first.value, str) and not first.value.startswith("."):
                    names.add(first.value)
                else:
                    complete = False
    return names, complete


TEST_NAMES = re.compile(r"(^test_.*|.*_test|^conftest)\.py$")
TEST_FOLDERS = {"tests", "test", "fixtures", "__pycache__"}


def is_test_file(rel: str) -> bool:
    """A test file or a shared test fixture: a ``tests`` or ``fixtures`` folder, ``test_*.py``, ``*_test.py`` or ``conftest.py``."""
    parts = rel.split("/")
    return bool(TEST_FOLDERS & set(parts[:-1])) or bool(TEST_NAMES.match(parts[-1]))


def foreign_files(config: Config, index: Index, own: Set[str]) -> Set[str]:
    """Files that belong to another implementation: every file an implementation record names (any solution), and every module in
    an ``impls`` folder of the evaluation folder, except the arm's own."""
    found: Set[str] = set()
    for row in index.implementations:
        path = (row.get("filepath") or "").partition("::")[0].strip()
        if path and not path.startswith("@"):
            found.add(path)
    root = config.root.resolve()
    for path in config.evaluation.glob("*/impls/*.py"):
        found.add(path.resolve().relative_to(root).as_posix())
    return found - own


def not_own_code(config: Config, rel: str, foreign: Set[str], own: Set[str]) -> bool:
    """Whether a file the scan reaches is left out of an arm's closure: a test or fixture, a package ``__init__``, anything else in
    the evaluation folder (scorer, datasets, shared fixtures), or a file another implementation owns."""
    if rel in own:
        return False
    evaluation = config.evaluation.resolve().relative_to(config.root.resolve()).as_posix() if config.evaluation.resolve().is_relative_to(config.root.resolve()) else config.evaluation_dir
    return (is_test_file(rel) or rel.endswith("/__init__.py") or rel == "__init__.py" or rel.startswith(evaluation + "/")
            or rel in foreign)


def closure_of(config: Config, starts: List[Path], skip=None) -> Tuple[Set[str], bool]:
    """``(files, complete)``: the repository files the start files import, transitively, from their source, and whether the scan was
    complete. It is not when a file cannot be read, is not Python, or imports a module by a computed name; the files found so far
    are still returned, for the rule that falls back."""
    roots = search_roots(config)
    root = config.root.resolve()
    seen: Dict[Path, None] = {}
    queue = [p.resolve() for p in starts]
    complete = True
    while queue:
        here = queue.pop()
        if here in seen or not here.is_file():
            continue
        if here.suffix != ".py":
            complete = False
            continue
        seen[here] = None
        info = here.stat()
        key = (str(here), info.st_mtime_ns, info.st_size, tuple(map(str, roots)))
        if key not in NAMES:
            tree = parse(here)
            NAMES[key] = import_names(tree, here, roots) if tree is not None else None
        found = NAMES[key]
        if found is None:
            complete = False
            continue
        names, whole = found
        complete = complete and whole
        for dotted in names:
            queue.extend(p for p in module_files(roots, dotted) if p not in seen and root in p.parents
                         and not (skip is not None and skip(p.relative_to(root).as_posix())))
    return {p.relative_to(root).as_posix() for p in seen}, complete


def start_files(config: Config, index: Index, component: str, impl: str, solutions: List[str]) -> Optional[List[Path]]:
    """The arm's own implementation files: the wrapper in ``impls/`` when there is one, and the files its records name (those of the
    implementation of that name, else of the solution's implementations). None when it has neither, or a record names a file that is
    not Python and there is no wrapper."""
    wrapper = config.evaluation / component / "impls" / f"{impl}.py"
    named = [r for r in index.implementations if r.get("solution_id") in solutions]
    mine = [r for r in named if normal(r.get("implementation_id", "")) == normal(impl)] or named
    files = [(r.get("filepath") or "").partition("::")[0].strip() for r in mine]
    files = [f for f in files if f and not f.startswith("@")]
    if wrapper.is_file():
        return [wrapper] + [config.root / f for f in files if f.endswith(".py")]
    if not files or any(not f.endswith(".py") for f in files):
        return None
    return [config.root / f for f in files]


def file_stats(config: Config, scope: Scope) -> tuple:
    root = config.root.resolve()
    found = []
    for rel in sorted(scope.closure or ()):
        try:
            info = (root / rel).stat()
            found.append((rel, info.st_mtime_ns, info.st_size))
        except OSError:
            found.append((rel, 0, 0))
    return tuple(found)


def scope_for(config: Config, component: str, impl: str, rule: Optional[str] = None) -> Scope:
    """What the arm measures under the rule (or the one in force), with the fallbacks written down. The scan is kept for the next
    call and reused while the records and every file it read are unchanged."""
    rule = rule or rule_for(config)
    key = (str(config.root), component, impl, rule)
    kept = SCOPES.get(key)
    if kept is not None and kept[0] == (signature(config), file_stats(config, kept[1])):
        return kept[1]
    scope = build_scope(config, component, impl, rule)
    SCOPES[key] = ((signature(config), file_stats(config, scope)), scope)
    return scope


def build_scope(config: Config, component: str, impl: str, rule: str) -> Scope:
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
        if starts:
            scope.own_files = {p.resolve().relative_to(root).as_posix() for p in starts if p.resolve().is_relative_to(root)}
            foreign = scope.foreign = foreign_files(config, index, scope.own_files)
            scope.closure, scope.complete = closure_of(config, starts, lambda rel: not_own_code(config, rel, foreign, scope.own_files))
        if scope.closure is None or not scope.complete:
            scope.note = ("its imports cannot be read completely (not Python, or a computed import), so the files it does import "
                          "and its component's files count")
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
    if scope.requested == "import_closure":
        if path in scope.own_files or (scope.closure is not None and path in scope.closure and path.endswith(".py")):
            return True, "the arm's own code" if path in scope.own_files else "imported by the arm"
        if is_test_file(path):
            return False, "a test or shared test fixture, not the arm's code"
        if path in scope.foreign:
            return False, "another implementation's code: its own recorded selection answers for it, not this result"
        if path.startswith(inside):
            return False, "the evaluation folder holds the scorer, datasets and fixtures, not the arm's code"
    elif path.startswith(inside):
        rest = path[len(inside):]
        if rest.startswith(scope.component + "/"):
            return True, f"in the evaluation folder of {scope.component}"
        if "/" not in rest:
            imported = not scope.complete or path in (scope.closure or set()) or not path.endswith(".py")
            return imported, "a fixture shared by every evaluation" if imported else "a shared fixture the arm does not import"
        return False, f"in the evaluation folder of {rest.split('/')[0]}"
    exists = (config.root / path).is_file()
    if scope.closure is not None and path.endswith(".py") and exists:
        if path in scope.closure:
            return True, "imported by the arm"
        if scope.rule == "import_closure":
            return False, "not the arm's own code (not imported, or owned by another implementation)"
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


def changed_files(config: Config, sha: str, until: str = "") -> Optional[List[str]]:
    """Tracked files of the measured code folders and the evaluation folder that differ from the working tree since ``sha``, a
    rename listed under both names; ``None`` when the commit is not known here."""
    base = sha.removesuffix("-dirty")
    done = subprocess.run(["git", "diff", "--name-only", "--no-renames", base, *([until] if until else []), "--", *measured_paths(config)],
                          cwd=config.root, capture_output=True, text=True)
    return done.stdout.split("\n") and [p for p in done.stdout.split("\n") if p] if done.returncode == 0 else None


def explain(config: Config, component: str, impl: str, sha: str, rule: Optional[str] = None,
            until: str = "") -> Optional[Dict[str, List[str]]]:
    """``{"counts": [...], "ignored": [...], "rule": [rule in force, fallback note]}``, each file as ``path (why)``, for the files
    changed since ``sha``; ``None`` when the commit is unknown."""
    changed = changed_files(config, sha, until)
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
