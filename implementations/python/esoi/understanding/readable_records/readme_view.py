"""The facts and small text helpers every generated README shares: layout constants, the loaded view of a repository, implementation labels, entry calls, metric leaders and the rendered height of a page."""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from esoi.structure.intent_registry import intents
from esoi.optimization.leaderboard import ranking, results_log
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.intents import Intent
from esoi.structure.intent_registry.registry import Registry, harness_arms
from esoi.structure.intent_registry.tables import repo_files, written

FILE = "README.md"
LAYOUTS = ("glance", "full", "links")
DEFAULT_LAYOUT = "glance"
FIRST_SCREEN_LINES = 100  # the vision, the solution coherence and the diagram all end inside this many rendered lines (two laptop screens)
DIAGRAM_LINES = 20        # a Mermaid block renders as a picture about this tall, whatever its source length
WRAP = 110                # characters of prose per rendered line
SUMMARY_LINES = 320       # the part of a page above its divider stays within this many rendered lines
LIST_LIMIT = 10           # a short list in the summary shows this many entries; the full record below holds them all

FIRST_LINE = ("These are ESOI records (evolvable structure that optimizes intent): why {subject} exists, and its problems, "
              "solutions, implementations, ideals and metrics. This page is generated from the CSV files beside it by "
              "`esoi check --write-docs`; edit the CSV files, not this page.")
NOTE = ("*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by "
        "`esoi readmes`. Edit the CSV files, not this page.*")
DIVIDER = "---"
RECORD_FILES = (("problems.csv", "problems"), ("ideals.csv", "ideals"), ("solutions.csv", "solutions"),
                ("implementations.csv", "implementations"), ("metrics.csv", "metrics"))


def impl_label(registry: Registry, solution_id: str, selected: str) -> str:
    """A selected implementation as a person reads it: its human name first and its handle in code font, ``Name (`handle`)``. ``selected``
    may be the arm's name, its full id or its file; with no record or no name the handle is shown alone."""
    picked = one_line(selected)
    if not picked:
        return "none selected"
    for row in registry.implementations:
        ident = row.get("implementation_id", "")
        if row.get("solution_id") == solution_id and (ident == picked or ident == f"{solution_id}:{picked}"
                                                      or (row.get("filepath", "").partition("::")[0].strip() == picked)):
            name = one_line(row.get("name", ""))
            if name and name.lower() != picked.lower():
                return f"{name} (`{picked}`)"
    return f"`{picked}`"


def list_item(row: Dict[str, str], key: str, text_key: str, limit: int = 0) -> str:
    """One bullet of a list of problems or ideals: ``- Name (`id`): sentence``; a record with no name leads with its sentence and puts the id
    after it (``- sentence (`id`)``), never the id first."""
    ident = row.get(key, "")
    name = one_line(row.get("name", ""))
    sentence = first_sentence(row.get(text_key, "")) if limit == 0 else first_sentence(row.get(text_key, ""), limit)
    if name and name.lower() != ident.lower():
        return f"- {name} (`{ident}`)" + (f": {sentence}" if sentence else "")
    return f"- {sentence} (`{ident}`)" if sentence else f"- `{ident}`"


def named(row: Dict[str, str], key: str) -> str:
    """A record as a person reads it: its ``name`` leading and its id after it as a code-font handle, ``Name (`id`)``. A record with no
    name is shown by its id alone. The id is the stable handle that commands and links use; the name is what every page leads with."""
    ident = row.get(key, "")
    name = one_line(row.get("name", ""))
    if name.lower().startswith(ident.lower() + ":"):
        name = name[len(ident) + 1:].strip()
    if not name or name.lower() == ident.lower():
        sentence = first_sentence(row.get("problem", "") or row.get("principle", ""))   # until a record has a name its sentence leads, never the id
        name = sentence if sentence and key in ("problem_id", "ideal_id") else ""
    return f"{name} (`{ident}`)" if name and name.lower() != ident.lower() else f"`{ident}`"


def one_line(text: str) -> str:
    """One line of a cell for a table or a list: whitespace folded, pipes made safe, an ``unconfirmed:`` marker dropped."""
    return " ".join(written(text).split()).replace("|", "/")


def metric_names(cell: str) -> str:
    """The metric names of a solution row ('none yet' when it has none), each written, joined by commas."""
    return ", ".join(n for n in (one_line(part) for part in (cell or "").split(";")) if n) or "none yet"


def first_sentence(text: str, limit: int = 0) -> str:
    """The first sentence of a cell, whole: a reader gets the complete sentence, never one cut at a character count (``limit`` is kept
    only so callers that pass one still work, and is ignored)."""
    clean = one_line(text)
    found = re.search(r"(?<=[.!?])\s", clean)
    return clean[:found.start()] if found else clean


