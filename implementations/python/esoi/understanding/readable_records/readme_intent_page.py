"""The README of one intent folder in each layout (glance, full, links): heading, navigation, solutions table, short lists, metrics and the full record tables."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from esoi.understanding.readable_records import diagram, readme_adopted, readme_trail
from esoi.structure.intent_registry.intents import Intent
from esoi.structure.intent_registry.registry import Registry
from esoi.understanding.readable_records.readme_view import DIVIDER, FILE, LIST_LIMIT, NOTE, RECORD_FILES, View, entry_call, first_sentence, impl_label, leader, link, list_item, metric_names, mine, named, one_line, vision_lines

def heading(intent: Intent, view: View) -> List[str]:
    """The title, the vision statement under it, and the breadcrumb line to this page."""
    name = one_line(intent.row.get("name", "")) or intent.intent_id
    return [f"# {name}", ""] + vision_lines(intent.row.get("vision_statement", "")) + \
        [readme_trail.breadcrumb(intent.folder, readme_trail.intent_steps(view, intent)), ""]


def arises(view: View, intent: Intent) -> str:
    """The sentence saying which implementation of which parent intent a sub-intent is."""
    parent = view.intent(intent.parent)
    where = f"[`{intent.parent}`]({link(intent.folder, parent.folder / FILE)})" if parent and view.config else f"`{intent.parent}`"
    return f"This sub-intent arises as the implementation `{intent.row.get('implements', '')}` of its parent intent {where}."


def navigation(view: View, registry: Registry, intent: Intent) -> List[str]:
    """Where to go next: sub-intents, the parent intent, the repository's top README and the record files."""
    if view.config is None:
        return []
    root = view.config.root
    out: List[str] = []
    children = [i for i in view.intents if i.parent == intent.intent_id]
    for child in children:
        name = one_line(child.row.get("name", "")) or child.intent_id
        out.append(f"- Sub-intent: [{name}]({link(intent.folder, child.folder / FILE)})")
    parent = view.intent(intent.parent) if intent.parent else None
    if parent is not None:
        out.append(f"- Parent intent: [{one_line(parent.row.get('name', '')) or parent.intent_id}]({link(intent.folder, parent.folder / FILE)})")
    if (root / FILE).is_file():
        out.append(f"- Repository: [top README]({link(intent.folder, root / FILE)})")
    places = [folder for owner, folder in view.beside if owner == intent.intent_id]
    if places:
        out.append("- Records beside the code: " + ", ".join(f"[{one_line(folder.relative_to(root).as_posix())}]({link(intent.folder, folder / FILE)})"
                                                            for folder in places))
    shown = [f"[{name}]({name})" for name, _ in RECORD_FILES if (intent.folder / name).is_file()]
    if (intent.folder / "intent.csv").is_file():
        shown.insert(0, "[intent.csv](intent.csv)")
    if shown:
        out.append("- Records: " + ", ".join(shown))
    if diagram.block(registry, intent):
        out.append("- Diagram page: [diagram.md](diagram.md)")
    return out


def one_level_below(view: View, registry: Registry, intent: Intent) -> List[str]:
    """The section naming what lies one level below the intent, each child with its kind so a reader sees before clicking whether it goes
    deeper: a sub-intent with its vision statement, a solution with its own page (a solution with implementations) with its purpose, and a
    solution with no page of its own with its purpose and where its implementations are. A sub-intent is the implementation of one solution
    (``implements`` names ``solution:implementation``), so that solution is shown by the sub-intent."""
    children = [i for i in view.intents if i.parent == intent.intent_id]
    refined = {i.row.get("implements", "").partition(":")[0].strip() for i in children}
    held = readme_trail.solution_folders(view)
    lines: List[str] = []
    for child in children:
        name = one_line(child.row.get("name", "")) or child.intent_id
        vision = one_line(child.row.get("vision_statement", ""))
        lines.append(f"- [{name}]({link(intent.folder, child.folder / FILE)}) (sub-intent)" + (f": {vision}" if vision else ""))
    for r in mine(registry.every_solution(), intent.intent_id):
        sid = r.get("solution_id", "")
        folder = held.get(sid)
        if sid in refined or (folder is not None and readme_trail.has_page_above(view, intent, folder)):
            continue   # shown by its sub-intent, or listed on the page of the solution folder above it
        purpose = one_line(r.get("purpose", "")) or one_line(r.get("description", ""))
        name = one_line(r.get("name", "")) or sid
        if folder is not None:
            lines.append(f"- [{name}]({link(intent.folder, folder / FILE)}) ({readme_trail.kind_of(view, registry, folder)})" + (f": {purpose}" if purpose else ""))
        else:
            lines.append(f"- {name} (solution with no page of its own, its implementations are in this intent's records)" + (f": {purpose}" if purpose else ""))
    if not lines:
        return []
    return ["## One level below", "", "This intent is implemented by the sub-intents and solutions below it; each shows whether it goes deeper.", ""] + lines + [""]


