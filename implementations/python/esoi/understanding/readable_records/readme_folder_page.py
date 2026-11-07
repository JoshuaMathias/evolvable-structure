"""The README of a folder that holds code beside the records: the implemented-by listing, its diagram, links, and the arm pages of rival implementations."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from esoi.structure.intent_registry import besidecode, intents
from esoi.understanding.readable_records import diagram, readme_trail
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import Intent
from esoi.structure.intent_registry.registry import Registry
from esoi.structure.intent_registry.interface import implementedby
from esoi.structure.intent_registry.tables import read_csv
from esoi.understanding.readable_records.readme_view import ARM_NOTE, FILE, FOLDER_NOTE, View, entry_call, first_sentence, impl_label, leader, link, list_item, metric_names, mine, named, one_line

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


def direct_children(view: View, folder: Path) -> List[Path]:
    """The beside-code folders directly below ``folder``, with none between."""
    return [down for _, down in view.beside
            if folder in down.parents and not any(folder in f.parents and f in down.parents for _, f in view.beside)]


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
    out += [f"- Down: [{one_line(down.relative_to(config.root).as_posix())}]({link(folder, down / FILE)})"
            for down in direct_children(view, folder)]
    if (config.root / FILE).is_file():
        out.append(f"- Repository: [top README]({link(folder, config.root / FILE)})")
    return out


def one_level_below(registry: Registry, view: View, folder: Path) -> List[str]:
    """The section naming the children of a solution folder, each with its kind: a sub-intent that implements one of its solutions (with its
    vision statement) and each solution folder directly below it (a solution with implementations, with its purpose). A leaf solution has
    none, so it has no such section at all: its implementations under their own heading are all there is below it."""
    lines: List[str] = [readme_trail.sub_intent_line(child, folder)
                        for child in readme_trail.sub_intents_of(view, ids_in(folder, "solutions.csv", "solution_id"))]
    for down in readme_trail.child_folders(view, folder):
        lines += [solution_folder_line(view, registry, folder, down, sid) for sid in ids_in(down, "solutions.csv", "solution_id")]
    return ["## One level below", ""] + lines + [""] if lines else []


def solution_folder_line(view: View, registry: Registry, folder: Path, down: Path, sid: str) -> str:
    """The list line of one solution folder directly below ``folder``: its name, kind and purpose."""
    row = next((r for r in registry.every_solution() if r.get("solution_id", "") == sid), {})
    purpose = one_line(row.get("purpose", "")) or one_line(row.get("description", ""))
    return (f"- [{one_line(row.get('name', '')) or sid}]({link(folder, down / FILE)}) ({readme_trail.kind_of(view, registry, down)})"
            + (f": {purpose}" if purpose else ""))


def part_of_name(view: View, above: tuple) -> str:
    """The name shown for the page above: the top intent's own name when that page is the top, else the trail's label."""
    top = next((i for i in view.intents if not i.parent), None)
    return (one_line(top.row.get("name", "")) or top.intent_id) if above[0] == "Top" and top is not None else above[0]


def folder_heading(registry: Registry, view: View, owner: str, folder: Path, solutions: List[dict]) -> List[str]:
    """The title, the purpose of a lone solution, the breadcrumb and the line naming the page above."""
    heading_text = one_line(solutions[0].get("name", "")) if len(solutions) == 1 else folder.name
    lines = [f"# {heading_text or folder.name}", ""]
    parent = view.intent(owner)
    if parent is not None and parent.folder.resolve() != folder.resolve() and solutions:
        # A solution folder is not an intent: it shows its own name and purpose, and only points to the intent that owns it (the nearest
        # intent.csv at or above the folder). That intent's vision, paragraph and diagram stay on its own page.
        if len(solutions) == 1:
            purpose = one_line(solutions[0].get("purpose", "")) or one_line(solutions[0].get("description", ""))
            lines += [f"**Purpose:** {purpose}", ""] if purpose else []
    steps = readme_trail.folder_steps(view, registry, owner, folder)
    lines += [readme_trail.breadcrumb(folder, steps), ""]
    above = readme_trail.immediate_parent(steps)
    if above is not None:
        lines += [f"Part of [{part_of_name(view, above)}]({link(folder, above[1] / FILE)})", ""]
    return lines


def solution_section(registry: Registry, view: View, folder: Path, r: dict, show_purpose: bool) -> List[str]:
    """One solution of the folder: its heading, purpose, exclusions, entry call, selected implementation and metric."""
    sid = r.get("solution_id", "")
    lines = [f"## {one_line(r.get('name', '')) or sid} (`{sid}`)", ""]
    purpose = first_sentence(r.get("purpose", "")) or first_sentence(r.get("description", ""))
    if purpose and show_purpose:
        lines += [purpose, ""]
    picked = one_line(r.get("selected", ""))
    for label, column in (("Out of scope", "out_of_scope"), ("Delegates to", "delegates_to")):
        said = one_line(r.get(column, ""))
        said = ", ".join(part.strip() for part in said.split(";") if part.strip()) if column == "delegates_to" else said
        if said and said.lower().rstrip(".") != "none":
            lines.append(f"- {label}: {said}")
    lines += [f"- Entry call: {entry_call(view, view.config.package, sid, r)}",
              f"- Selected implementation: {impl_label(registry, sid, picked)}",
              f"- Metric: {metric_names(r.get('metric', ''))}"]
    return lines + implemented_line(registry, view, folder, sid) + [""]


def implementations_section(registry: Registry, view: View, folder: Path) -> List[str]:
    """The table of the implementations whose records sit in this folder, with a link to the code and whether each is selected."""
    mine_impl = set(ids_in(folder, "implementations.csv", "implementation_id"))
    impls = [r for r in registry.implementations if r.get("implementation_id", "") in mine_impl]
    if not impls:
        return []
    chosen = {r.get("solution_id", ""): one_line(r.get("selected", "")) for r in registry.every_solution()}
    lines = ["## Implementations", "", "| Implementation | Handle | Purpose | Code | Selected |", "|---|---|---|---|---|"]
    for r in impls:
        name = r.get("implementation_id", "").split(":", 1)[-1]
        lines.append(f"| {one_line(r.get('name', '')) or r.get('implementation_id', '')} | `{r.get('implementation_id', '')}` | {one_line(r.get('description', ''))} | "
                     f"{code_cell(view, folder, r.get('filepath', ''))} | "
                     f"{'selected' if chosen.get(r.get('solution_id', '')) in (name, r.get('implementation_id', '')) else ''} |")
    return lines + [""]


def metrics_section(registry: Registry, view: View, folder: Path) -> List[str]:
    """The metrics whose records sit in this folder, each with its leader."""
    metric_ids = set(ids_in(folder, "metrics.csv", "metric_id"))
    metrics = [r for r in registry.metrics if r.get("metric_id", "") in metric_ids]
    if not metrics:
        return []
    lines = ["## Metrics", ""]
    for r in metrics:
        tail = leader(view, r)
        lines.append(f"- {named(r, 'metric_id')}" + (f": {tail}" if tail else ""))
    return lines + [""]


def problems_and_ideals(registry: Registry, folder: Path) -> List[str]:
    """The problems and the ideals whose records sit in this folder."""
    lines: List[str] = []
    problem_ids, ideal_ids = set(ids_in(folder, "problems.csv", "problem_id")), set(ids_in(folder, "ideals.csv", "ideal_id"))
    for title, rows, key, column in (("Problems", [r for r in registry.problems if r.get("problem_id", "") in problem_ids], "problem_id", "problem"),
                                     ("Ideals", [r for r in registry.ideals if r.get("ideal_id", "") in ideal_ids], "ideal_id", "principle")):
        if rows:
            lines += [f"## {title}", ""] + [list_item(r, key, column) for r in rows] + [""]
    return lines


def render_folder(registry: Registry, view: View, owner: str, folder: Path) -> str:
    """The README of a solution folder kept beside its code: each solution it holds, with its entry call and selected
    implementation, the implementations it holds with a link to the code, the metrics with their leaders, the problems and
    ideals, links up and down, and the diagram when the folders below it hold solutions it builds on."""
    solutions = [r for r in registry.every_solution() if r.get("solution_id", "") in ids_in(folder, "solutions.csv", "solution_id")]
    lines = folder_heading(registry, view, owner, folder, solutions)
    parent = view.intent(owner)
    single, parent_shown = len(solutions) == 1, parent is not None and parent.folder.resolve() != folder.resolve()
    for r in solutions:
        lines += solution_section(registry, view, folder, r, not (single and parent_shown))
    lines += one_level_below(registry, view, folder)
    picture = folder_diagram(registry, view, owner, folder)
    if picture:
        lines += ["## Diagram", "", "An arrow runs from the solution that provides to the solution that builds on it; its label is "
                  "what the provider outputs.", ""] + picture + [""]
    lines += implementations_section(registry, view, folder) + metrics_section(registry, view, folder) + problems_and_ideals(registry, folder)
    lines += ["## Where to go next", ""] + folder_links(view, owner, folder) + ["", FOLDER_NOTE]
    return "\n".join(lines).rstrip() + "\n"


def arm_table(registry: Registry, view: View, folder: Path) -> List[str]:
    """The table of the implementations whose code lies directly in this folder, with whether each is selected."""
    config = view.config
    mine = []
    for row in registry.implementations:
        path = (row.get("filepath", "") or "").split("::")[0].strip()
        if path and (config.root / path).resolve().parent == folder.resolve():
            mine.append(row)
    chosen = {r.get("solution_id", ""): one_line(r.get("selected", "")) for r in registry.every_solution()}
    lines = ["| Implementation | Handle | Code | Selected |", "|---|---|---|---|"]
    for r in sorted(mine, key=lambda r: r.get("implementation_id", "")):
        name = r.get("implementation_id", "").split(":", 1)[-1]
        lines.append(f"| {one_line(r.get('name', '')) or r.get('implementation_id', '')} | `{r.get('implementation_id', '')}` | {code_cell(view, folder, r.get('filepath', ''))} | "
                     f"{'selected' if chosen.get(r.get('solution_id', '')) in (name, r.get('implementation_id', '')) else ''} |")
    return lines


def render_arms(registry: Registry, view: View, folder: Path, owners: List[Tuple[str, Path]]) -> str:
    """The README of a folder of arm code whose records belong to an intent elsewhere: the arms it holds, each with its code and
    the intent that owns it, and a link to every owning intent's README."""
    config = view.config
    lines = [f"# Arms in {folder.name}", ""]
    first = view.intent(owners[0][0]) if owners else None
    if first is not None:
        trail = [(readme_trail.label(i), i.folder) for i in readme_trail.intent_chain(view, first)] + [(f"Arms in {folder.name}", None)]
        lines += [readme_trail.breadcrumb(folder, trail), ""]
    lines += arm_table(registry, view, folder)
    lines += ["", "## Where to go next", ""]
    for owner, owner_folder in owners:
        intent = view.intent(owner)
        label = (one_line(intent.row.get("name", "")) if intent is not None else "") or owner
        lines.append(f"- Owning intent: [{label}]({link(folder, owner_folder / FILE)})")
    if (config.root / FILE).is_file():
        lines.append(f"- Repository: [top README]({link(folder, config.root / FILE)})")
    return "\n".join(lines + ["", ARM_NOTE]).rstrip() + "\n"


def arm_pages(config: Config, registry: Registry, view: View, existing_only: bool = False) -> List[Tuple[Path, str]]:
    """``(path, text)`` for the README of each folder of arms owned by an intent elsewhere. A folder that already has a README this
    command did not write keeps it (it covers the folder); ``existing_only`` leaves out the ones not written yet."""
    out: List[Tuple[Path, str]] = []
    for folder, owners in sorted(besidecode.arm_folders(config).items()):
        path = folder / FILE
        if path.is_file() and ARM_NOTE not in path.read_text(encoding="utf-8"):
            continue
        if existing_only and not path.is_file():
            continue
        out.append((path, render_arms(registry, view, folder, owners)))
    return out
