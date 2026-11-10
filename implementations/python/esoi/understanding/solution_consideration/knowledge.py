"""Knowledge records: one row per piece of knowledge a solution's definition or implementations rest on, kept in ``knowledge.csv`` in a
records folder beside ``problems.csv`` and linked to any number of solutions.

Which knowledge bears on a pass depends on the situation, so a solution's prompt does not write all of it: by default the prompt is the
solution's stable part, and its knowledge items come back beside it as candidates for the caller's own context retrieval (each can
become a card in the caller's card store, ``cards``). With no retriever, ``ranked`` orders them by status, the strength of their
source and recency, contradicted ones labelled. Nothing is capped by a count: what fits is the caller's choice.

Columns: ``knowledge_id``, ``claim`` (one sentence), ``kind`` (assumption, best guess, evidence, theory, perspective, lesson), ``source``,
``solution_ids`` (``;``-separated), ``status`` (active, superseded, contradicted, expired), ``status_by`` (what superseded or contradicted
it), ``recorded`` and ``expiration`` (``YYYY-MM-DD``), and ``investigation_id`` (optional: the investigation record, ``investigations.py``, that found it). A source is written as one of:

    result:<component>/<arm>@<date>        a row of the results log
    url:<address> grade <A-D>              public evidence, graded
    person:<who>, <date>: "<their words>"  a person's words
    mistake:<record id>                    a mistake that taught it
    anything else                          a free source (weakest)

A solution whose ``knowledge`` cell is still free text has its sentences read as items too (source ``the solution's knowledge field``),
so nothing waits for ``esoi knowledge migrate``. Standard library only; no model call.
"""
from __future__ import annotations

import datetime
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.tables import SEP, ids, read_csv, write_csv
from esoi.understanding.solution_consideration import investigations
from esoi.understanding.spec_search.spec_index import tokens

FILE = "knowledge.csv"
COLUMNS = ["knowledge_id", "claim", "kind", "source", "solution_ids", "status", "status_by", "recorded", "expiration", "investigation_id"]
KINDS = ("assumption", "best guess", "evidence", "theory", "perspective", "lesson")
STATUSES = ("active", "superseded", "contradicted", "expired")
SOURCE_WEIGHT = {"person": 4.0, "result": 3.5, "mistake": 3.0, "evidence": 2.0, "other": 1.0, "field": 0.5}
GRADE_WEIGHT = {"A": 3.0, "B": 2.5, "C": 2.0, "D": 1.0}
LINKS = re.compile(r"^\s*knowledge\.csv:\s*(.*)$", re.I)
ENTRY = re.compile(r"^\s*\[(?P<kind>[a-z ]+)\]\s*(?P<claim>.*?)\s*(?:\(source:\s*(?P<source>[^)]*)\))?\s*$", re.I)
FIELD_SOURCE = "the solution's knowledge field"
KEEP_SHARE = 0.5   # the reference retriever keeps items scoring at least this share of the best one


def today() -> datetime.date:
    return datetime.date.today()


def source_kind(source: str) -> Tuple[str, str]:
    """``(kind, grade)`` of a source: result, evidence (with its grade), person, mistake, field or other."""
    text = (source or "").strip()
    low = text.lower()
    if low.startswith("result:") or "results.csv" in low:
        return "result", ""
    if low.startswith("url:") or low.startswith("http"):
        found = re.search(r"\bgrade\s+([A-D])\b", text)
        return "evidence", found.group(1) if found else ""
    if low.startswith("person:"):
        return "person", ""
    if low.startswith("mistake:"):
        return "mistake", ""
    if low.startswith(FIELD_SOURCE):
        return "field", ""
    return "other", ""


def as_date(text: str) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat((text or "").strip()[:10])
    except ValueError:
        return None