def solutions_table(view: View, registry: Registry, intent: Intent) -> List[str]:
    rows = mine(registry.every_solution(), intent.intent_id)
    if not rows:
        return []
    package = view.config.package if view.config else ""
    lines = ["| Solution | Handle | Entry call | Selected implementation | Metric |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {one_line(r.get('name', '')) or r.get('solution_id', '')} | `{r.get('solution_id', '')}` | {entry_call(view, package, r.get('solution_id', ''), r)} | "
                     f"{impl_label(registry, r.get('solution_id', ''), r.get('selected', ''))} | "
                     f"{metric_names(r.get('metric', ''))} |")
    return lines


def more(total: int, name: str) -> List[str]:
    """The line that points from a capped short list to the full record below."""
    return [f"- and {total - LIST_LIMIT} more: all {total} are in [{name}](#{name}) of the full record below"] if total > LIST_LIMIT else []


def short_lists(registry: Registry, intent: Intent) -> List[str]:
    out: List[str] = []
    problems = mine(registry.problems, intent.intent_id)
    if problems:
        out += ["**Problems**", ""]
        for r in problems[:LIST_LIMIT]:
            out.append(list_item(r, "problem_id", "problem"))
        out += more(len(problems), "problems") + [""]
    ideals = mine(registry.ideals, intent.intent_id)
    if ideals:
        out += ["**Ideals**", ""]
        for r in ideals[:LIST_LIMIT]:
            out.append(list_item(r, "ideal_id", "principle"))
        out += more(len(ideals), "ideals") + [""]
    return out


def metric_lines(view: View, registry: Registry, intent: Intent) -> List[str]:
    out = []
    rows = mine(registry.metrics, intent.intent_id)
    for r in rows[:LIST_LIMIT]:
        head = f"- {named(r, 'metric_id')}"
        tail = leader(view, r)
        out.append(head + (f": {tail}" if tail else ""))
    return out + more(len(rows), "metrics")


def where_cell(view: Optional[View], folder: Path, filepath: str) -> str:
    """Where an implementation is: a link to the file (or registry) it names when that exists, else the path as written."""
    shown = one_line(filepath)
    entry = filepath.partition("::")[0].strip()
    if view is not None and view.config is not None and entry and (view.config.root / entry).is_file():
        return f"[{shown}]({link(folder, view.config.root / entry)})"
    return shown


