"""Where a generated page sits in the hierarchy of pages: the breadcrumb line, the immediate parent, which solutions have a page of their own, and
whether a solution folder is the bottom of the hierarchy (implemented by alternatives only) or goes deeper (sub-intents or solutions below it)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from esoi.structure.intent_registry.intents import Intent
from esoi.structure.intent_registry.registry import Registry
from esoi.structure.intent_registry.tables import read_csv
from esoi.understanding.readable_records.readme_view import FILE, View, link, one_line

Step = Tuple[str, Optional[Path]]   # (label, the folder whose README it links to; None for the page itself)


def solution_ids_in(folder: Path) -> List[str]:
    """The solution ids one folder's own ``solutions.csv`` holds, in file order."""
    return [r.get("solution_id", "").strip() for r in read_csv(folder / "solutions.csv") if r.get("solution_id", "").strip()]


def solution_folders(view: View) -> Dict[str, Path]:
    """{solution id: the folder beside the code that holds it and has a README of its own}."""
    return {sid: folder for _, folder in view.beside for sid in solution_ids_in(folder)}


def folder_title(registry: Registry, folder: Path) -> str:
    """What a solution folder is called: its solution's name when it holds one solution, else the folder's name."""
    ids = solution_ids_in(folder)
    rows = [r for r in registry.every_solution() if r.get("solution_id", "") in ids]
    return (one_line(rows[0].get("name", "")) if len(rows) == 1 else "") or folder.name


def intent_chain(view: View, intent: Intent) -> List[Intent]:
    """The intent and its ancestors, the top intent first."""
    chain = [intent]
    while chain[0].parent:
        up = view.intent(chain[0].parent)
        if up is None or up in chain:
            break
        chain.insert(0, up)
    return chain


def label(intent: Intent) -> str:
    """How a breadcrumb names an intent: the top intent is ``Top``, every other one is its name."""
    return "Top" if not intent.parent else one_line(intent.row.get("name", "")) or intent.intent_id


def intent_steps(view: View, intent: Intent) -> List[Step]:
    """The steps from the top intent to this intent."""
    chain = intent_chain(view, intent)
    return [(label(i), i.folder) for i in chain[:-1]] + [(label(intent), None)]


def folder_steps(view: View, registry: Registry, owner: str, folder: Path) -> List[Step]:
    """The steps to a solution folder: its owning intent's chain, then each solution folder above it, then the folder itself."""
    parent = view.intent(owner)
    steps: List[Step] = [(label(i), i.folder) for i in intent_chain(view, parent)] if parent is not None else []
    above = sorted((f for _, f in view.beside if f in folder.parents and (parent is None or parent.folder in f.parents)), key=lambda f: len(f.parts))
    steps += [(folder_title(registry, f), f) for f in above]
    return steps + [(folder_title(registry, folder), None)]


def breadcrumb(from_folder: Path, steps: List[Step]) -> str:
    """``Top > [Container](link) > ... > this page``: every ancestor linked to its README, the page itself plain."""
    return "Breadcrumb: " + " > ".join(f"[{label}]({link(from_folder, where / FILE)})" if where is not None else label for label, where in steps)


def immediate_parent(steps: List[Step]) -> Optional[Step]:
    """The step just above the page, or None for the top page."""
    return steps[-2] if len(steps) > 1 else None


def sub_intent_line(child: Intent, from_folder: Path) -> str:
    """The list line of a sub-intent: its name linked from ``from_folder``, then its vision statement."""
    vision = one_line(child.row.get("vision_statement", ""))
    name = one_line(child.row.get("name", "")) or child.intent_id
    return f"- [{name}]({link(from_folder, child.folder / FILE)}) (sub-intent)" + (f": {vision}" if vision else "")


def sub_intents_of(view: View, solution_ids: List[str]) -> List[Intent]:
    """The sub-intents that implement any of these solutions (an intent's ``implements`` is ``solution:implementation``)."""
    return [i for i in view.intents if i.row.get("implements", "").partition(":")[0].strip() in solution_ids]


def has_page_above(view: View, owner: Intent, folder: Path) -> bool:
    """Whether another solution folder inside the owning intent's folder lies above this one, so its page is listed there and not on the intent's."""
    return any(f in folder.parents and owner.folder in f.parents for _, f in view.beside)


def child_folders(view: View, folder: Path) -> List[Path]:
    """The solution folders directly below a folder (no other solution folder between them)."""
    return [down for _, down in view.beside if folder in down.parents
            and not any(folder in f.parents and f in down.parents for _, f in view.beside)]


def is_bottom(view: View, registry: Registry, folder: Path) -> bool:
    """A solution folder is the bottom of the hierarchy when no sub-intent implements its solutions and no solution folder lies below it."""
    ids = solution_ids_in(folder)
    own = {r.get("implementation_id", "") for r in read_csv(folder / "implementations.csv") if r.get("sub_intent", "").strip()}
    return not sub_intents_of(view, ids) and not own and not child_folders(view, folder)


def kind_of(view: View, registry: Registry, folder: Path) -> str:
    """How a parent page names a solution folder before the reader clicks: whether it ends there or goes deeper."""
    return "solution with implementations" if is_bottom(view, registry, folder) else "solution with implementations and parts below it"


def solution_page_line(view: View, registry: Registry, base: Path, row: dict, folder: Optional[Path]) -> str:
    """The list line of one solution seen from the page in ``base``: a link to its own page with its kind and purpose, or a note that it has no page."""
    sid = row.get("solution_id", "")
    purpose = one_line(row.get("purpose", "")) or one_line(row.get("description", ""))
    name = one_line(row.get("name", "")) or sid
    tail = f": {purpose}" if purpose else ""
    if folder is not None:
        return f"- [{name}]({link(base, folder / FILE)}) ({kind_of(view, registry, folder)})" + tail
    return f"- {name} (solution with no page of its own, its implementations are in this intent's records)" + tail
