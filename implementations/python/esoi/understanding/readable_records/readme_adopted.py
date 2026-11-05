"""The part of an intent's README about solutions adopted or specialized from a library (``docs/explanation/adopting-solutions-from-a-library.md``).

An adopted solution is a link to the library's page, with the library's own name and description of it read from the library when the page is
generated and never copied into this repository's records. A specialized solution is a normal solution; here it also says which library solution
it specializes. A reference that does not resolve is shown by its handle alone (rule S53 informs of it).
"""
from __future__ import annotations

import posixpath
from pathlib import Path
from typing import List

from esoi.structure.intent_registry.intents import Intent
from esoi.structure.intent_registry.registry import Registry
from esoi.structure.library_adoption import resolve
from esoi.understanding.readable_records.readme_view import View, first_sentence, link, mine, one_line


def target(lib: resolve.Library, solution_id: str, folder: Path) -> str:
    """Where the library's page for a solution is: under the configured ``url`` when there is one, else a relative path; '' when it has no page."""
    page = lib.page(solution_id)
    if page is None or lib.root is None:
        return ""
    if lib.url:
        return lib.url.rstrip("/") + "/" + posixpath.normpath(page.relative_to(lib.root).as_posix())
    return link(folder, page)


def entry(libraries: resolve.Libraries, ref: resolve.Reference, folder: Path) -> str:
    """One bullet for a reference: ``- [Library name](link) (`local id`): the library's description, first sentence. Library: name.``"""
    lib = libraries.get(ref.library)
    row = lib.solution(ref.solution_id) if not lib.error else None
    if row is None:
        return f"- `{ref.local_id}` ({ref.kind} `@{ref.library}/{ref.solution_id}`, not resolved)"
    name = one_line(row.get("name", "")) or ref.solution_id
    where = target(lib, ref.solution_id, folder)
    shown = f"[{name}]({where})" if where else name
    said = first_sentence(row.get("description", "") or row.get("purpose", ""))
    verb = "Specializes" if ref.kind == "specializes" else "Adopted from"
    return f"- {shown} (`{ref.local_id}`): {said + ' ' if said else ''}{verb} the library `{ref.library}`."


def lines(view: View, registry: Registry, intent: Intent, level: str = "##") -> List[str]:
    """The section for this intent's adopted and specialized solutions, empty when it has none."""
    if view.config is None:
        return []
    refs, _ = resolve.references(view.config, registry)
    own = {r.get("solution_id", "") for r in mine(registry.every_solution() + registry.adopted, intent.intent_id)}
    mine_refs = [r for r in refs if r.local_id in own]
    if not mine_refs:
        return []
    libraries = resolve.Libraries(view.config)
    return [f"{level} Solutions from a library", ""] + [entry(libraries, r, intent.folder) for r in mine_refs] + [""]
