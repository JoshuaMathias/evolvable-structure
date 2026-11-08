"""The prompt for one solution's own consideration, formed from its network of records and nothing written for it by hand.

A solution is an area that deserves its own depth of focus, so a pass of AI that judges a change, a candidate or a finding against
it is given that solution's records first: its definition and Knowledge, every recorded result of its implementations, the
implementation the metric's cascade chose and the layer that runs it, its problems and ideals, the findings and candidates queued
against it, and the public evidence and priors kept for it. Its connected solutions follow at the depth their edge earns: the parent
briefly, the children and the dependencies by purpose, interface and selected implementation, the dependents by what they rely on.
A solution with children also gets the section that judges how its children combine (the child intent's coherence and diagram).

Every section has a tier (0 first). The prompt fills a size budget in tier order, so the closest and most decision-relevant records
come first and a section that does not fit is cut at a line and named, never silently skipped. Standard library only; no model call.
"""
from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from esoi.structure.intent_registry import intents as intents_module
from esoi.structure.intent_registry import registry as registry_module
from esoi.structure.intent_registry.tables import ids, read_csv
from esoi.understanding.solution_consideration import network_records

DEFAULT_BUDGET = 24000   # characters, about six thousand tokens
DETAIL_CHARS = 300
FIELD_CHARS = 900
NONE_WORDS = {"", "none", "-", "n/a"}
INSTRUCTIONS = (
    "You are giving one solution its own consideration. The records below are this solution's own memory and expertise: its "
    "definition, its recorded results, its selection and the records connected to it, closest first. Judge the matter against "
    "them before any general knowledge. A recorded result of this solution outranks a reputation or a public claim: when a "
    "candidate or an arm has already been measured here, your verdict cites that measurement. Say which records your verdict "
    "rests on, and say what is missing when the records do not settle it. Write plainly and use no em dashes.")
KNOWLEDGE_MODES = ("candidates", "ranked", "none")
DEFINITION_FIELDS = (("description", "Description"), ("purpose", "Purpose"), ("approach", "Approach"), ("out_of_scope", "Out of scope"),
                     ("milestones", "Milestones"), ("measures_of_success", "Measures of success"),
                     ("parameters", "Parameters"), ("inputs", "Inputs"), ("outputs", "Outputs"), ("effects", "Effects"),
                     ("usage_notes", "Usage notes"))


@dataclass
class Section:
    """One part of the prompt: its tier (0 is read first), a title and its lines."""
    tier: int
    title: str
    lines: List[str] = field(default_factory=list)


@dataclass
class Network:
    """Everything one prompt reads, loaded once and shared by every prompt of a fan-out."""
    config: Any
    registry: Any
    intents: List[Any]
    history: Dict[str, Dict[str, List[Dict[str, str]]]]
    files: List[network_records.RecordFile]
    graded: Dict[Any, Any]
    today: Optional[datetime.date] = None
    stale: bool = True
    knowledge: Optional[List[Dict[str, Any]]] = None   # every knowledge item of the repository, read once (``knowledge.all_items``)

    @property
    def solutions(self) -> Dict[str, Dict[str, str]]:
        return {r.get("solution_id", ""): r for r in self.registry.every_solution()}


def load(config, extra: Sequence[str] = (), stale: bool = True, today: Optional[datetime.date] = None) -> Network:
    """The network of a repository: its records, results log, declared extra records and graded public evidence."""
    from esoi.optimization.leaderboard import results_log
    from esoi.optimization.leaderboard.cascade_report import graded_evidence
    try:
        graded = graded_evidence(config, today)
    except ValueError:
        graded = {}   # malformed evidence is rule S-territory, not a reason to withhold the prompt
    from esoi.understanding.solution_consideration import knowledge
    loaded = registry_module.load(config)
    return Network(config, loaded, intents_module.discover(config), results_log.all_results(config.results_path),
                   network_records.declared(config, extra), graded, today, stale, knowledge.all_items(config, loaded, today))