def mine(rows: List[Dict[str, str]], intent_id: str) -> List[Dict[str, str]]:
    return [r for r in rows if r.get("intent_id", intent_id) == intent_id]


@dataclass
class View:
    """What a page needs to know beyond its own intent's records: the other intents (for links), the configuration, the results log
    (for each metric's leader) and the entry calls the code declares."""
    config: Optional[Config] = None
    intents: List[Intent] = field(default_factory=list)
    results: Dict[str, Dict[str, Dict[str, str]]] = field(default_factory=dict)
    declared: Dict[str, Any] = field(default_factory=dict)
    files: Optional[List[str]] = None   # the repository's files (git's list), for the ownership map's globs
    declared_all: Any = None   # every declaration the code makes (solutions and implementations), for the files that implement a solution
    beside: List[Tuple[str, Path]] = field(default_factory=list)   # (owning intent id, folder) of each solution folder kept beside the code

    def intent(self, intent_id: str) -> Optional[Intent]:
        return next((i for i in self.intents if i.intent_id == intent_id), None)


def view_of(config: Config, registry: Registry, results: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None) -> View:
    """The View of a repository (``results`` defaults to the latest rows of its results log)."""
    from esoi.structure.intent_registry.specify_from_code import declarations
    try:
        scanned = declarations.scan(config)
        declared = scanned.solutions
    except (OSError, ValueError):
        scanned, declared = None, {}
    return View(config, intents.discover(config),
                results_log.latest_results(config.results_path) if results is None else results, declared,
                repo_files(config.root), scanned,
                [(owner, folder) for owner, folder, has in intents.located(config) if not has])


def layout_of(config: Optional[Config], layout: Optional[str] = None) -> str:
    chosen = layout or ((config.readme.get("layout") if config is not None and isinstance(config.readme, dict) else "") or DEFAULT_LAYOUT)
    if chosen not in LAYOUTS:
        raise ValueError(f"unknown README layout {chosen!r}; choose one of {', '.join(LAYOUTS)}")
    return chosen


def link(folder: Path, target: Path) -> str:
    """A relative markdown link target from ``folder`` to ``target`` (posix)."""
    return Path(os.path.relpath(target, folder)).as_posix()


def recorded_call(row: Optional[Dict[str, str]]) -> str:
    """The call a solution's own records give in its language: the first code span of its ``usage_notes`` ('' when there is none).
    A repository of any language records its entry call there, so its page needs no Python declaration."""
    found = re.search(r"`([^`\n]+)`", written((row or {}).get("usage_notes", "")))
    return found.group(1).strip() if found else ""


def entry_call(view: View, config_package: str, solution_id: str, row: Optional[Dict[str, str]] = None) -> str:
    """The one-line call of a solution (``package.run("id", example)`` for Python code that declares it, or the call written in the
    solution's ``usage_notes`` in any language), or the plain statement that none is declared."""
    decl = view.declared.get(solution_id)
    if decl is None or not getattr(decl, "entry", "") and not getattr(decl, "kind", ""):
        recorded = recorded_call(row)
        return f"`{recorded}`".replace("|", "/") if recorded else "no entry declared"
    package = config_package or "package"
    if getattr(decl, "has_example", False) and decl.example is not None:
        shown = repr(decl.example)
        shown = shown if len(shown) <= 48 else "..."
        return f"`{package}.run(\"{solution_id}\", {shown})`".replace("|", "/")
    return f"`{package}.run(\"{solution_id}\")`"


def leader(view: View, metric: Dict[str, str]) -> str:
    """The implementation that leads a metric's first component in the results log, with its score ('' when none is recorded)."""
    if view.config is None:
        return ""
    arms = harness_arms(view.config, metric.get("command", ""))
    if not arms:
        return ""
    rows = view.results.get(arms[0][0], {})
    ranked = ranking.rank(rows) if rows else []
    if not ranked:
        return "no result recorded"
    top = ranked[0]
    return f"leader `{top['impl']}`, {top.get('passed', '?')} of {top.get('cases', '?')} cases"



def screen_lines(text: str) -> int:
    """How tall a block of markdown renders, in lines: prose wraps at ``WRAP`` characters and a Mermaid block counts as
    ``DIAGRAM_LINES`` whatever its source length."""
    total, inside = 0, False
    for line in text.splitlines():
        if line.startswith("```"):
            if not inside:
                total += DIAGRAM_LINES
            inside = not inside
            continue
        if not inside:
            total += max(1, math.ceil(len(line) / WRAP))
    return total
