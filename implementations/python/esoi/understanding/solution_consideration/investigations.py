"""Investigation records: one piece of information gathering done to answer a question, kept as data so it can be checked,
applied and revisited (standard: ``docs/reference/knowledge-search-standard.md``).

An investigation finds new evidence (a trial, an observation, an interview: primary) or gathers existing evidence (a review of what is
already known: secondary). One record shape holds both, with a ``kind`` naming the activity, so there is one standard and no parallel one.
An experiment is a research direction (``experiments.py``, ``experiments.csv``); an investigation happens inside one or on its own,
and each row may name its experiment in ``experiment_id``. The role is loose on purpose: a record is a question, a method fixed beforehand, what was observed, what it means, what it changed and when to revisit.
Everything else is optional unless the kind asks for it, and a qualitative investigation is never forced to carry a number.

Files named before the rename (``research.csv``, ``research_items.csv``, the column ``research_id``) are still read when the new
file or column is absent (``renamed``); everything is written under the new names.

Its home is an intent (``intent_id``), not a solution: a question may bear on several solutions, problems, ideals, metrics or
alternatives (``links``, many to many and optional), or on none yet when it is about how to think about the intent itself.

Everything here is advice: a malformed or incomplete record is listed, never failed. Standard library only; no model call.

``investigations.csv`` columns: ``investigation_id``, ``kind`` (review, trial, observation, interview, other), ``intent_id``,
``experiment_id`` (the row of ``experiments.csv`` the activity belongs to; optional), ``links``
(``kind:id`` entries separated by ``;``, kind one of ``LINK_KINDS``; empty when the question is about the intent itself), ``question``,
``decision`` (what the answer informs), ``size`` (quick, standard, full), ``protocol_date`` (the method is fixed on this date, before
the work), ``method`` (how it is done, by whom), ``criteria``, ``sources``, ``queries`` (``source | query | date | hits``) and ``found``,
``screened_out`` (``count reason``), ``kept`` (a review's screening), ``observe`` (a trial or observation: what will be observed and how),
``change_my_mind`` (what would count as changing one's mind; for a comparison of alternatives, the metric, stage, expected and
rejecting values), ``stop`` (end condition: date, sample or cost), ``done_on`` (when the activity was done), ``synthesis_known``, ``synthesis_contested``,
``synthesis_unknown`` (what it means), ``limitations``, ``decisions`` (a review's ``candidate: verb: reason`` entries, verb one of
``DECISIONS``), ``refresh_on`` (when to revisit), ``status`` (open, superseded). Lists are separated by ``;``.

``investigation_items.csv`` columns: ``investigation_id``, ``item_id``, ``claim`` (a finding or observation), ``source`` (where it is recorded),
``source_date``, ``independent`` (yes, no, unknown), ``verified`` (opened, cross-checked, snippet, not-opened, observed), ``licence``
(for code; ``n/a`` otherwise), ``grade`` (A to D, the grading of ``esoi evidence``; optional outside a review), ``knowledge_id``,
``applied`` (what it changed, as ``kind:record id`` entries, kind one of ``APPLIED_KINDS``, or ``not-applied: reason``). Knowledge it
produced carries ``investigation_id``, so a record created or changed because of an investigation points back to it; the page of a solution
lists them (``readme_lines``).
"""
from __future__ import annotations

import datetime
import re
from typing import Dict, List, Mapping, Optional, Tuple

from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.tables import read_csv

FILE = "investigations.csv"
ITEMS_FILE = "investigation_items.csv"
LEGACY_FILE = "research.csv"
LEGACY_ITEMS_FILE = "research_items.csv"
LEGACY_ID = "research_id"
COLUMNS = ["investigation_id", "kind", "intent_id", "experiment_id", "links", "question", "decision", "size", "protocol_date", "method", "criteria", "sources",
           "queries", "found", "screened_out", "kept", "observe", "change_my_mind", "stop", "done_on", "synthesis_known",
           "synthesis_contested", "synthesis_unknown", "limitations", "decisions", "refresh_on", "status"]
