"""A project's shared kernel: the low-level modules many units import by design (configuration, the records registry, error types, a storage
base), told apart from another solution's internals.

A module is a kernel when three things hold. Many units depend on it: at least ``Budgets.min_kernel_importers`` other units import it. It is stable
(Martin's instability, fan-out over fan-in plus fan-out, counted in units, is at most ``Budgets.kernel_instability``). And it depends on no solution:
every module of another unit in its import closure is itself a kernel or a declared entry (the acyclic and stable dependencies principles; found as
a fixed point, so a module that reaches up into a solution, directly or through a helper, is never one). An import of a kernel is clean only when
every name it takes is taken by two or more units (the common reuse principle: a name one unit alone uses belongs in that unit, so moving a unit's
own code into a foundation module does not make its imports look shared).

Why: on three repositories with history to read (2026-11-05, the last 400 commits, files modified in place), an importer changed with its target
in 3 percent of the target's changes for a kernel against 11 percent for other reach-ins in one, 19 against 47 in another and 1.4 against 6.4 in the
third, about as rarely as imports through declared entries; names that one unit alone takes changed with it 14 to 50 percent of the time. The fourth
repository had been reorganized so recently that its kernels had 8 recorded changes, too few to say.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Set, Tuple

from esoi.structure.structure_quality.balance import Budgets
from esoi.structure.structure_quality.project import Project

Edge = Tuple[str, str, str, str, Tuple[str, ...]]   # from unit, to unit, from file, to file, names taken


def file_dependencies(project: Project, targets: Callable[[Project, str, Tuple[str, ...]], List[str]]) -> Dict[str, Set[str]]:
    """Per module, the project modules it imports (in any unit)."""
    deps: Dict[str, Set[str]] = defaultdict(set)
    for module in project.modules.values():
        for base, names in module.imports:
            for target in targets(project, base, names):
                if target in project.modules and target != module.path:
                    deps[module.path].add(target)
    return deps


def closure(start: str, deps: Dict[str, Set[str]]) -> Set[str]:
    seen: Set[str] = set()
    stack = [start]
    while stack:
        for nxt in deps.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def fan_counts(edges: List[Edge]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """For each file the units that import it, and for each file the units it imports."""
    fan_in: Dict[str, Set[str]] = defaultdict(set)
    fan_out: Dict[str, Set[str]] = defaultdict(set)
    for from_unit, to_unit, from_file, to_file, _ in edges:
        fan_in[to_file].add(from_unit)
        fan_out[from_file].add(to_unit)
    return fan_in, fan_out


def kernels(project: Project, edges: List[Edge], is_entry: Callable[[str], bool], budgets: Budgets,
            targets: Callable[[Project, str, Tuple[str, ...]], List[str]]) -> Set[str]:
    """The modules of the project's shared kernel (see the module docstring)."""
    fan_in, fan_out = fan_counts(edges)
    found = {path for path, units in fan_in.items()
             if len(units) >= budgets.min_kernel_importers and len(fan_out[path]) / (len(units) + len(fan_out[path])) <= budgets.kernel_instability}
    deps = file_dependencies(project, targets)
    reach = {path: closure(path, deps) for path in found}
    changed = True
    while changed:
        changed = False
        for path in sorted(found):
            unit = project.modules[path].unit
            if any(project.modules[o].unit != unit and o not in found and not is_entry(o) for o in reach[path]):
                found.discard(path)
                changed = True
    return found


def shared_names(edges: List[Edge]) -> Dict[str, Dict[str, Set[str]]]:
    """Per target module, per name taken from it, the units that take it."""
    out: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    for from_unit, _, _, to_file, names in edges:
        for name in names:
            out[to_file][name].add(from_unit)
    return out


def single_unit_names(edge: Edge, takers: Dict[str, Dict[str, Set[str]]]) -> List[str]:
    """The names an import of a kernel takes that only its own unit takes (empty when the import is a shared use)."""
    return [n for n in edge[4] if len(takers[edge[3]][n]) < 2]
