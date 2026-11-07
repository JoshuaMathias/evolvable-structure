"""The Solution Diagram of each intent, generated from its records: how the intent's solutions connect, what is transferred on
each edge, and in which direction (the skill's optional intent field ``solution_diagram``).

The records already say it. An implementation builds on other solutions through their interfaces (``uses_solution_ids``), so the
solution that is built on gives its output to the solution whose implementation builds on it. A node is a solution of the intent;
an edge runs from the solution that provides to the one that uses it and is labelled with the provider's ``outputs`` cell (what is
transferred). Only solutions of the same intent are drawn; a dependency across intents is read from the records themselves.

``render`` returns Mermaid (which GitHub renders) in a ``diagram.md`` beside the intent's records, written by ``esoi diagram`` and by
``esoi check --write-docs``, and reported by rule S8 when out of date. The hand-written ``solution_diagram`` field holds only what the
interfaces do not say: a flow no implementation declares yet, or a note on why the edges are shaped as they are. An intent with no
edge gets no diagram file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Tuple

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import Intent, discover
from esoi.structure.intent_registry.registry import Registry
from esoi.structure.intent_registry.tables import ids, written
from esoi.understanding.readable_records.readme_view import without_id_prefix

FILE = "diagram.md"
HEADER = ("These are ESOI records rendered as a diagram (evolvable structure that optimizes intent). This page is generated from the "
          "solutions' outputs and the implementations' `uses_solution_ids` by `esoi diagram`; edit those records, not this page.")


def clip(text: str, limit: int = 0) -> str:
    """One line of a cell, without characters Mermaid reads as syntax. Never cut: the whole text is the label (``limit`` is ignored)."""
    clean = " ".join(written(text).replace('"', "'").replace("|", "/").replace("[", "(").replace("]", ")").split())
    return clean.rstrip(".")


def edges(registry: Registry, intent_id: str) -> Dict[Tuple[str, str], str]:
    """{(provider solution id, user solution id): what is transferred} among the solutions of one intent."""
    own = {r.get("solution_id", ""): r for r in registry.every_solution() if r.get("intent_id", intent_id) == intent_id}
    found: Dict[Tuple[str, str], str] = {}
    for impl in registry.implementations:
        user = impl.get("solution_id", "")
        for provider in ids(impl.get("uses_solution_ids", "")):
            if user in own and provider in own and provider != user:
                found.setdefault((provider, user), clip(own[provider].get("outputs", "")))
    return found


def label_of(sid: str, name: str) -> str:
    """A node's label: the display name as the headline and the id as a small italic second line. A name that is only its id (or starts
    with the id and a colon) is shown once, never as ``id: name`` twice."""
    shown = without_id_prefix(" ".join((name or "").split()), sid)
    if not shown or shown.lower() == sid.lower():
        return clip(sid, 40)
    return f"{clip(shown, 40)}<br/><i>{sid}</i>"


def block(registry: Registry, intent: Intent) -> List[str]:
    """The fenced Mermaid source of one intent's diagram, as lines ([] when no solution of it builds on another). The diagram page
    and the intent's README both embed these lines, so the two cannot differ."""
    found = edges(registry, intent.intent_id)
    if not found:
        return []
    names = {r.get("solution_id", ""): r.get("name", "") for r in registry.every_solution()}
    order = [r.get("solution_id") for r in registry.every_solution()]
    used = sorted({s for pair in found for s in pair}, key=order.index)
    node = {sid: f"s{i}" for i, sid in enumerate(used)}
    lines = ["```mermaid", "flowchart LR"]
    lines += [f'    {node[sid]}["{label_of(sid, names.get(sid, ""))}"]' for sid in used]
    for (provider, user), label in sorted(found.items(), key=lambda kv: (used.index(kv[0][0]), used.index(kv[0][1]))):
        lines.append(f'    {node[provider]} -->|"{label}"| {node[user]}' if label else f"    {node[provider]} --> {node[user]}")
    return lines + ["```"]


def render(registry: Registry, intent: Intent) -> str:
    """The diagram page of one intent ("" when no solution of it builds on another)."""
    lines = block(registry, intent)
    if not lines:
        return ""
    paragraph = " ".join((intent.row.get("solution_coherence") or "").split())
    head = [HEADER, "", f"# Solution diagram: {intent.row.get('name', '') or intent.intent_id}", ""]
    if paragraph:
        head += [paragraph, ""]   # the intent's own account of how its solutions fit, above the picture of it
    head += ["An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.", ""]
    return "\n".join(head + lines + [""])


def pages(config: Config, registry: Registry) -> List[Tuple[Path, str]]:
    """(path, expected text) for every intent's diagram page; the text is "" when the intent should have none."""
    return [(intent.folder / FILE, render(registry, intent)) for intent in discover(config)]


def stale(config: Config, registry: Registry) -> List[Path]:
    out = []
    for path, text in pages(config, registry):
        if text and (not path.exists() or path.read_text(encoding="utf-8") != text):
            out.append(path)
        elif not text and path.exists():
            out.append(path)
    return out


def write(config: Config, registry: Registry, say: Callable[[str], None] = print) -> None:
    for path, text in pages(config, registry):
        if text:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")
                say(f"wrote {path.relative_to(config.root)}")
        elif path.exists():
            path.unlink()
            say(f"removed {path.relative_to(config.root)} (no solution of the intent builds on another)")


def run_cli(config: Config, check: bool = False, say: Callable[[str], None] = print) -> int:
    """``esoi diagram [--check]``: write each intent's diagram page, or with ``check`` list the ones out of date (exit 1)."""
    from esoi.structure.intent_registry import registry as registry_module
    loaded = registry_module.load(config)
    if not config.intent_mode:
        say("no intents here (the legacy layout has no intent folders), so there is no diagram to draw")
        return 0
    if check:
        late = stale(config, loaded)
        for path in late:
            say(f"{path.relative_to(config.root)}: out of date (run `esoi diagram`)")
        if not late:
            say("esoi diagram ok")
        return 1 if late else 0
    write(config, loaded, say)
    return 0