ITEM_COLUMNS = ["investigation_id", "item_id", "claim", "source", "source_date", "independent", "verified", "licence", "grade", "knowledge_id",
                "applied"]
KINDS = ("review", "trial", "observation", "interview", "other")
SIZES = ("quick", "standard", "full")
DECISIONS = ("adopt", "adapt", "build-on", "reject", "defer", "no-candidate")
VERIFIED = ("opened", "cross-checked", "snippet", "not-opened", "observed")
LINK_KINDS = ("solution", "problem", "ideal", "metric", "implementation", "intent", "knowledge")
APPLIED_KINDS = ("document", "knowledge", "implementation", "metric", "stage", "selection", "waiver", "decision", "experiment",
                 "milestone", "problem", "ideal", "solution", "intent")
GRACE_DAYS = {"quick": 7, "standard": 14, "full": 30}   # findings are applied, or marked not applied, within this many days
STANDARD_DATE = datetime.date(2026, 11, 10)
ALL_KINDS_NEED = ("kind", "intent_id", "question", "size", "protocol_date", "method", "done_on", "limitations", "refresh_on")
KIND_NEEDS = {"review": ("decision", "criteria", "sources", "queries", "found", "screened_out", "kept", "decisions"),
              "trial": ("observe", "change_my_mind"), "observation": ("observe",)}
SYNTHESIS = ("synthesis_known", "synthesis_contested", "synthesis_unknown")
SEP = ";"


def as_date(text: str) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat((text or "").strip()[:10])
    except ValueError:
        return None


def parts(cell: str) -> List[str]:
    return [p.strip() for p in (cell or "").split(SEP) if p.strip()]


def renamed(row: Mapping[str, str]) -> Dict[str, str]:
    """The row with a ``research_id`` cell read as ``investigation_id`` (the one mapping for records written before the rename)."""
    out = dict(row)
    if LEGACY_ID in out and "investigation_id" not in out:
        out["investigation_id"] = out.pop(LEGACY_ID)
    return out


def read_records(folder, name: str, legacy: str) -> List[Dict[str, str]]:
    """The rows of ``name`` in a records folder, or of ``legacy`` when only the file named before the rename exists."""
    return [renamed(r) for r in read_csv(folder / (name if (folder / name).exists() else legacy))]


def rows(config) -> List[Dict[str, str]]:
    """Every row of every ``investigations.csv`` in the records folders."""
    return [r for _, folder in intents.folders(config) for r in read_records(folder, FILE, LEGACY_FILE)]


def item_rows(config) -> List[Dict[str, str]]:
    """Every row of every ``investigation_items.csv`` in the records folders."""
    return [r for _, folder in intents.folders(config) for r in read_records(folder, ITEMS_FILE, LEGACY_ITEMS_FILE)]


def linked(row: Mapping[str, str], kind: str = "") -> List[str]:
    """The ids a record links to, all or of one link kind."""
    out = []
    for entry in parts(row.get("links", "")):
        link_kind, _, rid = entry.partition(":")
        if rid.strip() and (not kind or link_kind.strip() == kind):
            out.append(rid.strip())
    return out


def counted(entries: List[str]) -> Optional[int]:
    """The sum of the leading counts of ``count reason`` entries, or None when one has no count."""
    total = 0
    for entry in entries:
        found = re.match(r"(\d+)\s+\S", entry)
        if not found:
            return None
        total += int(found.group(1))
    return total


def to_int(text: str) -> Optional[int]:
    try:
        return int((text or "").strip())
    except ValueError:
        return None


