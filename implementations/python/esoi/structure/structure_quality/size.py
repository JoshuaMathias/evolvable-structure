"""Dimension 2, size and cohesion: parts small enough to read whole, and not so many that the folder cannot be read either.

Six parts (the dimension is their geometric mean, so one part that fails pulls it down). Three are graded by how far over the budget a part goes, so a
5000-line function costs fifty times a 200-line one instead of counting as one offender among thousands: the share of function lines inside the
function budget (outermost functions, so a nested function is not counted twice), the share of module lines inside the module budget, and the share of
decision points inside the complexity budget (McCabe's count per function, ``complexity.py``). Three are shares of items: files by the folder they
sit in (only the files past a folder's budget count as out of it), solutions per intent folder (read from the records beside the code), and files by
depth. Shrinking files raises the graded parts and lowers the folder and depth parts, and the coupling and reuse dimensions pay for the split, which is
why this is one part of the number and not the number.
"""
from __future__ import annotations

import csv
from pathlib import PurePosixPath
from typing import Dict, List, Tuple

from esoi.structure.structure_quality.balance import Budgets, Dimension, combine, share
from esoi.structure.structure_quality.project import Project


def intent_children(project: Project) -> List[Tuple[str, int]]:
    """Per folder holding an ``intent.csv``, the solutions it groups: its own rows and those of folders directly below it that are not intents."""
    root = project.root
    out: List[Tuple[str, int]] = []
    for relative in project.named["intent.csv"]:
        folder = (root / relative).parent
        count = 0
        for solutions in [folder / "solutions.csv", *sorted(folder.glob("*/solutions.csv"))]:
            if solutions.parent != folder and (solutions.parent / "intent.csv").exists():
                continue
            if solutions.is_file():
                with solutions.open(newline="", encoding="utf-8") as handle:
                    count += sum(1 for _ in csv.DictReader(handle))
        out.append((folder.relative_to(root).as_posix() or ".", count))
    return out


def within(sizes: List[int], budget: int):
    """The share of the total that sits inside the budget: ``1 - sum of the excess over the budget / sum of the sizes``, None when there is nothing."""
    total = sum(sizes)
    return None if total <= 0 else round(1 - sum(max(0, n - budget) for n in sizes) / total, 4)


def size_offenders(project: Project, budgets: Budgets, functions: list, long_modules: list, crowded: dict, wide: list, deep: list) -> List[str]:
    """The lines naming what is over a size budget, worst first within each kind."""
    long_functions = sorted((f for f in functions if f[5] and f[3] > budgets.function_lines), key=lambda f: -f[3])
    complex_functions = sorted((f for f in functions if f[4] > budgets.complexity), key=lambda f: -f[4])
    offenders = [f"{p}: function {n} is {length} lines (budget {budgets.function_lines})" for p, n, _, length, _, _ in long_functions]
    offenders += [f"{m.path}: {m.lines} lines (budget {budgets.module_lines})" for m in long_modules]
    offenders += [f"{p}: function {n} has complexity {c} (budget {budgets.complexity})" for p, n, _, _, c, _ in complex_functions[:50]]
    offenders += [f"{f}: {n} files in one folder (budget {budgets.files_per_folder})" for f, n in sorted(crowded.items(), key=lambda kv: -kv[1])]
    offenders += [f"{f}: groups {n} solutions (budget {budgets.children_per_intent})" for f, n in sorted(wide, key=lambda kv: -kv[1])]
    offenders += [f"{m.path}: {len(PurePosixPath(m.path).parts) - 1} folders deep (budget {budgets.depth})" for m in deep[:10]]
    return offenders


def wide_intents(project: Project, budgets: Budgets) -> Tuple[list, list]:
    """Every intent folder with its count of child solutions, and those over the budget."""
    children = intent_children(project)
    return children, [(f, n) for f, n in children if n > budgets.children_per_intent]


def crowded_folders(project: Project, budgets: Budgets) -> Tuple[Dict[str, int], int]:
    """The folders holding more files than the budget, and how many files lie past the budget in all of them."""
    crowded = {f: n for f, n in project.folder_files().items() if n > budgets.files_per_folder}
    return crowded, sum(n - budgets.files_per_folder for n in crowded.values())


def measure(project: Project, budgets: Budgets) -> Dimension:
    modules = list(project.modules.values())
    functions = [(m.path, name, line, length, decisions, outermost) for m in modules for name, line, length, decisions, outermost in m.functions]
    outermost = [f for f in functions if f[5]]
    long_modules = sorted((m for m in modules if m.lines > budgets.module_lines), key=lambda m: -m.lines)
    crowded, files_in_crowded = crowded_folders(project, budgets)
    deep = [m for m in modules if len(PurePosixPath(m.path).parts) - 1 > budgets.depth]
    children, wide = wide_intents(project, budgets)
    parts = {"function_lines_within_budget": within([f[3] for f in outermost], budgets.function_lines),
             "module_lines_within_budget": within([m.lines for m in modules], budgets.module_lines),
             "decisions_within_complexity_budget": within([f[4] for f in functions], budgets.complexity),
             "files_in_folders_within_budget": share(len(modules) - files_in_crowded, len(modules)),
             "intents_within_children_budget": share(len(children) - len(wide), len(children)),
             "files_within_depth_budget": share(len(modules) - len(deep), len(modules))}
    offenders = size_offenders(project, budgets, functions, long_modules, crowded, wide, deep)
    return Dimension("size", combine(list(parts.values())), {k: v for k, v in parts.items() if v is not None}, offenders)
