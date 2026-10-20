"""The specification index: a small, deterministic, non-AI map of a repository's intent records, so a person or a system
can find the few specifications that matter for a new use case or input without reading them all.

It is built from the records and holds no copy of them that a person edits. Every record becomes one entry with a
stable id (the record's own id), a tier-0 line (kind, id, name), a tier-1 summary (what it says in a sentence or two),
weighted terms for lexical matching, and its links to other records in both directions. Reading goes by tiers
(progressive disclosure): tier 0 to scan, tier 1 to decide, tier 2 (the full record row) only for what was chosen.

``find`` ranks entries lexically (field-weighted TF-IDF over the index's own document frequencies) and can pull in the
linked records of each hit (a problem's solutions, a solution's metrics). That is candidate narrowing and nothing more:
embeddings, vector stores and model calls are deliberately not here. A system that wants them (an agent runner is
one) takes the index's entries as its candidate set, adds its own semantic search and a model for the final choice.
The index is JSON-serializable (``build`` returns plain dicts) so that system can read it with no dependency on this
package; ``digest`` per entry and for the whole index says when a cached copy of it is stale. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from . import intents, registry as registry_module
from .config import Config
from .tables import SEP
from esoi import implementation, solution

VERSION = 1
KINDS = {"intent": "intent", "problem": "problem_id", "ideal": "ideal_id", "solution": "solution_id",
         "implementation": "implementation_id", "metric": "metric_id"}
# Columns that carry the words a person would use for the record, by weight. The first non-empty one is the title.
TITLE = {"intent": ["name"], "problem": ["problem"], "ideal": ["name", "principle"], "solution": ["name"],
         "implementation": ["name"], "metric": ["name"]}
SUMMARY = {"intent": ["vision_statement"], "problem": ["problem", "why_it_matters"], "ideal": ["principle", "state_description"],
           "solution": ["scoped_purpose", "goals"], "implementation": ["description"], "metric": ["scoped_purpose"]}
BODY = {"intent": ["opportunity"], "problem": ["who_has_it", "why_hard"], "ideal": ["hints_of_measurement"],
        "solution": ["knowledge", "usage_notes", "inputs", "outputs"], "implementation": ["advantages"],
        "metric": ["record"]}
WEIGHTS = {"id": 3.0, "title": 3.0, "summary": 2.0, "body": 1.0}
STOP = frozenset("a an and are as at be by for from has have in is it its of on or that the their this to was were which "
                 "with without not no but can may use used uses when what who why how into than then them they there so "
                 "such each every any all one more most only also other another own same too very if over under up out "
                 "about after before between both do does done get gets via per".split())
TOKEN = re.compile(r"[a-z0-9]+")
MAX_TERMS = 60
SUMMARY_CHARS = 280
LINK_COLUMN = re.compile(r"_ids?$")


def tokens(text: str) -> List[str]:
    """Lowercase words of at least three letters (or a digit) that are not stop words, with a light plural fold."""
    out = []
    for word in TOKEN.findall((text or "").lower()):
        if word in STOP or (len(word) < 3 and not word.isdigit()):
            continue
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.append(word)
    return out


def squash(text: str) -> str:
    return " ".join((text or "").split())


def first_text(row: Dict[str, str], columns: List[str]) -> str:
    return next((squash(row[c]) for c in columns if squash(row.get(c, ""))), "")


def clip(text: str, chars: int) -> str:
    if len(text) <= chars:
        return text
    cut = text[:chars].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "..."


def weighted_terms(entry_id: str, title: str, summary: str, body: str) -> Dict[str, float]:
    """The entry's terms with the heaviest field each appeared in, the strongest ``MAX_TERMS`` kept."""
    found: Dict[str, float] = {}
    for field, text in (("id", entry_id.replace("-", " ").replace(":", " ").replace("_", " ")), ("title", title),
                        ("summary", summary), ("body", body)):
        for term in tokens(text):
            found[term] = max(found.get(term, 0.0), WEIGHTS[field])
    kept = sorted(found.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_TERMS]
    return dict(sorted(kept))


