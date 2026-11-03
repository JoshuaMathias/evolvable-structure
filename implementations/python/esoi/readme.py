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

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import diagram, intents, leaderboard
from .config import Config
from .intents import Intent
from .registry import Registry, harness_arms
from .tables import read_csv, written

FILE = "README.md"
LAYOUTS = ("glance", "full", "links")
DEFAULT_LAYOUT = "glance"
FIRST_SCREEN_LINES = 100  # the vision, the solution coherence and the diagram all end inside this many rendered lines (two laptop screens)
DIAGRAM_LINES = 20        # a Mermaid block renders as a picture about this tall, whatever its source length
WRAP = 110                # characters of prose per rendered line
SUMMARY_LINES = 320       # the part of a page above its divider stays within this many rendered lines
SENTENCE_CHARS = 200
LIST_LIMIT = 10           # a short list in the summary shows this many entries; the full record below holds them all

FIRST_LINE = ("These are ESOI records (evolvable structure that optimizes intent): why {subject} exists, and its problems, "
              "solutions, implementations, ideals and metrics. This page is generated from the CSV files beside it by "
              "`esoi check --write-docs`; edit the CSV files, not this page.")
NOTE = ("*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by "
        "`esoi readmes`. Edit the CSV files, not this page.*")
DIVIDER = "---"
RECORD_FILES = (("problems.csv", "problems"), ("ideals.csv", "ideals"), ("solutions.csv", "solutions"),
                ("implementations.csv", "implementations"), ("metrics.csv", "metrics"))


def one_line(text: str) -> str:
    """One line of a cell for a table or a list: whitespace folded, pipes made safe, an ``unconfirmed:`` marker dropped."""
    return " ".join(written(text).split()).replace("|", "/")


def metric_names(cell: str) -> str:
    """The metric names of a solution row ('none yet' when it has none), each written, joined by commas."""
    return ", ".join(n for n in (one_line(part) for part in (cell or "").split(";")) if n) or "none yet"