def row_problems(row: Mapping[str, str], items: List[Mapping[str, str]]) -> List[str]:
    """What one investigation record lacks against the standard for its kind and size."""
    out: List[str] = []
    kind = (row.get("kind") or "").strip().lower()
    size = (row.get("size") or "").strip().lower()
    if kind not in KINDS:
        out.append(f"kind {row.get('kind')!r} is not one of {', '.join(KINDS)}")
    if size not in SIZES:
        out.append(f"size {row.get('size')!r} is not one of {', '.join(SIZES)}")
    out += [f"has no {c}" for c in ALL_KINDS_NEED + KIND_NEEDS.get(kind, ()) if not (row.get(c) or "").strip()]
    if size in ("standard", "full"):
        out += [f"has no {c} (a {size} investigation says what is known, contested and unknown)" for c in SYNTHESIS
                if not (row.get(c) or "").strip()]
    for entry in parts(row.get("links", "")):
        if entry.partition(":")[0].strip() not in LINK_KINDS or not entry.partition(":")[2].strip():
            out.append(f"link {entry!r} reads `kind:id`, kind one of {', '.join(LINK_KINDS)}")
    protocol, done = as_date(row.get("protocol_date", "")), as_date(row.get("done_on", ""))
    if protocol and done and protocol > done:
        out.append("protocol_date is after done_on: the method is fixed before the work")
    if kind == "review":
        found, kept = to_int(row.get("found", "")), to_int(row.get("kept", ""))
        out_count = counted(parts(row.get("screened_out", "")))
        if (row.get("screened_out") or "").strip() and out_count is None:
            out.append("screened_out entries read `count reason`")
        if None not in (found, kept, out_count) and found - out_count != kept:
            out.append(f"found {found} less screened out {out_count} is not kept {kept}")
        for entry in parts(row.get("decisions", "")):
            pieces = [p.strip() for p in entry.split(":", 2)]
            if len(pieces) < 3 or pieces[1] not in DECISIONS or not pieces[2]:
                out.append(f"decision {entry!r} reads `candidate: {'|'.join(DECISIONS)}: reason`")
        if kept and len(items) != kept:
            out.append(f"kept {kept} but investigation_items.csv holds {len(items)} item(s) for it")
    for item in items:
        who = item.get("item_id") or "(no id)"
        grade = (item.get("grade") or "").strip()
        if grade not in ("A", "B", "C", "D") and (kind == "review" or grade):
            out.append(f"item {who} has no grade A to D")
        if (item.get("independent") or "").strip() not in ("yes", "no", "unknown") and (kind == "review" or item.get("independent")):
            out.append(f"item {who} independent is not yes, no or unknown")
        if (item.get("verified") or "").strip() not in VERIFIED and (kind == "review" or item.get("verified")):
            out.append(f"item {who} verified is not one of {', '.join(VERIFIED)}")
        if not (item.get("claim") or "").strip() or not (item.get("source") or "").strip() or not (item.get("source_date") or "").strip():
            out.append(f"item {who} needs a claim, a source and its date")
    return out


def experiment_problems(config) -> List[Tuple[str, str]]:
    """Activities that name an experiment which has no row in ``experiments.csv``."""
    from esoi.understanding.solution_consideration import experiments
    frames = {(r.get("experiment_id") or "").strip() for r in experiments.rows(config)}
    return [((r.get("investigation_id") or "").strip(), f"names experiment {r.get('experiment_id')}, which has no row in experiments.csv")
            for r in rows(config) if (r.get("experiment_id") or "").strip() and (r.get("experiment_id") or "").strip() not in frames]


def applied_problems(row: Mapping[str, str], items: List[Mapping[str, str]], on: datetime.date) -> List[str]:
    """Items past their size's grace period with no ``applied`` entry, and entries that are neither ``kind:id`` nor ``not-applied: reason``."""
    out: List[str] = []
    size = (row.get("size") or "").strip().lower()
    done = as_date(row.get("done_on", ""))
    late = bool(done) and (on - done).days > GRACE_DAYS.get(size, 14)
    for item in items:
        who, text = item.get("item_id") or "(no id)", (item.get("applied") or "").strip()
        if not text:
            if late:
                out.append(f"item {who} is neither applied nor marked not-applied after {GRACE_DAYS.get(size, 14)} days")
            continue
        if text.lower().startswith("not-applied"):
            if not text.partition(":")[2].strip():
                out.append(f"item {who} is marked not-applied with no reason")
            continue
        for entry in parts(text):
            kind, _, rid = entry.partition(":")
            if kind.strip() not in APPLIED_KINDS or not rid.strip():
                out.append(f"item {who} applied entry {entry!r} reads `kind:record id`, kind one of {', '.join(APPLIED_KINDS)}")
    return out


