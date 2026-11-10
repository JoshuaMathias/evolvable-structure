"""Experiment records: the scope of an intent's current focused exploration (docs/reference/experiments-in-esoi.md).

An experiment directs focused attention for a period and fixes certain things for that period, like a trial period before
reevaluating: what is held fixed is not reopened until the reevaluation date, and is reopened then. It lives at the intent, in
``experiments.csv`` beside the intent's other records (an intent with no such file is valid), and may bear on many solutions,
problems, ideals, metrics or milestones, or on none. The research done inside it (``research.csv``, reviews, observations, trials
under the research standard) names it in ``experiment_id``; the list of those rows is ``research_ids``.

Everything here is advice: an incomplete or odd record is listed, never failed. Standard library only; no model call.

Columns: ``experiment_id``, ``intent_id``, ``name``, ``focus`` (the question or way of thinking explored), ``directs`` (whose attention it
directs, a person or role; empty when it is one's own), ``status`` (planned, running, reevaluating, ended), ``starts_on``,
``reevaluate_on`` (date), ``reevaluate_when`` (a condition, instead of or beside the date), ``held_fixed`` (the choices not re-decided
for the period, ``;`` separated, each ``subject = choice`` or free text), ``inside``, ``left_out`` (for now), ``links`` (``kind:id``
entries, kind one of ``LINK_KINDS``), ``research_ids``, ``learned``, ``changed`` (``kind:record id`` entries: knowledge, structure,
priorities, milestones), ``decision`` (continue, change, end), ``next_experiment_id``.
"""
from __future__ import annotations

import datetime
from typing import Dict, List, Mapping, Optional, Tuple

from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.tables import read_csv

FILE = "experiments.csv"
COLUMNS = ["experiment_id", "intent_id", "name", "focus", "directs", "priority", "status", "starts_on", "reevaluate_on", "reevaluate_when", "held_fixed",
           "inside", "left_out", "links", "research_ids", "learned", "changed", "decision", "next_experiment_id"]
STATUSES = ("planned", "running", "reevaluating", "ended")
DECISIONS = ("continue", "change", "end")
LINK_KINDS = ("solution", "problem", "ideal", "metric", "milestone", "implementation", "knowledge")
CHANGED_KINDS = ("knowledge", "problem", "ideal", "solution", "implementation", "metric", "milestone", "priority", "stage", "selection",
                 "waiver", "decision", "document")
NEEDS = ("intent_id", "name", "focus", "status", "starts_on", "inside")
SEP = ";"


def as_date(text: str) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat((text or "").strip()[:10])
    except ValueError:
        return None


def parts(cell: str) -> List[str]:
    return [p.strip() for p in (cell or "").split(SEP) if p.strip()]


def rows(config) -> List[Dict[str, str]]:
    """Every row of every ``experiments.csv`` in the records folders."""
    return [r for _, folder in intents.folders(config) for r in read_csv(folder / FILE)]


def running(config, intent_id: str = "", directs: str = "") -> List[Dict[str, str]]:
    """The experiments that are running (or being reevaluated), optionally of one intent or one person: where attention goes now."""
    found = [r for r in rows(config) if (r.get("status") or "").strip() in ("running", "reevaluating")
             and (not intent_id or r.get("intent_id") == intent_id) and (not directs or (r.get("directs") or "").strip() == directs)]
    return sorted(found, key=lambda r: (to_int(r.get("priority", "")) or 10 ** 6, r.get("experiment_id", "")))


def due(config, on: Optional[datetime.date] = None) -> List[Dict[str, str]]:
    """Running experiments whose reevaluation date is today or past: what an AI prompts a reevaluation of."""
    on = on or datetime.date.today()
    return [r for r in rows(config) if (r.get("status") or "").strip() == "running" and (d := as_date(r.get("reevaluate_on", ""))) and d <= on]


def commitments(row: Mapping[str, str]) -> Dict[str, str]:
    """``{subject: choice}`` of the held-fixed entries written ``subject = choice``."""
    out = {}
    for entry in parts(row.get("held_fixed", "")):
        subject, eq, choice = entry.partition("=")
        if eq and subject.strip() and choice.strip():
            out[subject.strip().lower()] = choice.strip().lower()
    return out


def to_int(text: str) -> Optional[int]:
    try:
        return int((text or "").strip())
    except ValueError:
        return None


