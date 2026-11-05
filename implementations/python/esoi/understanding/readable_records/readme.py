"""A readable README.md for every intent folder, generated from its records (``esoi readmes``).

The CSV files hold the specification; a person clicking into an intent folder should not need to open five of them to learn what
it is, how its parts fit and where to go next. ``render`` writes the page from the records of one intent, so the page cannot
disagree with them and nothing in it is kept by hand. ``esoi readmes`` writes the pages, ``esoi readmes --check`` lists the stale
ones, and ``esoi check --write-docs`` calls the same code; rule S8 reports a page that is out of date. Prose a person wrote about the
network (a ``network.md``) is theirs and is left alone.

Three layouts are rival implementations of the solution ``readable-records`` and are measured on ``readme_at_a_glance`` (the
standard is in ``docs/reference/intent-readme.md``):

* ``glance``: what a person needs first, then the full record below a divider: name, vision statement and opportunities; how the
  solutions fit together; the Mermaid diagram inline; a solutions table with each solution's one-line entry call and selected
  implementation; problems and ideals as short lists; metrics with their current leader; links to sub-intents, the parent intent and
  the repository's top README; a divider; the full record tables.
* ``full``: the record tables only, in file order (the page before the standard).
* ``links``: name, vision statement and links to everything else.

``DEFAULT_LAYOUT`` is the arm the measurement selected; a repository overrides it with ``[readme] layout = "..."``. A cell that holds
only an ``unconfirmed:`` marker is an unwritten cell and is left out of the page, because a page states finished truth only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import Intent
from esoi.structure.intent_registry.registry import Registry
from esoi.understanding.readable_records.readme_view import FILE, View, layout_of, view_of
from esoi.understanding.readable_records.readme_intent_page import render_full, render_glance, render_links
from esoi.understanding.readable_records.readme_folder_page import arm_pages, render_folder

RENDERERS: Dict[str, Callable[[Registry, Intent, View], str]] = {"glance": render_glance, "full": render_full, "links": render_links}


def render(registry: Registry, intent: Intent, view: Optional[View] = None, layout: Optional[str] = None) -> str:
    """The README of one intent folder in the repository's layout (``layout`` overrides it)."""
    view = view or View()
    return RENDERERS[layout_of(view.config, layout)](registry, intent, view)


def pages(config: Config, registry: Registry, results: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None,
          layout: Optional[str] = None, written_arm_pages_only: bool = False) -> List[Tuple[Path, str]]:
    """``(path, expected text)`` for every intent folder's README (none in the legacy layout, which has no intent folders)."""
    if not config.intent_mode:
        return []
    with intents.session():   # the record folders are found once for every page
        view = view_of(config, registry, results)
        return ([(i.folder / FILE, render(registry, i, view, layout)) for i in view.intents]
                + [(folder / FILE, render_folder(registry, view, owner, folder)) for owner, folder in view.beside]
                + arm_pages(config, registry, view, existing_only=written_arm_pages_only))


def top_page(config: Config, registry: Registry, layout: Optional[str] = None) -> str:
    """The README text of the first intent folder (the top intent) in a layout: the first page ``pages`` lists, without rendering the others."""
    with intents.session():
        view = view_of(config, registry)
        return render(registry, view.intents[0], view, layout)


def stale(config: Config, registry: Registry, results: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None) -> List[Path]:
    return [path for path, text in pages(config, registry, results)
            if not path.exists() or path.read_text(encoding="utf-8") != text]


def write(config: Config, registry: Registry, say: Callable[[str], None] = print) -> int:
    """Write every page that differs from what the records generate; returns how many were written."""
    count = 0
    for path, text in pages(config, registry):
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            say(f"wrote {path.relative_to(config.root)}")
            count += 1
    return count


def run_cli(config: Config, check: bool = False, say: Callable[[str], None] = print) -> int:
    """``esoi readmes [--check]``: write each intent folder's README, or with ``check`` list the stale ones (exit 1)."""
    from esoi.structure.intent_registry import registry as registry_module
    if not config.intent_mode:
        say("no intents here (the legacy layout has no intent folders), so there is no README to write")
        return 0
    loaded = registry_module.load(config)
    if check:
        late = stale(config, loaded)
        for path in late:
            say(f"{path.relative_to(config.root)}: out of date (run `esoi readmes`)")
        if not late:
            say("esoi readmes ok")
        return 1 if late else 0
    write(config, loaded, say)
    return 0