def item_of(row: Mapping[str, str], on: datetime.date) -> Dict[str, Any]:
    """One knowledge row as the dict a consumer reads, its status made current (an active item past its expiration is expired)."""
    kind, grade = source_kind(row.get("source", ""))
    status = (row.get("status") or "active").strip().lower()
    expires = as_date(row.get("expiration", ""))
    if status == "active" and expires is not None and expires < on:
        status = "expired"
    recorded = as_date(row.get("recorded", ""))
    age = (on - recorded).days if recorded else 3650
    rank = SOURCE_WEIGHT.get(kind, 1.0) + (GRADE_WEIGHT.get(grade, 0.0) / 3 if kind == "evidence" else 0.0) + max(0.0, 1 - age / 365)
    return {"id": (row.get("knowledge_id") or "").strip(), "claim": " ".join((row.get("claim") or "").split()),
            "kind": (row.get("kind") or "").strip().lower(), "source": (row.get("source") or "").strip(), "source_kind": kind, "grade": grade,
            "solution_ids": ids(row.get("solution_ids", "")), "status": status, "status_by": (row.get("status_by") or "").strip(),
            "recorded": (row.get("recorded") or "").strip(), "expiration": (row.get("expiration") or "").strip(), "rank": round(rank, 3)}


def rows(config) -> List[Dict[str, str]]:
    """Every row of every ``knowledge.csv`` in the records folders, each with the folder it is in (``folder``)."""
    out = []
    for _, folder in intents.folders(config):
        for row in read_csv(folder / FILE):
            out.append({**investigations.renamed(row), "folder": str(folder)})
    return out


def field_items(solution: Mapping[str, str]) -> List[Dict[str, str]]:
    """The items a free-text ``knowledge`` cell holds: one per ``[kind] claim (source: ...)`` line, else one per sentence."""
    text = (solution.get("knowledge") or "").strip()
    if not text or LINKS.match(text):
        return []
    sid = solution.get("solution_id", "")
    parts = [p for p in re.split(r"\n+", text) if p.strip()]
    if not any((m := ENTRY.match(p)) and m.group("kind").lower() in KINDS for p in parts):
        parts = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text) if p.strip()]
        if len(parts) == 1 and "; " in parts[0]:   # one sentence listing several sources of knowledge: one item per entry
            parts = [p.strip().rstrip(".") + "." for p in parts[0].split("; ") if p.strip()]
    out = []
    for n, part in enumerate(parts, 1):
        found = ENTRY.match(part)
        kind = (found.group("kind").lower() if found and found.group("kind").lower() in KINDS else "best guess")
        claim = found.group("claim") if found and found.group("kind").lower() in KINDS else part
        source = (found.group("source") if found and found.group("source") else f"{FIELD_SOURCE} of {sid}")
        out.append({"knowledge_id": f"{sid}-field-{n}", "claim": claim.strip(), "kind": kind, "source": source, "solution_ids": sid,
                    "status": "active"})
    return out


