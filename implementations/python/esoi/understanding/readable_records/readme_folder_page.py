"""The README of a folder that holds code beside the records: the implemented-by listing, its diagram, links, and the arm pages of rival implementations."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
from esoi.structure.intent_registry import besidecode, intents
from esoi.understanding.readable_records import diagram
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import Intent
from esoi.structure.intent_registry.registry import Registry
from esoi.structure.intent_registry import implementedby
from esoi.structure.intent_registry.tables import read_csv
from esoi.understanding.readable_records.readme_view import FILE, View, entry_call, first_sentence, impl_label, leader, link, list_item, metric_names, mine, named, one_line

def ids_in(folder: Path, name: str, key: str) -> List[str]:
    """The record ids one folder's own file holds, in file order."""
    return [r.get(key, "").strip() for r in read_csv(folder / name) if r.get(key, "").strip()]


def code_cell(view: View, folder: Path, filepath: str) -> str:
    """An implementation's code as a link from the folder's page when the file exists, else the path as written."""
    path = filepath.split("::")[0].strip()
    if not path:
        return "no code yet"
    if view.config is not None and (view.config.root / path).is_file():
        return f"[`{path}`]({link(folder, view.config.root / path)})"
    return f"`{one_line(path)}`"


def implemented_line(registry: Registry, view: View, folder: Path, solution_id: str) -> List[str]:
    """``- Implemented by: ...``: the files that implement a solution as links from the folder's page, generated from the records, the
    declarations and the ownership map (never hand-kept), at most ``implementedby.CAP`` of them."""
    files = implementedby.implemented_by(view.config, registry, solution_id, view.declared_all, view.files)
    if not files:
        return []
    root = view.config.root
    shown = [f"[`{f}`]({link(folder, root / f)})" for f in files[:implementedby.CAP]]
    rest = len(files) - len(shown)
    return ["- Implemented by: " + ", ".join(shown) + (f" and {rest} more" if rest > 0 else "")]


def folder_diagram(registry: Registry, view: View, owner: str, folder: Path) -> List[str]:
    """The Mermaid diagram of the solutions held in this folder and in the folders below it, when one builds on another."""
    below = [f for _, f in view.beside if f == folder or folder in f.parents]
    own = {s for f in below for s in ids_in(f, "solutions.csv", "solution_id")}
    rows = [r for r in registry.every_solution() if r.get("solution_id", "") in own]
    if len(rows) < 2:
        return []
    shaped = Registry(solutions=rows, solution_order=[r.get("solution_id", "") for r in rows],
                      implementations=[r for r in registry.implementations if r.get("solution_id", "") in own])
    return diagram.block(shaped, Intent(owner, folder))


def folder_links(view: View, owner: str, folder: Path) -> List[str]:
    config = view.config
    out: List[str] = []
    parents = [f for _, f in view.beside if f in folder.parents]
    up = parents[-1] if parents else None
    if up is not None:
        out.append(f"- Up: [{one_line(up.relative_to(config.root).as_posix())}]({link(folder, up / FILE)})")
    parent = view.intent(owner)
    if parent is not None:
        out.append(f"- Intent: [{one_line(parent.row.get('name', '')) or parent.intent_id}]({link(folder, parent.folder / FILE)})")
    for _, down in view.beside:
        if folder in down.parents and not any(folder in f.parents and f in down.parents for _, f in view.beside):
            out.append(f"- Down: [{one_line(down.relative_to(config.root).as_posix())}]({link(folder, down / FILE)})")
    if (config.root / FILE).is_file():
        out.append(f"- Repository: [top README]({link(folder, config.root / FILE)})")
    return out