def readme_lines(config, solution_ids, level: str = "##") -> List[str]:
    """The lines a page shows under its knowledge: each investigation linked to one of ``solution_ids`` and what each item changed."""
    wanted = set(solution_ids)
    items = item_rows(config)
    lines: List[str] = []
    for row in rows(config):
        if not wanted & set(linked(row, "solution")):
            continue
        rid = (row.get("investigation_id") or "").strip()
        applied = [f"{(i.get('item_id') or '').strip()}: {(i.get('applied') or '').strip() or 'not yet applied'}"
                   for i in items if i.get("investigation_id") == rid]
        lines.append(f"- `{rid}` ({row.get('kind', '')}, {row.get('size', '')}, done {row.get('done_on', '')}, revisit {row.get('refresh_on', '')}): "
                     f"{' '.join((row.get('question') or '').split())} Applied: " + ("; ".join(applied) if applied else "no item kept") + ".")
    return [f"{level} Investigations behind the knowledge", ""] + lines + [""] if lines else []


def due(config, on: Optional[datetime.date] = None) -> List[Dict[str, str]]:
    """Open investigations whose ``refresh_on`` is today or past."""
    on = on or datetime.date.today()
    return [r for r in rows(config) if (r.get("status") or "open").strip() == "open" and (d := as_date(r.get("refresh_on", ""))) and d <= on]


def uninvestigated_knowledge(config) -> List[str]:
    """Ids of knowledge rows recorded on or after the standard's date that cite an address but name no investigation."""
    from esoi.understanding.solution_consideration import knowledge
    out = []
    for row in knowledge.rows(config):
        recorded = as_date(row.get("recorded", ""))
        kind, _ = knowledge.source_kind(row.get("source", ""))
        if recorded and recorded >= STANDARD_DATE and kind == "evidence" and not (row.get("investigation_id") or "").strip():
            out.append((row.get("knowledge_id") or "(no id)").strip())
    return out


def advice(config, on: Optional[datetime.date] = None) -> List[Tuple[str, str]]:
    """``(key, advice)`` for every record gap, an investigation past its revisit date, and knowledge citing sources with no investigation."""
    on = on or datetime.date.today()
    by_research: Dict[str, List[Mapping[str, str]]] = {}
    for item in item_rows(config):
        by_research.setdefault(item.get("investigation_id", ""), []).append(item)
    out: List[Tuple[str, str]] = []
    for row in rows(config):
        key = (row.get("investigation_id") or "").strip() or "(no id)"
        mine = by_research.get(key, [])
        out += [(key, p) for p in row_problems(row, mine) + applied_problems(row, mine, on)]
    out += experiment_problems(config)
    out += [((r.get("investigation_id") or "").strip(), f"revisit was due {r.get('refresh_on')}; redo it or set its status to superseded")
            for r in due(config, on)]
    known = {(r.get("investigation_id") or "").strip() for r in rows(config)}
    from esoi.understanding.solution_consideration import knowledge
    for row in knowledge.rows(config):
        rid = (row.get("investigation_id") or "").strip()
        if rid and rid not in known:
            out.append(((row.get("knowledge_id") or "").strip(), f"names investigation {rid}, which has no row in investigations.csv"))
    out += [(k, "cites sources and names no investigation_id; record the investigation that found it (docs/reference/knowledge-search-standard.md)")
            for k in uninvestigated_knowledge(config)]
    return out


def notes(config, on: Optional[datetime.date] = None) -> List[str]:
    """The advice as lines for ``esoi check``'s notes; never a failure."""
    return [f"note: investigation {key}: {text}" for key, text in advice(config, on)]
