"""What one arm measures under a staleness rule (repo_wide, component_paths or import_closure) and the judgment of one changed path against it."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.import_scan import is_test_file
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.import_world import WORLDS, start_files, world_of
from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.ownership_index import INDEXES, arm_solutions, beside_folders, glob_pattern, implementation_files, index_of, rule_for, signature


SCOPES: Dict[tuple, Tuple[tuple, "Scope"]] = {}   # (root, component, arm, rule) -> (stat of every file the scan read, scope)


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
    shared_components: Set[str] = field(default_factory=set)   # components that serve other solutions too: their files are not this arm's alone
    shared: Set[str] = field(default_factory=set)      # helper files another implementation's closure imports too: nobody's own code


def forget() -> None:
    """Drop what a run remembers (the record folders, the import graphs, the scopes): the next question reads the repository again."""
    WORLDS.clear()
    SCOPES.clear()
    INDEXES.clear()


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
    scope.shared_components = {cid for cid, _, sols in index.components if cid in own_ids and sols - set(solutions)}
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
            world = world_of(config, index)
            scope.foreign = world.implementations - scope.own_files
            closure, whole = set(scope.own_files), True
            for rel in scope.own_files:
                if rel in world.closures:
                    found, ok = world.closures[rel]
                    closure |= found
                    whole = whole and ok
                else:
                    whole = False
            scope.shared = {h for h in closure - world.implementations if world.importers.get(h, set()) - scope.own_files}
            scope.closure = (closure & scope.own_files) | (closure - scope.shared - world.implementations) | (closure & world.implementations & scope.own_files)
            scope.complete = whole
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
        if path in scope.shared:
            return False, "a helper shared with other implementations: nobody's own code"
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
    if owner and scope.requested == "import_closure" and owner in scope.shared_components:
        return False, f"owned by component {owner}, which other solutions share: not this arm's own code"
    if owner:
        return True, f"owned by {owner}"
    other = first_match(scope.others, path)
    if other:
        return False, f"owned by component {other}"
    if scope.requested == "import_closure":
        return False, "owned by no component and not found in the arm's own imports: not the arm's own code"
    return True, "owned by no component, so it counts for every arm"