def record_tables(registry: Registry, intent: Intent, level: str = "##", view: Optional[View] = None) -> List[str]:
    """The full record: every problem, ideal, solution, implementation and metric of the intent, by id."""
    iid = intent.intent_id
    lines: List[str] = []
    problems = mine(registry.problems, iid)
    if problems:
        lines += [f"{level} Problems", ""] + [list_item(r, "problem_id", "problem", 400) for r in problems] + [""]
    ideals = mine(registry.ideals, iid)
    if ideals:
        lines += [f"{level} Ideals", ""] + [list_item(r, "ideal_id", "principle", 400)
                                           for r in ideals] + [""]
    solutions = mine(registry.every_solution(), iid)
    if solutions:
        lines += [f"{level} Solutions", "", "| Solution | Handle | Selected | Metric |", "|---|---|---|---|"]
        lines += [f"| {one_line(r.get('name', '')) or r.get('solution_id', '')} | `{r.get('solution_id', '')}` | {impl_label(registry, r.get('solution_id', ''), r.get('selected', ''))} | "
                  f"{metric_names(r.get('metric', ''))} |" for r in solutions] + [""]
    implementations = mine(registry.implementations, iid)
    if implementations:
        lines += [f"{level} Implementations", "", "| Implementation | Handle | Where | Sub-intent |", "|---|---|---|---|"]
        lines += [f"| {one_line(r.get('name', '')) or r.get('implementation_id', '')} | `{r.get('implementation_id', '')}` | {where_cell(view, intent.folder, r.get('filepath', ''))} | "
                  f"{('[' + r['sub_intent'] + '](' + r['sub_intent'] + '/README.md)') if r.get('sub_intent') else ''} |"
                  for r in implementations] + [""]
    metrics = mine(registry.metrics, iid)
    if metrics:
        lines += [f"{level} Metrics", ""] + [f"- {named(r, 'metric_id')}: "
                                            f"`{one_line(r.get('command', '')) or 'none'}`" for r in metrics] + [""]
    return lines


def render_full(registry: Registry, intent: Intent, view: View) -> str:
    """The record tables only (the page as it was before the at-a-glance standard)."""
    lines = heading(intent, view)
    if not intent.is_top:
        lines += [f"This sub-intent arises as the implementation `{intent.row.get('implements', '')}` of its parent "
                  f"intent `{intent.parent}`. Opportunities: {one_line(intent.row.get('opportunities', ''))}", ""]
    if intent.row.get("solution_coherence", "").strip():
        lines += ["## How the solutions fit together", "", one_line(intent.row["solution_coherence"]), ""]
    lines += readme_adopted.lines(view, registry, intent)
    return "\n".join(lines + record_tables(registry, intent, "##", view) + [NOTE]).rstrip() + "\n"


def render_glance(registry: Registry, intent: Intent, view: View) -> str:
    """The at-a-glance page: the summary a reader needs first, a divider, then the full record."""
    lines = heading(intent, view)
    opportunities = one_line(intent.row.get("opportunities", ""))
    if not intent.is_top:
        lines += [arises(view, intent) + (f" Opportunities: {opportunities}" if opportunities else ""), ""]
    elif opportunities:
        lines += [f"Opportunities: {opportunities}", ""]
    if intent.row.get("solution_coherence", "").strip():
        lines += ["## How the solutions fit together", "", one_line(intent.row["solution_coherence"]), ""]
    picture = diagram.block(registry, intent)
    if picture:
        lines += ["## Diagram", "", "An arrow runs from the solution that provides to the solution that builds on it; its label is what "
                  "the provider outputs.", ""] + picture + [""]
    lines += one_level_below(view, registry, intent)
    table = solutions_table(view, registry, intent)
    if table:
        lines += ["## Solutions at a glance", ""] + table + [""]
    lines += readme_adopted.lines(view, registry, intent)
    shorts = short_lists(registry, intent)
    if shorts:
        lines += ["## Problems and ideals", ""] + shorts
    metrics = metric_lines(view, registry, intent)
    if metrics:
        lines += ["## Metrics and their leaders", ""] + metrics + [""]
    nav = navigation(view, registry, intent)
    if nav:
        lines += ["## Where to go next", ""] + nav + [""]
    lines += [DIVIDER, "", "## The full record", ""]
    return "\n".join(lines + record_tables(registry, intent, "###", view) + ["", NOTE]).rstrip() + "\n"


def render_links(registry: Registry, intent: Intent, view: View) -> str:
    """A compact page: name, vision statement and links to everything else."""
    lines = heading(intent, view)
    if not intent.is_top:
        lines += [arises(view, intent), ""]
    counts = []
    for name, key in RECORD_FILES:
        n = len(mine(registry.every_solution() if key == "solutions" else getattr(registry, key), intent.intent_id))
        counts.append(f"[{key} ({n})]({name})" if (intent.folder / name).is_file() else f"{key} ({n})")
    nav = navigation(view, registry, intent)
    lines += ["## Go to", ""] + [line for line in nav if not line.startswith("- Records")] + ["- Records: " + ", ".join(counts), "", NOTE]
    return "\n".join(lines).rstrip() + "\n"