def clip(text: str, chars: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= chars else text[:chars].rsplit(" ", 1)[0] + "..."


def named(network: Network, sid: str) -> str:
    row = network.solutions.get(sid, {})
    return f"{row.get('name') or sid} ({sid})"


def real_ids(text: str) -> List[str]:
    return [i for i in ids(text or "") if i.lower() not in NONE_WORDS]


# The edges of the network -------------------------------------------------------------------------------------------------------

def parent_of(network: Network, sid: str) -> str:
    """The solution whose implementation is the intent that holds ``sid`` (the scope above it), or an empty string."""
    intent_id = network.solutions.get(sid, {}).get("intent_id", "")
    intent = next((i for i in network.intents if i.intent_id == intent_id), None)
    if intent is None:
        return ""
    return next((ref.split(":", 1)[0] for ref in ids(intent.row.get("implements", "")) if ref.split(":", 1)[0] != sid), "")


def child_intents(network: Network, sid: str) -> List[Any]:
    """The intents an implementation of ``sid`` is: the sub-intents whose solutions are its children."""
    return [i for i in network.intents if any(ref.split(":", 1)[0] == sid for ref in ids(i.row.get("implements", "")))]


def children_of(network: Network, sid: str) -> List[str]:
    held = {i.intent_id for i in child_intents(network, sid)}
    return [s for s, row in network.solutions.items() if row.get("intent_id") in held and s != sid]


def implementations_of(network: Network, sid: str) -> List[Dict[str, str]]:
    return [r for r in network.registry.implementations if r.get("solution_id") == sid]


def dependencies_of(network: Network, sid: str) -> Dict[str, str]:
    """``{solution id: how it is used}``: the solutions it delegates to and those its implementations use."""
    out = {d: "delegated to" for d in real_ids(network.solutions.get(sid, {}).get("delegates_to", ""))}
    for impl in implementations_of(network, sid):
        for used in real_ids(impl.get("uses_solution_ids", "")):
            out.setdefault(used, f"used by {impl.get('implementation_id', '')}")
    return {d: how for d, how in out.items() if d != sid and d in network.solutions}


def dependents_of(network: Network, sid: str) -> Dict[str, str]:
    """``{solution id: what relies on it}``: solutions that delegate to ``sid`` or whose implementations use it."""
    out: Dict[str, str] = {}
    for other, row in network.solutions.items():
        if other != sid and sid in real_ids(row.get("delegates_to", "")):
            out[other] = "delegates to it"
    for impl in network.registry.implementations:
        if sid in real_ids(impl.get("uses_solution_ids", "")) and impl.get("solution_id") not in ("", sid):
            out.setdefault(impl["solution_id"], f"its implementation {impl.get('implementation_id', '')} uses it")
    return out


# Sections ------------------------------------------------------------------------------------------------------------------------

def definition_section(network: Network, sid: str) -> Section:
    row = network.solutions[sid]
    lines = [f"Solution: {named(network, sid)}" + (f", in intent {row['intent_id']}" if row.get("intent_id") else "")]
    lines += [f"{label}: {clip(row[key], FIELD_CHARS)}" for key, label in DEFINITION_FIELDS if (row.get(key) or "").strip()]
    return Section(0, "Definition", lines)


def components_of(network: Network, sid: str) -> List[str]:
    """The results-log components the solution's metrics run, in metric order."""
    out: List[str] = []
    row = network.solutions[sid]
    for metric in (m for m in network.registry.metrics if m.get("metric_id") in ids(row.get("metric_ids", "")) or sid in ids(m.get("solution_ids", ""))):
        for component, _ in registry_module.harness_arms(network.config, metric.get("command", "")):
            if component not in out:
                out.append(component)
    return out


def result_line(network: Network, component: str, impl: str, rows: List[Dict[str, str]], selected: str) -> str:
    newest = rows[-1]
    passed, cases = newest.get("passed", "?"), newest.get("cases", "?")
    balanced = f", balanced {newest['balanced']}" if (newest.get("balanced") or "").strip() else ""
    mark = " [selected]" if impl == selected else ""
    note = ""
    if network.stale:
        from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reason
        try:
            why = stale_reason(network.config, component, newest, True)
        except Exception:   # a repository without git history still gets its results
            why = ""
        note = f" (stale: {clip(why, 160)})" if why else ""
    older = f"; {len(rows) - 1} earlier run(s)" if len(rows) > 1 else ""
    detail = f"; {clip(newest.get('details', ''), DETAIL_CHARS)}" if (newest.get("details") or "").strip() else ""
    return (f"{impl}{mark}: passed {passed} of {cases}{balanced} on {newest.get('date', '?')}, commit {newest.get('git_sha', '?')}, "
            f"cases {newest.get('cases_sha', '?')}{older}{detail}{note}")


def score_of(rows: List[Dict[str, str]]) -> float:
    newest = rows[-1]
    try:
        return float(newest.get("balanced") or "nan") if (newest.get("balanced") or "").strip() else int(newest.get("passed") or 0) / max(int(newest.get("cases") or 1), 1)
    except ValueError:
        return 0.0


def results_section(network: Network, sid: str, selected: str) -> Section:
    """Every recorded result of the solution's implementations, newest run per implementation, best first. Older code is said, never hidden."""
    lines: List[str] = []
    log = Path(network.config.results).as_posix()
    for component in components_of(network, sid):
        arms = network.history.get(component, {})
        if not arms:
            lines.append(f"{component}: no recorded result in {log}")
            continue
        lines.append(f"{component} ({log}), newest run per implementation, best first:")
        for impl, rows in sorted(arms.items(), key=lambda kv: (-score_of(kv[1]), kv[0])):
            lines.append("  " + result_line(network, component, impl, rows, selected))
    if not lines:
        lines.append("No metric of this solution names a command that records results, so nothing is measured yet.")
    return Section(0, "Recorded results", lines)


def selection_section(network: Network, sid: str) -> Section:
    """The selected implementation, the layer of the selection cascade that runs it, and what the metric's cascade chooses."""
    from esoi.runtime.implementation_selection.select import default_name
    row = network.solutions[sid]
    selected = default_name(row, network.registry.implementations)
    lines = [f"Selected in the records: {selected or 'none'}"]
    lines += runtime_layer_lines(network, sid)
    lines += metric_cascade_lines(network, sid, selected)
    return Section(0, "Selection", lines)


def runtime_layer_lines(network: Network, sid: str) -> List[str]:
    import os
    from esoi.runtime.implementation_selection import selection_cascade, selection_registry
    environ = dict(os.environ, **{selection_registry.ROOT_ENV: str(network.config.root)})
    try:
        picked = selection_cascade.choose(sid, None, environ)
    except Exception:   # nothing selected or nothing declared: the records line above says so
        return []
    return [f"Runs now: {picked.name}, chosen by the {picked.layer} layer ({picked.source})"]


def metric_cascade_lines(network: Network, sid: str, selected: str) -> List[str]:
    """Each metric's stages and the implementation its cascade chooses, as ``esoi cascade`` decides it."""
    from esoi.optimization.leaderboard.cascade_report import metric_arm
    from esoi.optimization.leaderboard.cascade_stages import load_stages
    from esoi.optimization.leaderboard.stage_standings import decide, standings
    lines: List[str] = []
    for metric in (m for m in network.registry.metrics if sid in ids(m.get("solution_ids", ""))):
        stages, errors = load_stages(network.config, metric)
        if not stages:
            continue
        lines.append(f"Cascade of {metric.get('metric_id', '')}: {' > '.join(s.name for s in stages)}")
        component, _ = metric_arm(network.config, network.registry, metric, [sid])
        if not component or component not in network.history:
            lines.append("  no results yet at any stage")
            continue
        stale = cascade_staleness(network, component)
        decision = decide(stages, standings(stages, network.history[component], network.today, stale, network.config.evaluation),
                          network.config.evaluation)
        if decision.winner:
            lines.append(f"  chosen by the cascade: {decision.winner} at stage {stages[decision.stage].name}"
                         + (f"; the records select {selected}" if selected and selected != decision.winner else ""))
        lines += [f"  note: {clip(n, 240)}" for n in decision.notes]
    return lines


def cascade_staleness(network: Network, component: str) -> Callable[[Dict[str, str]], str]:
    if not network.stale:
        return lambda row: ""
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures.interface import stale_reason
    return lambda row: stale_reason(network.config, component, row, True)


def metric_section(network: Network, sid: str) -> Section:
    lines: List[str] = []
    for metric in (m for m in network.registry.metrics if sid in ids(m.get("solution_ids", ""))):
        lines.append(f"Metric {metric.get('metric_id', '')}: {metric.get('name', '')}")
        for key, label in (("purpose", "Purpose"), ("record", "Record"), ("disadvantages", "Cannot see"),
                           ("cascading_conditionals", "Cascading conditionals")):
            if (metric.get(key) or "").strip():
                lines.append(f"  {label}: {clip(metric[key], FIELD_CHARS)}")
    return Section(1, "Metric", lines)


def problems_ideals_section(network: Network, sid: str) -> Section:
    row = network.solutions[sid]
    lines: List[str] = []
    problems = {p.get("problem_id", ""): p for p in network.registry.problems}
    ideals = {i.get("ideal_id", ""): i for i in network.registry.ideals}
    for pid in ids(row.get("problem_ids", "")):
        p = problems.get(pid, {})
        lines.append(f"Problem {pid}: {clip(p.get('problem', ''), 500)} Why it matters: {clip(p.get('why_it_matters', ''), 300)}")
    for iid in ids(row.get("ideal_ids", "")):
        i = ideals.get(iid, {})
        lines.append(f"Ideal {iid} ({i.get('name', '')}): {clip(i.get('principle', ''), 300)} Reached when: {clip(i.get('hints_of_measurement', ''), 300)}")
    return Section(1, "Problems and ideals", lines)


def implementations_section(network: Network, sid: str) -> Section:
    lines = []
    for impl in implementations_of(network, sid):
        text = f"{impl.get('implementation_id', '')} ({impl.get('name', '')}): {clip(impl.get('description', ''), 400)}"
        for key, label in (("advantages", "Advantages"), ("disadvantages", "Disadvantages")):
            if (impl.get(key) or "").strip():
                text += f" {label}: {clip(impl[key], 250)}"
        lines.append(text)
    return Section(1, "Implementations", lines)


def queued_section(network: Network, sid: str) -> Section:
    """Findings, candidates and other declared records about this solution."""
    found = network_records.about(network.config, network.registry, sid, network.files)
    return Section(1, "Findings and candidates queued against it",
                   [f"{f['kind']} {f['id']} ({f['file']}; {f['via']}): {clip(f['text'], 1200)}" for f in found])


def evidence_section(network: Network, sid: str) -> Section:
    """Public evidence others measured for the solution's implementations (never a result of ours), and records kept beside it."""
    from esoi.optimization.when_metrics_are_run.public_evidence import evidence_grading, evidence_records
    lines: List[str] = []
    if network.graded:
        exact = evidence_records.implementation_candidates(network.config, network.registry, sid)
        candidates = {key[0] for key in network.graded}
        for impl in implementations_of(network, sid):
            short = impl.get("implementation_id", "").split(":", 1)[-1]
            keys = set(exact.get(short, "").split(",")) | {c for c in candidates
                                                           if network_records.candidate_words(c) and network_records.candidate_words(c) <= network_records.implementation_words(impl)}
            for estimate in evidence_grading.lines_for_implementation(network.graded, ",".join(sorted(k for k in keys if k))):
                lines.append(f"{short} (as {estimate.candidate}, others' measurement): {estimate.line()}")
    for path in beside_files(network, sid):
        for row in read_csv(path):
            lines.append(f"{path.name}: {clip(network_records.row_text(row), 500)}")
    return Section(1, "Public evidence and priors", lines)


def beside_files(network: Network, sid: str) -> List[Path]:
    """CSV files kept in the solution's own records folder that are not record files (priors, local registries)."""
    skip = {intents_module.INTENT_FILE, *intents_module.RECORD_FILES, "components.csv", "waivers.csv", "results.csv", "per_case.csv", "runs.csv",
            "evidence.csv", "esoi_template.csv"}
    for _, folder in intents_module.folders(network.config):
        if any(r.get("solution_id") == sid for r in read_csv(folder / "solutions.csv")):
            if folder == network.config.structure or len([r for r in read_csv(folder / "solutions.csv")]) > 1:
                return []   # a shared folder: its other files are not this solution's own
            return sorted(p for p in folder.glob("*.csv") if p.name not in skip)
    return []


def brief(network: Network, sid: str, depth: str) -> str:
    """A connected solution at the depth its edge earns: ``brief`` (purpose), ``interface`` (purpose, interface, selected)."""
    from esoi.runtime.implementation_selection.select import default_name
    row = network.solutions.get(sid, {})
    text = f"{named(network, sid)}: {clip(row.get('purpose', ''), 300)}"
    if depth == "interface":
        for key, label in (("inputs", "Inputs"), ("outputs", "Outputs")):
            if (row.get(key) or "").strip():
                text += f" {label}: {clip(row[key], 250)}"
        chosen = default_name(row, network.registry.implementations)
        text += f" Selected: {chosen or 'none'}."
    else:
        text += f" Approach: {clip(row.get('approach', ''), 250)}"
    return text


def connected_sections(network: Network, sid: str) -> List[Section]:
    parent = parent_of(network, sid)
    children = children_of(network, sid)
    deps = {d: how for d, how in dependencies_of(network, sid).items() if d not in children and d != parent}
    dependents = {d: how for d, how in dependents_of(network, sid).items() if d not in children and d != parent}
    own_outputs = clip(network.solutions[sid].get("outputs", ""), 200)
    return [
        Section(2, "Parent (the scope above)", [brief(network, parent, "brief")] if parent else []),
        Section(2, "Children", [brief(network, c, "interface") for c in children]),
        Section(2, "Dependencies", [f"{brief(network, d, 'interface')} ({how})" for d, how in deps.items()]),
        Section(3, "Dependents (what relies on this solution)",
                [f"{named(network, d)} {how}: {clip(network.solutions[d].get('purpose', ''), 200)}"
                 + (f" It relies on: {own_outputs}" if own_outputs else "") for d, how in dependents.items()]),
    ]


def combination_section(network: Network, sid: str) -> Section:
    """For a solution with children: how they combine, from the child intent's own coherence and diagram."""
    lines: List[str] = []
    for intent in child_intents(network, sid):
        row = intent.row
        lines.append(f"Intent {intent.intent_id} ({row.get('name', '')}), implementing {row.get('implements', '')}. Vision: {clip(row.get('vision_statement', ''), 300)}")
        for key, label in (("solution_coherence", "Solution coherence"), ("solution_diagram", "Solution diagram"), ("opportunities", "Opportunities")):
            if (row.get(key) or "").strip():
                lines.append(f"  {label}: {clip(row[key], 2500)}")
        diagram = intent.folder / "diagram.md"
        if not (row.get("solution_diagram") or "").strip() and diagram.is_file():
            lines.append(f"  Solution diagram ({diagram.name}): {clip(diagram.read_text(encoding='utf-8'), 2000)}")
    if lines:
        lines.insert(0, "Judge this level as its own scope: does the structure of the combination of its children fulfil its purpose, "
                        "and which child, edge or missing child limits it?")
    return Section(1, "How its children combine", lines)


def knowledge_section(network: Network, sid: str, mode: str) -> Section:
    """``ranked``: every item in the no-retriever order, the inactive ones after and labelled. ``candidates``: one line saying how many
    items wait for the caller's retrieval. ``none``: nothing."""
    from esoi.understanding.solution_consideration import knowledge
    active, inactive = knowledge.items(network, sid)
    if mode == "ranked":
        return Section(1, "Knowledge", [knowledge.line(i) for i in active + inactive])
    if mode == "candidates" and (active or inactive):
        return Section(0, "Knowledge", [f"{len(active)} knowledge item(s) are offered beside this prompt for the situation to choose from"
                                        + (f" ({len(inactive)} superseded, contradicted or expired)" if inactive else "") + "."])
    return Section(1, "Knowledge", [])


def sections_of(network: Network, sid: str, task: str = "", knowledge: str = "candidates") -> List[Section]:
    """Every section of one solution's prompt, in reading order within each tier."""
    from esoi.runtime.implementation_selection.select import default_name
    if sid not in network.solutions:
        raise KeyError(sid)
    selected = default_name(network.solutions[sid], network.registry.implementations)
    head = Section(0, "How to read this", [INSTRUCTIONS] + ([f"The matter to consider: {task}"] if task else []))
    return [head, definition_section(network, sid), results_section(network, sid, selected), selection_section(network, sid),
            queued_section(network, sid), combination_section(network, sid), metric_section(network, sid),
            problems_ideals_section(network, sid), knowledge_section(network, sid, knowledge), evidence_section(network, sid),
            implementations_section(network, sid), *connected_sections(network, sid)]


def omission_note(count: int) -> str:
    return f"({count} more line(s) omitted for size: read them with `esoi spec show ID --tier 2`)"


def fitted(section: Section, room: int) -> List[str]:
    """The lines of a section that fit ``room`` characters, with a note of what was cut when something was."""
    taken: List[str] = []
    for n, line in enumerate(section.lines):
        rest = len(section.lines) - n - 1
        reserve = len(omission_note(rest)) + 1 if rest else 0
        if len(line) + 1 + reserve > room:
            if taken and room >= len(omission_note(len(section.lines) - n)) + 1:
                taken.append(omission_note(len(section.lines) - n))
            return taken
        taken.append(line)
        room -= len(line) + 1
    return taken


def render(sections: List[Section], budget: int) -> Dict[str, Any]:
    """The prompt text that fits ``budget`` characters, sections taken in tier order, and what was cut."""
    kept: List[tuple] = []
    used, omitted = 0, []
    for n in sorted(range(len(sections)), key=lambda i: (sections[i].tier, i)):
        section = sections[n]
        if not section.lines:
            continue
        head = f"## {section.title}"
        taken = fitted(section, budget - used - len(head) - (2 if kept else 0))
        shown = len([t for t in taken if not t.startswith("(") or not t.endswith("--tier 2`)")])
        if shown < len(section.lines):
            omitted.append({"section": section.title, "tier": section.tier, "lines_omitted": len(section.lines) - shown})
        if taken:
            block = "\n".join([head, *taken])
            kept.append((n, section, block))
            used += len(block) + (2 if len(kept) > 1 else 0)
    kept.sort(key=lambda item: (item[1].tier, item[0]))
    text = "\n\n".join(block for _, _, block in kept)
    return {"text": text, "chars": len(text), "sections": [{"title": s.title, "tier": s.tier, "lines": len(s.lines)} for _, s, _ in kept],
            "omitted": omitted}


def prompt(network: Network, sid: str, task: str = "", budget: int = DEFAULT_BUDGET, role: str = "solution",
           knowledge: str = "candidates") -> Dict[str, Any]:
    """One solution's prompt as plain data: ``{solution_id, name, role, parent, children, text, chars, sections, omitted, digest}``, and
    with ``knowledge`` ``candidates`` or ``ranked`` also ``knowledge`` (active items, best first) and ``knowledge_inactive``."""
    from esoi.understanding.solution_consideration import knowledge as knowledge_module
    if knowledge not in KNOWLEDGE_MODES:
        raise ValueError(f"knowledge must be one of {', '.join(KNOWLEDGE_MODES)}, not {knowledge!r}")
    out = render(sections_of(network, sid, task, knowledge), budget)
    made = {"solution_id": sid, "name": network.solutions[sid].get("name", ""), "role": role, "parent": parent_of(network, sid),
            "children": children_of(network, sid), **out, "digest": hashlib.sha256(out["text"].encode("utf-8")).hexdigest()[:12]}
    if knowledge != "none":
        made["knowledge"], made["knowledge_inactive"] = knowledge_module.items(network, sid)
    return made


def budget_of(config, asked: Optional[int] = None) -> int:
    """The size budget: the one asked for, else ``[consider] budget``, else the default."""
    return int(asked or (getattr(config, "consider", {}) or {}).get("budget") or DEFAULT_BUDGET)