def digest_of(row: Dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def entries_of(config: Config) -> List[Dict[str, Any]]:
    """One entry per record of every intent, in tree order. Links are the cells of ``*_id`` and ``*_ids`` columns that
    name another record, and each link is also recorded on the record it points to."""
    loaded = registry_module.load(config)
    rows_by_kind: Dict[str, List[Dict[str, str]]] = {
        "problem": loaded.problems, "ideal": loaded.ideals, "implementation": loaded.implementations,
        "metric": loaded.metrics, "solution": loaded.every_solution()}
    entries: List[Dict[str, Any]] = []
    for intent in intents.discover(config):
        row = dict(intent.row)
        row["intent_id"] = intent.intent_id
        entries.append({"id": intent.intent_id, "kind": "intent", "intent": intent.intent_id, "source": row})
    for kind, rows in rows_by_kind.items():
        for row in rows:
            if row.get(KINDS[kind], "").strip():
                entries.append({"id": row[KINDS[kind]].strip(), "kind": kind, "intent": row.get("intent_id", ""), "source": row})
    known = {e["id"] for e in entries}
    forward: Dict[str, List[str]] = {e["id"]: [] for e in entries}
    for e in entries:
        for column, cell in e["source"].items():
            if not LINK_COLUMN.search(column) or column == KINDS.get(e["kind"]) or column == "intent_id":
                continue
            for target in (part.strip() for part in cell.split(SEP)):
                if target in known and target != e["id"] and target not in forward[e["id"]]:
                    forward[e["id"]].append(target)
    back: Dict[str, List[str]] = {i: [] for i in known}
    for source, targets in forward.items():
        for target in targets:
            back[target].append(source)
    out = []
    for e in entries:
        row = e.pop("source")
        title = clip(first_text(row, TITLE[e["kind"]]), 100)
        summary = clip(first_text(row, SUMMARY[e["kind"]]), SUMMARY_CHARS)
        body = " ".join(squash(row.get(c, "")) for c in BODY[e["kind"]])
        refs = forward[e["id"]] + [i for i in back[e["id"]] if i not in forward[e["id"]]]
        out.append({**e, "title": title, "summary": summary, "refs": refs, "terms": weighted_terms(e["id"], title, summary, body),
                    "digest": digest_of(row)})
    return out


def build(config: Config) -> Dict[str, Any]:
    """The whole index: ``version``, ``digest``, entry count ``n``, ``df`` (how many entries hold each term) and ``entries``."""
    entries = entries_of(config)
    df = Counter(term for e in entries for term in e["terms"])
    whole = hashlib.sha256("".join(e["id"] + e["digest"] for e in entries).encode("utf-8")).hexdigest()[:12]
    return {"version": VERSION, "digest": whole, "n": len(entries), "df": dict(sorted(df.items())), "entries": entries}


def line(entry: Dict[str, Any]) -> str:
    """Tier 0: one line a reader or a model can scan."""
    return f"{entry['kind']} {entry['id']}: {entry['title']}"


@solution("spec-index")
def find_specs(index: Dict[str, Any], text: str, k: int = 8, expand: int = 0) -> List[Dict[str, Any]]:
    """The ``k`` entries of ``index`` that best match the words of a new use case or input, best first, each as
    ``{id, kind, score, matched, via}`` (``via`` is the hit a linked entry came in through, empty for a direct match).
    ``expand`` adds up to that many linked entries per hit after the direct matches. No model is called."""


def ranked(index: Dict[str, Any], text: str, idf_of) -> List[Dict[str, Any]]:
    query = Counter(tokens(text))
    scored = []
    for entry in index["entries"]:
        matched = sorted(t for t in query if t in entry["terms"])
        if not matched:
            continue
        score = sum(entry["terms"][t] * idf_of(t) for t in matched)
        scored.append({"id": entry["id"], "kind": entry["kind"], "score": round(score, 3), "matched": matched, "via": ""})
    return sorted(scored, key=lambda h: (-h["score"], h["id"]))


def with_links(index: Dict[str, Any], hits: List[Dict[str, Any]], k: int, expand: int) -> List[Dict[str, Any]]:
    by_id = {e["id"]: e for e in index["entries"]}
    out = hits[:k]
    if expand > 0:
        seen = {h["id"] for h in out}
        for hit in list(out):
            added = 0
            for ref in by_id[hit["id"]]["refs"]:
                if ref not in seen and added < expand:
                    seen.add(ref)
                    added += 1
                    out.append({"id": ref, "kind": by_id[ref]["kind"], "score": 0.0, "matched": [], "via": hit["id"]})
    return out


@implementation("spec-index", "weighted-tfidf")
def weighted_tfidf(index: Dict[str, Any], text: str, k: int = 8, expand: int = 0) -> List[Dict[str, Any]]:
    """Field-weighted TF-IDF over the index's own document frequencies: a rare term is worth more than a common one, and
    a word in a record's id or name is worth more than one in its body."""
    n, df = index["n"], index["df"]
    return with_links(index, ranked(index, text, lambda t: math.log((n + 1) / (df.get(t, 0) + 1)) + 1.0), k, expand)


@implementation("spec-index", "term-overlap")
def term_overlap(index: Dict[str, Any], text: str, k: int = 8, expand: int = 0) -> List[Dict[str, Any]]:
    """The baseline: count shared terms, every term and field worth the same. Kept so the metric can show what the
    weighting buys."""
    flat = {**index, "entries": [{**e, "terms": {t: 1.0 for t in e["terms"]}} for e in index["entries"]]}
    return with_links(index, ranked(flat, text, lambda t: 1.0), k, expand)


def get(index: Dict[str, Any], entry_id: str) -> Optional[Dict[str, Any]]:
    return next((e for e in index["entries"] if e["id"] == entry_id), None)


def show(config: Config, index: Dict[str, Any], entry_id: str, tier: int = 1) -> str:
    """Progressive disclosure of one entry. Tier 0 is its one line, tier 1 adds the summary and the linked ids, tier 2 is
    the full record row read from the records (never from the index, which holds no copy of them)."""
    entry = get(index, entry_id)
    if entry is None:
        raise KeyError(entry_id)
    lines = [line(entry)]
    if tier >= 1:
        lines += [entry["summary"], "links: " + (", ".join(entry["refs"]) or "none")]
    if tier >= 2:
        row = full_row(config, entry)
        lines += [f"{key}: {squash(value)}" for key, value in row.items() if squash(value)]
    return "\n".join(lines)


def full_row(config: Config, entry: Dict[str, Any]) -> Dict[str, str]:
    loaded = registry_module.load(config)
    if entry["kind"] == "intent":
        found = [i.row for i in intents.discover(config) if i.intent_id == entry["id"]]
        return found[0] if found else {}
    rows = {"problem": loaded.problems, "ideal": loaded.ideals, "implementation": loaded.implementations,
            "metric": loaded.metrics, "solution": loaded.every_solution()}[entry["kind"]]
    return next((r for r in rows if r.get(KINDS[entry["kind"]], "").strip() == entry["id"]), {})


def render_scan(index: Dict[str, Any], hits: List[Dict[str, Any]]) -> str:
    """The tier-0 lines of a result, one per hit, for a person or a prompt."""
    by_id = {e["id"]: e for e in index["entries"]}
    return "\n".join(line(by_id[h["id"]]) + (f"  (via {h['via']})" if h["via"] else "") for h in hits)