def first_sentence(text: str, limit: int = SENTENCE_CHARS) -> str:
    """The first sentence of a cell, cut at a word with an ellipsis when it is longer than ``limit``."""
    clean = one_line(text)
    found = re.search(r"(?<=[.!?])\s", clean)
    sentence = clean[:found.start()] if found else clean
    if len(sentence) > limit:
        sentence = sentence[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "..."
    return sentence


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
    beside: List[Tuple[str, Path]] = field(default_factory=list)   # (owning intent id, folder) of each solution folder kept beside the code

    def intent(self, intent_id: str) -> Optional[Intent]:
        return next((i for i in self.intents if i.intent_id == intent_id), None)


def view_of(config: Config, registry: Registry, results: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None) -> View:
    """The View of a repository (``results`` defaults to the latest rows of its results log)."""
    from . import declarations
    try:
        declared = declarations.scan(config).solutions
    except (OSError, ValueError):
        declared = {}
    return View(config, intents.discover(config),
                leaderboard.latest_results(config.results_path) if results is None else results, declared,
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
    ranked = leaderboard.rank(rows) if rows else []
    if not ranked:
        return "no result recorded"
    top = ranked[0]
    return f"leader `{top['impl']}`, {top.get('passed', '?')} of {top.get('cases', '?')} cases"


def heading(intent: Intent) -> List[str]:
    name = one_line(intent.row.get("name", "")) or intent.intent_id
    out = [f"# {name}", ""]
    if intent.row.get("vision_statement", "").strip():
        out += [one_line(intent.row["vision_statement"]), ""]
    return out


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
        vision = first_sentence(child.row.get("vision_statement", ""))
        out.append(f"- Sub-intent: [{name}]({link(intent.folder, child.folder / FILE)}) ({vision})" if vision
                   else f"- Sub-intent: [{name}]({link(intent.folder, child.folder / FILE)})")
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


def solutions_table(view: View, registry: Registry, intent: Intent) -> List[str]:
    rows = mine(registry.every_solution(), intent.intent_id)
    if not rows:
        return []
    package = view.config.package if view.config else ""
    lines = ["| Solution | Entry call | Selected implementation | Metric |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r.get('solution_id', '')}` | {entry_call(view, package, r.get('solution_id', ''), r)} | "
                     f"{('`' + one_line(r['selected']) + '`') if one_line(r.get('selected', '')) else 'none selected'} | "
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
            text = first_sentence(r.get("problem", ""))
            out.append(f"- `{r.get('problem_id', '')}`" + (f": {text}" if text else ""))
        out += more(len(problems), "problems") + [""]
    ideals = mine(registry.ideals, intent.intent_id)
    if ideals:
        out += ["**Ideals**", ""]
        for r in ideals[:LIST_LIMIT]:
            text = first_sentence(r.get("principle", ""))
            name = one_line(r.get("name", ""))
            out.append(f"- `{r.get('ideal_id', '')}`" + (f", {name}" if name else "") + (f": {text}" if text else ""))
        out += more(len(ideals), "ideals") + [""]
    return out


def metric_lines(view: View, registry: Registry, intent: Intent) -> List[str]:
    out = []
    rows = mine(registry.metrics, intent.intent_id)
    for r in rows[:LIST_LIMIT]:
        head = f"- `{r.get('metric_id', '')}`, {one_line(r.get('name', ''))}"
        tail = leader(view, r)
        out.append(head + (f": {tail}" if tail else ""))
    return out + more(len(rows), "metrics")


def record_tables(registry: Registry, intent: Intent, level: str = "##", view: Optional[View] = None) -> List[str]:
    """The full record: every problem, ideal, solution, implementation and metric of the intent, by id."""
    iid = intent.intent_id
    lines: List[str] = []
    problems = mine(registry.problems, iid)
    if problems:
        lines += [f"{level} Problems", ""] + [f"- `{r.get('problem_id', '')}`: {one_line(r.get('problem', ''))}" for r in problems] + [""]
    ideals = mine(registry.ideals, iid)
    if ideals:
        lines += [f"{level} Ideals", ""] + [f"- `{r.get('ideal_id', '')}`, {one_line(r.get('name', ''))}: {one_line(r.get('principle', ''))}"
                                           for r in ideals] + [""]
    solutions = mine(registry.every_solution(), iid)
    if solutions:
        lines += [f"{level} Solutions", "", "| Solution | Name | Selected | Metric |", "|---|---|---|---|"]
        lines += [f"| `{r.get('solution_id', '')}` | {one_line(r.get('name', ''))} | {one_line(r.get('selected', ''))} | "
                  f"{metric_names(r.get('metric', ''))} |" for r in solutions] + [""]
    implementations = mine(registry.implementations, iid)
    if implementations:
        lines += [f"{level} Implementations", "", "| Implementation | Name | Where | Sub-intent |", "|---|---|---|---|"]
        lines += [f"| `{r.get('implementation_id', '')}` | {one_line(r.get('name', ''))} | {one_line(r.get('filepath', ''))} | "
                  f"{('[' + r['sub_intent'] + '](' + r['sub_intent'] + '/README.md)') if r.get('sub_intent') else ''} |"
                  for r in implementations] + [""]
    metrics = mine(registry.metrics, iid)
    if metrics:
        lines += [f"{level} Metrics", ""] + [f"- `{r.get('metric_id', '')}`, {one_line(r.get('name', ''))}: "
                                            f"`{one_line(r.get('command', '')) or 'none'}`" for r in metrics] + [""]
    return lines


def render_full(registry: Registry, intent: Intent, view: View) -> str:
    """The record tables only (the page as it was before the at-a-glance standard)."""
    lines = [FIRST_LINE.format(subject="this project" if intent.is_top else "this sub-intent"), ""] + heading(intent)
    if not intent.is_top:
        lines += [f"This sub-intent arises as the implementation `{intent.row.get('implements', '')}` of its parent "
                  f"intent `{intent.parent}`. Opportunities: {one_line(intent.row.get('opportunities', ''))}", ""]
    if intent.row.get("solution_coherence", "").strip():
        lines += ["## How the solutions fit together", "", one_line(intent.row["solution_coherence"]), ""]
    return "\n".join(lines + record_tables(registry, intent)).rstrip() + "\n"


def render_glance(registry: Registry, intent: Intent, view: View) -> str:
    """The at-a-glance page: the summary a reader needs first, a divider, then the full record."""
    lines = heading(intent) + [NOTE, ""]
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
    table = solutions_table(view, registry, intent)
    if table:
        lines += ["## Solutions at a glance", ""] + table + [""]
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
    return "\n".join(lines + record_tables(registry, intent, "###")).rstrip() + "\n"


def render_links(registry: Registry, intent: Intent, view: View) -> str:
    """A compact page: name, vision statement and links to everything else."""
    lines = heading(intent) + [NOTE, ""]
    if not intent.is_top:
        lines += [arises(view, intent), ""]
    counts = []
    for name, key in RECORD_FILES:
        n = len(mine(registry.every_solution() if key == "solutions" else getattr(registry, key), intent.intent_id))
        counts.append(f"[{key} ({n})]({name})" if (intent.folder / name).is_file() else f"{key} ({n})")
    nav = navigation(view, registry, intent)
    lines += ["## Go to", ""] + [line for line in nav if not line.startswith("- Records")] + ["- Records: " + ", ".join(counts), ""]
    return "\n".join(lines).rstrip() + "\n"


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
    for r in solutions:
        sid = r.get("solution_id", "")
        lines += [f"## {one_line(r.get('name', '')) or sid} (`{sid}`)", ""]
        purpose = first_sentence(r.get("purpose", "")) or first_sentence(r.get("description", ""))
        if purpose:
            lines += [purpose, ""]
        picked = one_line(r.get("selected", ""))
        lines += [f"- Entry call: {entry_call(view, config.package, sid, r)}",
                  f"- Selected implementation: {('`' + picked + '`') if picked else 'none selected'}",
                  f"- Metric: {metric_names(r.get('metric', ''))}", ""]
    picture = folder_diagram(registry, view, owner, folder)
    if picture:
        lines += ["## Diagram", "", "An arrow runs from the solution that provides to the solution that builds on it; its label is "
                  "what the provider outputs.", ""] + picture + [""]
    mine_impl = set(ids_in(folder, "implementations.csv", "implementation_id"))
    impls = [r for r in registry.implementations if r.get("implementation_id", "") in mine_impl]
    if impls:
        chosen = {r.get("solution_id", ""): one_line(r.get("selected", "")) for r in registry.every_solution()}
        lines += ["## Implementations", "", "| Implementation | Name | Code | Selected |", "|---|---|---|---|"]
        for r in impls:
            name = r.get("implementation_id", "").split(":", 1)[-1]
            lines.append(f"| `{r.get('implementation_id', '')}` | {one_line(r.get('name', ''))} | {code_cell(view, folder, r.get('filepath', ''))} | "
                         f"{'selected' if chosen.get(r.get('solution_id', '')) in (name, r.get('implementation_id', '')) else ''} |")
        lines.append("")
    metric_ids = set(ids_in(folder, "metrics.csv", "metric_id"))
    metrics = [r for r in registry.metrics if r.get("metric_id", "") in metric_ids]
    if metrics:
        lines += ["## Metrics", ""]
        for r in metrics:
            tail = leader(view, r)
            lines.append(f"- `{r.get('metric_id', '')}`, {one_line(r.get('name', ''))}" + (f": {tail}" if tail else ""))
        lines.append("")
    problem_ids, ideal_ids = set(ids_in(folder, "problems.csv", "problem_id")), set(ids_in(folder, "ideals.csv", "ideal_id"))
    for title, rows, key, column in (("Problems", [r for r in registry.problems if r.get("problem_id", "") in problem_ids], "problem_id", "problem"),
                                     ("Ideals", [r for r in registry.ideals if r.get("ideal_id", "") in ideal_ids], "ideal_id", "principle")):
        if rows:
            lines += [f"## {title}", ""] + [f"- `{r.get(key, '')}`" + (f": {first_sentence(r.get(column, ''))}" if first_sentence(r.get(column, '')) else "")
                                             for r in rows] + [""]
    lines += ["## Where to go next", ""] + folder_links(view, owner, folder) + [""]
    return "\n".join(lines).rstrip() + "\n"


RENDERERS: Dict[str, Callable[[Registry, Intent, View], str]] = {"glance": render_glance, "full": render_full, "links": render_links}


def render(registry: Registry, intent: Intent, view: Optional[View] = None, layout: Optional[str] = None) -> str:
    """The README of one intent folder in the repository's layout (``layout`` overrides it)."""
    view = view or View()
    return RENDERERS[layout_of(view.config, layout)](registry, intent, view)


def pages(config: Config, registry: Registry, results: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None,
          layout: Optional[str] = None) -> List[Tuple[Path, str]]:
    """``(path, expected text)`` for every intent folder's README (none in the legacy layout, which has no intent folders)."""
    if not config.intent_mode:
        return []
    view = view_of(config, registry, results)
    return ([(i.folder / FILE, render(registry, i, view, layout)) for i in view.intents]
            + [(folder / FILE, render_folder(registry, view, owner, folder)) for owner, folder in view.beside])


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
    from . import registry as registry_module
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