def row_problems(row: Mapping[str, str]) -> List[str]:
    out = [f"has no {c}" for c in NEEDS if not (row.get(c) or "").strip()]
    status = (row.get("status") or "").strip()
    if status and status not in STATUSES:
        out.append(f"status {status!r} is not one of {', '.join(STATUSES)}")
    if status in ("running", "planned") and not ((row.get("reevaluate_on") or "").strip() or (row.get("reevaluate_when") or "").strip()):
        out.append("names no reevaluate_on or reevaluate_when: a trial period ends in a reevaluation")
    if status == "running" and not (row.get("held_fixed") or "").strip():
        out.append("holds nothing fixed (held_fixed); say what is not re-decided for the period, or that nothing is")
    if status in ("reevaluating", "ended"):
        out += [f"is {status} but has no {c}" for c in ("learned", "decision") if not (row.get(c) or "").strip()]
    if (row.get("decision") or "").strip() and (row.get("decision") or "").strip() not in DECISIONS:
        out.append(f"decision {row.get('decision')!r} is not one of {', '.join(DECISIONS)}")
    for entry in parts(row.get("links", "")):
        if entry.partition(":")[0].strip() not in LINK_KINDS or not entry.partition(":")[2].strip():
            out.append(f"link {entry!r} reads `kind:id`, kind one of {', '.join(LINK_KINDS)}")
    for entry in parts(row.get("changed", "")):
        if entry.partition(":")[0].strip() not in CHANGED_KINDS or not entry.partition(":")[2].strip():
            out.append(f"changed entry {entry!r} reads `kind:record id`, kind one of {', '.join(CHANGED_KINDS)}")
    if (row.get("priority") or "").strip() and (to_int(row.get("priority", "")) or 0) < 1:
        out.append("priority is a whole number from 1 (first)")
    start, end = as_date(row.get("starts_on", "")), as_date(row.get("reevaluate_on", ""))
    if start and end and end < start:
        out.append("reevaluate_on is before starts_on")
    return out


def advice(config, on: Optional[datetime.date] = None) -> List[Tuple[str, str]]:
    """``(key, advice)`` for record gaps, a reevaluation due, research that does not exist, and running experiments of one person that
    fix different choices for the same subject."""
    from esoi.understanding.solution_consideration import research
    on = on or datetime.date.today()
    every = rows(config)
    known_research = {(r.get("research_id") or "").strip() for r in research.rows(config)}
    out: List[Tuple[str, str]] = []
    for row in every:
        key = (row.get("experiment_id") or "").strip() or "(no id)"
        out += [(key, p) for p in row_problems(row)]
        out += [(key, f"names research {rid}, which has no row in research.csv") for rid in parts(row.get("research_ids", ""))
                if rid not in known_research]
    out += [((r.get("experiment_id") or "").strip(), f"reevaluation was due {r.get('reevaluate_on')}; prompt the reevaluation (what was learned, "
            "what it changed, continue, change or end)") for r in due(config, on)]
    for intent_id in sorted({(r.get("intent_id") or "").strip() for r in every}):
        ranks = [(to_int(r.get("priority", "")), (r.get("experiment_id") or "").strip()) for r in running(config, intent_id)]
        for rank in sorted({n for n, _ in ranks if n}):
            same = [i for n, i in ranks if n == rank]
            if len(same) > 1:
                out.append((same[0], f"shares priority {rank} with running experiment(s) {', '.join(same[1:])}: the order is what directs attention first"))
    live = [r for r in every if (r.get("status") or "").strip() in ("running", "reevaluating") and (r.get("directs") or "").strip()]
    for n, first in enumerate(live):
        for second in live[n + 1:]:
            if (first.get("directs") or "").strip() != (second.get("directs") or "").strip():
                continue
            a, b = commitments(first), commitments(second)
            for subject in sorted(set(a) & set(b)):
                if a[subject] != b[subject]:
                    out.append(((first.get("experiment_id") or "").strip(),
                                f"fixes {subject} as {a[subject]!r} while running experiment {second.get('experiment_id')} of the same person fixes it as {b[subject]!r}"))
    return out


def notes(config, on: Optional[datetime.date] = None) -> List[str]:
    """The advice as lines for ``esoi check``'s notes; never a failure."""
    return [f"note: experiment {key}: {text}" for key, text in advice(config, on)]


def running_lines(config, intent_id: str, level: str = "##") -> List[str]:
    """The lines at the top of an intent's page: its running experiments in priority order, one line each with the reevaluation date.
    Nothing when it has none."""
    lines = []
    for n, row in enumerate(running(config, intent_id), 1):
        date = (row.get("reevaluate_on") or "").strip() or (row.get("reevaluate_when") or "").strip() or "no reevaluation set"
        lines.append(f"{n}. `{row.get('experiment_id', '')}` {row.get('name', '')}: {' '.join((row.get('focus') or '').split())} (reevaluate {date})")
    return [f"{level} Running experiments", ""] + lines + [""] if lines else []


def readme_lines(config, intent_id: str, level: str = "##") -> List[str]:
    """The lines an intent's page shows: each experiment with its status, focus, period and what is held fixed."""
    lines = []
    for row in rows(config):
        if (row.get("intent_id") or "").strip() != intent_id:
            continue
        period = f"from {row.get('starts_on', '')}" + (f", reevaluate {row.get('reevaluate_on')}" if (row.get("reevaluate_on") or "").strip() else "")
        fixed = f" Held fixed: {'; '.join(parts(row.get('held_fixed', '')))}." if (row.get("held_fixed") or "").strip() else ""
        lines.append(f"- `{row.get('experiment_id', '')}` ({row.get('status', '')}, {period}): {' '.join((row.get('focus') or '').split())}{fixed}")
    return [f"{level} Experiments", ""] + lines + [""] if lines else []
