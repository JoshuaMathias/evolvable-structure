"""Dimension 2, size and cohesion: parts small enough to read whole, and not so many that the folder cannot be read either.

Five parts, each a share of items inside its budget (the dimension is their geometric mean, so one part that fails pulls it down): functions by count, modules by count, files by the folder they sit in (only the files past a
folder's budget count as out of it), solutions per intent folder (read from the records beside the code), and files by depth.
Shrinking files raises the first two and lowers the third and fifth, and the coupling and reuse dimensions pay for the split, which is why this
is one part of the number and not the number.
"""
from __future__ import annotations

import csv
from pathlib import Path, PurePosixPath
from typing import List, Tuple

from esoi.structure.structure_quality.balance import Budgets, Dimension, combine, share
from esoi.structure.structure_quality.project import SKIPPED, Project


def intent_children(root: Path) -> List[Tuple[str, int]]:
    """Per folder holding an ``intent.csv``, the solutions it groups: its own rows and those of folders directly below it that are not intents."""
    out: List[Tuple[str, int]] = []
    for intent in root.rglob("intent.csv"):
        rel = intent.relative_to(root)
        if SKIPPED & set(rel.parts):
            continue
        folder = intent.parent
        count = 0
        for solutions in [folder / "solutions.csv", *sorted(folder.glob("*/solutions.csv"))]:
            if solutions.parent != folder and (solutions.parent / "intent.csv").exists():
                continue
            if solutions.is_file():
                with solutions.open(newline="", encoding="utf-8") as handle:
                    count += sum(1 for _ in csv.DictReader(handle))
        out.append((folder.relative_to(root).as_posix() or ".", count))
    return out


def measure(project: Project, budgets: Budgets) -> Dimension:
    modules = list(project.modules.values())
    functions = [(m.path, name, line, length) for m in modules for name, line, length in m.functions]
    long_functions = sorted((f for f in functions if f[3] > budgets.function_lines), key=lambda f: -f[3])
    long_modules = sorted((m for m in modules if m.lines > budgets.module_lines), key=lambda m: -m.lines)
    counts = project.folder_files()
    crowded = {f: n for f, n in counts.items() if n > budgets.files_per_folder}
    files_in_crowded = sum(n - budgets.files_per_folder for n in crowded.values())   # the files past the budget
    deep = [m for m in modules if len(PurePosixPath(m.path).parts) - 1 > budgets.depth]
    children = intent_children(project.root)
    wide = [(f, n) for f, n in children if n > budgets.children_per_intent]
    parts = {"functions_within_budget": share(len(functions) - len(long_functions), len(functions)),
             "modules_within_budget": share(len(modules) - len(long_modules), len(modules)),
             "files_in_folders_within_budget": share(len(modules) - files_in_crowded, len(modules)),
             "intents_within_children_budget": share(len(children) - len(wide), len(children)),
             "files_within_depth_budget": share(len(modules) - len(deep), len(modules))}
    offenders = [f"{p}: function {n} is {length} lines (budget {budgets.function_lines})" for p, n, _, length in long_functions]
    offenders += [f"{m.path}: {m.lines} lines (budget {budgets.module_lines})" for m in long_modules]
    offenders += [f"{f}: {n} files in one folder (budget {budgets.files_per_folder})" for f, n in sorted(crowded.items(), key=lambda kv: -kv[1])]
    offenders += [f"{f}: groups {n} solutions (budget {budgets.children_per_intent})" for f, n in sorted(wide, key=lambda kv: -kv[1])]
    offenders += [f"{m.path}: {len(PurePosixPath(m.path).parts) - 1} folders deep (budget {budgets.depth})" for m in deep[:10]]
    return Dimension("size", combine(list(parts.values())), {k: v for k, v in parts.items() if v is not None}, offenders)