def render_folder(registry: Registry, view: View, owner: str, folder: Path) -> str:
    """The README of a solution folder kept beside its code: each solution it holds, with its entry call and selected
    implementation, the implementations it holds with a link to the code, the metrics with their leaders, the problems and
    ideals, links up and down, and the diagram when the folders below it hold solutions it builds on."""
    config = view.config
    where = folder.relative_to(config.root).as_posix()
    solutions = [r for r in registry.every_solution() if r.get("solution_id", "") in ids_in(folder, "solutions.csv", "solution_id")]
    heading_text = one_line(solutions[0].get("name", "")) if len(solutions) == 1 else folder.name
    lines = [f"# {heading_text or folder.name}", "",
             f"*ESOI records kept beside the code in `{where}`, generated from the CSV files in this folder by `esoi readmes`. "
             "Edit the CSV files, not this page.*", ""]
    parent = view.intent(owner)
    if parent is not None and parent.folder.resolve() != folder.resolve() and solutions:
        # The folder holds the solutions of an intent whose own page is elsewhere: open with that intent's purpose and how its solutions fit.
        vision = one_line(parent.row.get("vision_statement", ""))
        if vision:
            lines += [vision, ""]
        lines += [f"These are the solutions of [{one_line(parent.row.get('name', '')) or parent.intent_id}]({link(folder, parent.folder / FILE)}).", ""]
        if parent.row.get("solution_coherence", "").strip():
            lines += ["## How the solutions fit together", "", one_line(parent.row["solution_coherence"]), ""]
        picture = diagram.block(registry, parent)
        if picture:
            lines += ["## Overview diagram", "", "An arrow runs from the solution that provides to the solution that builds on it; its label is "
                      "what the provider outputs.", ""] + picture + [""]
    for r in solutions:
        sid = r.get("solution_id", "")
        lines += [f"## {one_line(r.get('name', '')) or sid} (`{sid}`)", ""]
        purpose = first_sentence(r.get("purpose", "")) or first_sentence(r.get("description", ""))
        if purpose:
            lines += [purpose, ""]
        picked = one_line(r.get("selected", ""))
        lines += [f"- Entry call: {entry_call(view, config.package, sid, r)}",
                  f"- Selected implementation: {impl_label(registry, sid, picked)}",
                  f"- Metric: {metric_names(r.get('metric', ''))}"]
        lines += implemented_line(registry, view, folder, sid) + [""]
    picture = folder_diagram(registry, view, owner, folder)
    if picture:
        lines += ["## Diagram", "", "An arrow runs from the solution that provides to the solution that builds on it; its label is "
                  "what the provider outputs.", ""] + picture + [""]
    mine_impl = set(ids_in(folder, "implementations.csv", "implementation_id"))
    impls = [r for r in registry.implementations if r.get("implementation_id", "") in mine_impl]
    if impls:
        chosen = {r.get("solution_id", ""): one_line(r.get("selected", "")) for r in registry.every_solution()}
        lines += ["## Implementations", "", "| Implementation | Handle | Code | Selected |", "|---|---|---|---|"]
        for r in impls:
            name = r.get("implementation_id", "").split(":", 1)[-1]
            lines.append(f"| {one_line(r.get('name', '')) or r.get('implementation_id', '')} | `{r.get('implementation_id', '')}` | {code_cell(view, folder, r.get('filepath', ''))} | "
                         f"{'selected' if chosen.get(r.get('solution_id', '')) in (name, r.get('implementation_id', '')) else ''} |")
        lines.append("")
    metric_ids = set(ids_in(folder, "metrics.csv", "metric_id"))
    metrics = [r for r in registry.metrics if r.get("metric_id", "") in metric_ids]
    if metrics:
        lines += ["## Metrics", ""]
        for r in metrics:
            tail = leader(view, r)
            lines.append(f"- {named(r, 'metric_id')}" + (f": {tail}" if tail else ""))
        lines.append("")
    problem_ids, ideal_ids = set(ids_in(folder, "problems.csv", "problem_id")), set(ids_in(folder, "ideals.csv", "ideal_id"))
    for title, rows, key, column in (("Problems", [r for r in registry.problems if r.get("problem_id", "") in problem_ids], "problem_id", "problem"),
                                     ("Ideals", [r for r in registry.ideals if r.get("ideal_id", "") in ideal_ids], "ideal_id", "principle")):
        if rows:
            lines += [f"## {title}", ""] + [list_item(r, key, column) for r in rows] + [""]
    lines += ["## Where to go next", ""] + folder_links(view, owner, folder) + [""]
    return "\n".join(lines).rstrip() + "\n"


ARM_MARK = "ESOI arms kept in"


def render_arms(registry: Registry, view: View, folder: Path, owners: List[Tuple[str, Path]]) -> str:
    """The README of a folder of arm code whose records belong to an intent elsewhere: the arms it holds, each with its code and
    the intent that owns it, and a link to every owning intent's README."""
    config = view.config
    where = folder.relative_to(config.root).as_posix()
    here = {f.resolve(): owner for owner, f in owners}
    mine = []
    for row in registry.implementations:
        path = (row.get("filepath", "") or "").split("::")[0].strip()
        if path and (config.root / path).resolve().parent == folder.resolve():
            mine.append(row)
    lines = [f"# Arms in {folder.name}", "",
             f"*{ARM_MARK} `{where}`, generated from the records of the intents that own them by `esoi readmes`. Edit those records, not this page.*", ""]
    chosen = {r.get("solution_id", ""): one_line(r.get("selected", "")) for r in registry.every_solution()}
    lines += ["| Implementation | Handle | Code | Selected |", "|---|---|---|---|"]
    for r in sorted(mine, key=lambda r: r.get("implementation_id", "")):
        name = r.get("implementation_id", "").split(":", 1)[-1]
        lines.append(f"| {one_line(r.get('name', '')) or r.get('implementation_id', '')} | `{r.get('implementation_id', '')}` | {code_cell(view, folder, r.get('filepath', ''))} | "
                     f"{'selected' if chosen.get(r.get('solution_id', '')) in (name, r.get('implementation_id', '')) else ''} |")
    lines += ["", "## Where to go next", ""]
    for owner, owner_folder in owners:
        intent = view.intent(owner)
        label = (one_line(intent.row.get("name", "")) if intent is not None else "") or owner
        lines.append(f"- Owning intent: [{label}]({link(folder, owner_folder / FILE)})")
    if (config.root / FILE).is_file():
        lines.append(f"- Repository: [top README]({link(folder, config.root / FILE)})")
    return "\n".join(lines).rstrip() + "\n"


def arm_pages(config: Config, registry: Registry, view: View, existing_only: bool = False) -> List[Tuple[Path, str]]:
    """``(path, text)`` for the README of each folder of arms owned by an intent elsewhere. A folder that already has a README this
    command did not write keeps it (it covers the folder); ``existing_only`` leaves out the ones not written yet."""
    out: List[Tuple[Path, str]] = []
    for folder, owners in sorted(besidecode.arm_folders(config).items()):
        path = folder / FILE
        if path.is_file() and ARM_MARK not in path.read_text(encoding="utf-8")[:600]:
            continue
        if existing_only and not path.is_file():
            continue
        out.append((path, render_arms(registry, view, folder, owners)))
    return out