def all_items(config, registry=None, on: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
    """Every knowledge item of the repository: the rows of its knowledge tables and the items still held as free text."""
    from esoi.structure.intent_registry import registry as registry_module
    loaded = registry or registry_module.load(config)
    on = on or today()
    found = [item_of(r, on) for r in rows(config)]
    for solution in loaded.every_solution():
        found += [item_of(r, on) for r in field_items(solution)]
    return found


def items(network, sid: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """``(active, inactive)`` items linked to one solution, each list best first by ``rank``."""
    on = network.today or today()
    every = network.knowledge if getattr(network, "knowledge", None) is not None else all_items(network.config, network.registry, on)
    mine = [i for i in every if sid in i["solution_ids"]]
    active = sorted((i for i in mine if i["status"] == "active"), key=lambda i: (-i["rank"], i["id"]))
    inactive = sorted((i for i in mine if i["status"] != "active"), key=lambda i: (-i["rank"], i["id"]))
    return active, inactive


def line(item: Mapping[str, Any]) -> str:
    """One item as a prompt line; an item that is not active says so and what replaced it."""
    label = "" if item["status"] == "active" else f" [{item['status'].upper()}" + (f" by {item['status_by']}" if item["status_by"] else "") + "]"
    grade = f", grade {item['grade']}" if item["grade"] else ""
    return f"{item['id']} ({item['kind']}; {item['source_kind']}{grade}){label}: {item['claim']} Source: {item['source']}"


def select(found: Sequence[Mapping[str, Any]], task: str) -> List[Mapping[str, Any]]:
    """The reference retriever: items whose claim shares rare words with the task, keeping those scoring near the best. A consumer with
    its own retriever (cards, vectors) uses that instead; this one exists so a repository with none still chooses by the situation."""
    wanted = set(tokens(task))
    if not wanted or not found:
        return []
    counts: Dict[str, int] = {}
    for item in found:
        for term in set(tokens(item["claim"])):
            counts[term] = counts.get(term, 0) + 1
    scored = []
    for item in found:
        terms = set(tokens(item["claim"])) & wanted
        score = sum(math.log((len(found) + 1) / counts[t]) for t in terms) * (1 + item["rank"] / 10)
        if score > 0:
            scored.append((score, item))
    if not scored:
        return []
    best = max(s for s, _ in scored)
    return [i for s, i in sorted(scored, key=lambda p: (-p[0], p[1]["id"])) if s >= KEEP_SHARE * best]


def folder_of(config, sid: str) -> Path:
    """The records folder whose ``solutions.csv`` holds ``sid`` (the structure folder when none does)."""
    for _, folder in intents.folders(config):
        if any(r.get("solution_id") == sid for r in read_csv(folder / "solutions.csv")):
            return folder
    return config.structure


def add(config, item: Mapping[str, Any]) -> Tuple[str, bool]:
    """Write one knowledge item, ensure-one: an item with the same ``knowledge_id``, else the same claim and solutions, is kept as it is.
    Returns ``(knowledge_id, created)``. The item goes to the records folder of its first solution."""
    solutions = list(item.get("solution_ids") or []) if not isinstance(item.get("solution_ids"), str) else ids(item["solution_ids"])
    if not solutions or not (item.get("claim") or "").strip() or not (item.get("source") or "").strip():
        raise ValueError("a knowledge item needs a claim, a source and at least one solution id")
    kind = (item.get("kind") or "best guess").strip().lower()
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, not {kind!r}")
    folder = folder_of(config, solutions[0])
    held = [investigations.renamed(r) for r in read_csv(folder / FILE)]
    claim = " ".join(str(item["claim"]).split())
    for row in held:
        if (item.get("knowledge_id") and row.get("knowledge_id") == item["knowledge_id"]) or (
                " ".join(row.get("claim", "").split()) == claim and set(ids(row.get("solution_ids", ""))) == set(solutions)):
            return row.get("knowledge_id", ""), False
    taken = {r.get("knowledge_id", "") for r in held}
    number = sum(1 for t in taken if t.startswith(f"k-{solutions[0]}-")) + 1
    while f"k-{solutions[0]}-{number}" in taken:
        number += 1
    new_id = item.get("knowledge_id") or f"k-{solutions[0]}-{number}"
    row = {"knowledge_id": new_id, "claim": claim, "kind": kind, "source": str(item["source"]).strip(), "solution_ids": SEP.join(solutions),
           "status": (item.get("status") or "active"), "status_by": item.get("status_by", ""),
           "recorded": item.get("recorded") or today().isoformat(), "expiration": item.get("expiration", ""),
           "investigation_id": item.get("investigation_id", "")}
    write_csv(folder / FILE, COLUMNS, held + [row])
    return new_id, True


def migrate(config, apply: bool = False) -> List[str]:
    """Move every free-text ``knowledge`` cell into knowledge rows and leave the cell as the list of their ids. A dry run without ``apply``."""
    from esoi.structure.intent_registry.tables import read_header
    report: List[str] = []
    for _, folder in intents.folders(config):
        path = folder / "solutions.csv"
        solutions = read_csv(path)
        changed = False
        for solution in solutions:
            found = field_items(solution)
            if not found:
                continue
            made = []
            for item in found:
                item = {k: v for k, v in item.items() if k != "knowledge_id"}
                if item["source"].startswith(FIELD_SOURCE):
                    item["source"] = f"{FIELD_SOURCE} of {solution['solution_id']}, migrated {today().isoformat()}"
                made.append(add(config, item)[0] if apply else "new")
            report.append(f"{solution['solution_id']}: {len(found)} item(s) -> {', '.join(made)}")
            if apply:
                solution["knowledge"] = "knowledge.csv: " + SEP.join(made)
                changed = True
        if changed:
            write_csv(path, read_header(path), solutions)
    return report


def stable_card(network, sid: str, text: str) -> Dict[str, Any]:
    """The solution's stable part as one managed card: its writer owns the digest, while learned notes may accrue onto it."""
    row = network.solutions[sid]
    return {"id": f"solution-{sid}", "kind": "solution", "title": row.get("name") or sid, "summary": row.get("purpose", ""),
            "content": text, "keywords": sorted(set(tokens(f"{sid} {row.get('name', '')} {row.get('purpose', '')}")))[:20],
            "tags": [f"solution:{sid}"], "managed_by": "esoi", "managed_fields": ["title", "summary", "content", "keywords"]}


def item_card(item: Mapping[str, Any]) -> Dict[str, Any]:
    """One knowledge item as a card for the consumer's card store: kind and source are card fields; an inactive item is for quarantine."""
    return {"id": f"knowledge-{item['id']}", "kind": "knowledge", "knowledge_kind": item["kind"], "title": item["claim"][:100],
            "summary": item["claim"], "source": item["source"], "source_kind": item["source_kind"], "grade": item["grade"],
            "status": item["status"], "status_by": item["status_by"], "expiration": item["expiration"], "rank": item["rank"],
            "keywords": sorted(set(tokens(item["claim"])))[:20], "tags": [f"solution:{s}" for s in item["solution_ids"]],
            "managed_by": "esoi", "managed_fields": ["title", "summary", "source", "status", "knowledge_kind"]}


def problems(config, registry, history, on: Optional[datetime.date] = None) -> List[Tuple[str, str]]:
    """``(key, problem)`` for rule S61: a row without a source, an unknown kind, status or solution, an active item past its expiration,
    and an active item sourced on a result that a newer result of the same arm departs from."""
    on = on or today()
    known = {r.get("solution_id", "") for r in registry.every_solution()}
    out: List[Tuple[str, str]] = []
    for row in rows(config):
        key = (row.get("knowledge_id") or "").strip() or "(no id)"
        item = item_of(row, on)
        if not item["source"]:
            out.append((key, "has no source; name a result, a graded address, a person's words with the date, or a mistake"))
        if item["kind"] not in KINDS:
            out.append((key, f"kind {item['kind']!r} is not one of {', '.join(KINDS)}"))
        if (row.get("status") or "active").strip().lower() not in STATUSES:
            out.append((key, f"status {row.get('status')!r} is not one of {', '.join(STATUSES)}"))
        unknown = [s for s in item["solution_ids"] if s not in known]
        if not item["solution_ids"] or unknown:
            out.append((key, f"names no known solution ({', '.join(unknown) or 'none'})"))
        if item["status"] == "expired" and (row.get("status") or "active").strip().lower() == "active":
            out.append((key, f"expired on {item['expiration']}; renew it with a new source or set its status to expired"))
        if item["status"] == "active" and (newer := newer_result(item["source"], history)):
            out.append((key, f"a newer result may contradict it ({newer}); re-confirm it, or set its status to superseded or contradicted"))
    return out


RESULT_SOURCE = re.compile(r"result:\s*(\w+)/(\w[\w@=.,-]*)@(\d{4}-\d{2}-\d{2})")


def newer_result(source: str, history: Mapping[str, Mapping[str, List[Mapping[str, str]]]]) -> str:
    """A newer row of the arm a ``result:`` source cites whose pass rate differs from the cited row's by a tenth or more, described."""
    found = RESULT_SOURCE.search(source or "")
    if not found:
        return ""
    component, arm, date = found.groups()
    rows_of = list(history.get(component, {}).get(arm, []))

    def rate(row) -> float:
        try:
            return int(row.get("passed") or 0) / max(int(row.get("cases") or 1), 1)
        except ValueError:
            return 0.0
    cited = [r for r in rows_of if (r.get("date") or "") == date]
    newer = [r for r in rows_of if (r.get("date") or "") > date]
    if not cited or not newer:
        return ""
    last = newer[-1]
    if abs(rate(last) - rate(cited[-1])) < 0.1:
        return ""
    return f"{component}/{arm} passed {last.get('passed')} of {last.get('cases')} on {last.get('date')}, against {cited[-1].get('passed')} of {cited[-1].get('cases')} cited"
