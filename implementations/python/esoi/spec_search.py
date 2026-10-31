"""One search over records and other items: lexical, optional semantic, a confidence gate and at most one judging call.

``esoi.spec_index`` narrows the repository's records lexically. A system that also wants a semantic search, a model's final
choice, or one ranking across several sources (the records and its own notes, cards or documents) needs the stages around
that narrowing. They hold nothing about any one product, so they are here, and the product supplies only what is its own:

  * the VIEWS. A ``View`` is one searchable item read in place: a record of the specification index (``views_from_index``)
    or any other item (``views_from_items``). Nothing is copied into a store. A view's ``key`` is the record's own id for a
    record, and ``kind:id`` for any other source, so an item can never shadow a record.
  * the VECTOR SEARCH, optional: ``vector_search(text, k)`` returns view keys best first (or ``(key, cosine)`` pairs). The
    library holds no embeddings.
  * the JUDGE, optional: ``judge(task, lines, limit)`` is given one line per candidate and returns the keys it chose, as a
    list or as the model's reply text (``parse_ids`` reads ``{"ids": [...]}``). The library calls no model and holds no
    prompt; the caller's judge does both. A judge that raises or returns nothing readable keeps the candidates it was given.

The stages: lexical scores (field-weighted TF-IDF, the formula of ``spec_index.weighted_tfidf``), semantic scores, reciprocal
rank fusion, then by ``strategy``:

  * ``gated`` (default). A ``Gate`` answers a clear case from the two searches' agreement and an empty case with nothing,
    both without a judge call; any other request costs one call that judges the best ``gate.pool`` candidates together.
  * ``judge-all``. The judge sees every candidate, in parallel batches of ``batch_size``.
  * ``lexical``. The best ``lexical_top`` lexical matches. No vector search, no judge.

With no judge the fused candidates are the answer, never worse than lexical. Each ranked record then brings up to ``expand``
linked records, marked ``linked_from``. When the top record is a problem or intent that no solution serves, the result says
so (``no_solution_yet``), which is the cue to define one. The ``Gate`` thresholds are defaults tuned for one product's
records and embedding model: measure them on yours (a cosine means little across embedding models).
Standard library only.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import math

from . import spec_index
from esoi import implementation, solution

log = logging.getLogger("esoi.spec_search")

RECORD_SOURCE = "records"
STRATEGIES = ("gated", "judge-all", "lexical")
TAG_MODES = ("boost", "filter")
# The kinds a request is usually matched against; implementations are reached through their solution's links.
RECORD_CANDIDATE_KINDS = ("intent", "problem", "ideal", "solution", "metric")
NO_SOLUTION_KINDS = ("problem", "intent")
RRF_OFFSET = 60            # reciprocal rank fusion: score = sum 1 / (RRF_OFFSET + rank)
ITEM_WEIGHTS = (("title", 3.0), ("keywords", 2.0), ("text", 1.0))   # what the spec index gives a name, a short field, a body
LINE_TEXT = 160


@dataclass(frozen=True)
class Gate:
    """When the cheap stages decide alone. ``sure``: both searches rank the same view first and the top cosine is at least
    ``sure_vector`` or the top lexical score at least ``sure_lexical``. ``nothing``: the top cosine is below
    ``nothing_vector`` and the top lexical score below ``nothing_lexical``. A vector search that gives no scores can never
    make a sure answer. ``agree_rank``: a view in the top few of both searches joins a sure answer. ``pool``: how many
    candidates the single judging call sees."""
    sure_vector: float = 0.72
    sure_lexical: float = 60.0
    nothing_vector: float = 0.52
    nothing_lexical: float = 12.0
    agree_rank: int = 3
    pool: int = 20


@dataclass
class View:
    """One searchable item, read in place. ``links`` are keys of other views; ``tags`` are tag ids and problem ids."""
    kind: str
    id: str
    title: str
    text: str = ""
    source: str = RECORD_SOURCE
    links: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()
    terms: Mapping[str, float] = field(default_factory=dict)
    intent: str = ""

    @property
    def key(self) -> str:
        return self.id if self.source == RECORD_SOURCE else f"{self.kind}:{self.id}"


@dataclass
class TagTable:
    """Tag -> the problems it mitigates, and each solution's tags, read as data."""
    tag_problems: Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    solution_tags: Dict[str, Tuple[str, ...]] = field(default_factory=dict)

    def expand(self, wanted: Iterable[str]) -> set:
        """A requested tag stands for itself and for the problems it mitigates; a problem id stands for itself."""
        out = set()
        for tag in wanted:
            out.add(tag)
            out.update(self.tag_problems.get(tag, ()))
        return out


@dataclass
class Found:
    kind: str
    id: str
    source: str
    title: str
    key: str = ""
    linked_from: str = ""      # the key of the ranked item that brought this one; empty for a ranked item
    no_solution: bool = False  # a problem or intent that no solution serves


@dataclass
class Selection:
    """Ranked items best first, each followed by the items it brought. ``route`` says how it was decided: ``sure`` and
    ``nothing`` (no judge), ``judged``, ``unjudged`` (no judge given), ``lexical``. ``no_solution_yet`` is the key of the
    top record when it is a problem or intent that no solution serves."""
    items: List[Found] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)
    sources: Dict[str, List[str]] = field(default_factory=dict)   # key -> ["lexical", "vector"] that proposed it
    calls: int = 0
    failed_batches: int = 0
    route: str = ""
    no_solution_yet: str = ""

    @property
    def ids(self) -> List[str]:
        return [i.key for i in self.items]

    @property
    def linked(self) -> Dict[str, str]:
        return {i.key: i.linked_from for i in self.items if i.linked_from}


VectorSearch = Callable[[str, int], List[Any]]
Judge = Callable[[str, List[str], int], Union[str, Sequence[str], None]]


def terms_of(title: str, text: str = "", keywords: Sequence[str] = ()) -> Dict[str, float]:
    """Field-weighted terms for an item the index did not build, folded exactly as the index folds a record."""
    out: Dict[str, float] = {}
    for (name, weight), words in zip(ITEM_WEIGHTS, (title, " ".join(map(str, keywords)), text)):
        for term in spec_index.tokens(words):
            out[term] = max(out.get(term, 0.0), weight)
    return out


def views_from_items(items: Mapping[str, Mapping[str, Any]], *, kind: str = "item", source: str = "items",
                     text_of: Optional[Callable[[Mapping[str, Any]], str]] = None) -> List[View]:
    """A view per item dict (``{id: item}``) with optional ``name``, ``description`` or ``summary``, ``keywords`` and
    ``tags``. ``text_of(item)`` is the item's search text when it is not its description or summary."""
    views = []
    for item_id, item in items.items():
        if not isinstance(item, Mapping):
            continue
        title = str(item.get("name") or item_id)
        text = text_of(item) if text_of else str(item.get("description") or item.get("summary") or "")
        keywords = [k for k in (item.get("keywords") or []) if isinstance(k, str)]
        tags = tuple(t for t in (item.get("tags") or []) if isinstance(t, str))
        views.append(View(kind=kind, id=str(item_id), title=title, text=text, source=source, tags=tags,
                          terms=terms_of(title, text, keywords)))
    return views


def views_from_index(index: Mapping[str, Any], tag_table: Optional[TagTable] = None) -> List[View]:
    """A view per record of a specification index, every kind. A solution carries its tags plus its linked problems; a
    problem carries its own id plus every tag that mitigates it."""
    entries = index["entries"]
    kind_of = {e["id"]: e["kind"] for e in entries}
    mitigated_by: Dict[str, List[str]] = {}
    for tag, problems in (tag_table.tag_problems.items() if tag_table else ()):
        for problem_id in problems:
            mitigated_by.setdefault(problem_id, []).append(tag)
    views = []
    for e in entries:
        links = tuple(e.get("refs") or ())
        if e["kind"] == "solution":
            tags = (tag_table.solution_tags.get(e["id"], ()) if tag_table else ()) + tuple(r for r in links if kind_of.get(r) == "problem")
        elif e["kind"] == "problem":
            tags = (e["id"], *mitigated_by.get(e["id"], ()))
        else:
            tags = ()
        views.append(View(kind=e["kind"], id=e["id"], title=e.get("title", ""), text=e.get("summary", ""), links=links,
                          tags=tuple(dict.fromkeys(tags)), terms=e.get("terms") or {}, intent=e.get("intent", "")))
    return views


def lexical_scored(views: Sequence[View], text: str, k: int, kinds: Optional[Sequence[str]] = None) -> List[Tuple[str, float]]:
    """``(key, score)`` of the ``k`` views of the wanted kinds that best match the request: field-weighted TF-IDF with the
    document frequencies taken from ``views`` themselves, the formula of ``spec_index.weighted_tfidf``."""
    df: Counter = Counter()
    for v in views:
        df.update(v.terms.keys())
    n = len(views)
    index = {"entries": [{"id": v.key, "kind": v.kind, "terms": v.terms} for v in views
                         if kinds is None or v.kind in kinds]}
    hits = spec_index.ranked(index, text, lambda t: math.log((n + 1) / (df.get(t, 0) + 1)) + 1.0)
    return [(h["id"], h["score"]) for h in hits[:k]]


def semantic_scored(vector_search: Optional[VectorSearch], text: str, k: int, kind_of: Mapping[str, str],
                    kinds: Optional[Sequence[str]] = None) -> List[Tuple[str, float]]:
    """``(key, cosine)`` from the injected search, restricted to known keys of the wanted kinds. Bare keys score 0.0, so the
    gate cannot take them for strong evidence. A failing search is an empty one."""
    if vector_search is None:
        return []
    try:
        raw = vector_search(text, k * 3 if kinds is not None else k)
    except Exception:  # noqa: BLE001  semantic widening is optional; lexical still answers
        log.debug("vector search failed", exc_info=True)
        return []
    out = []
    for item in raw:
        key, score = item if isinstance(item, (tuple, list)) else (item, 0.0)
        if key in kind_of and (kinds is None or kind_of[key] in kinds):
            out.append((key, float(score)))
    return out[:k]


def fuse(rankings: List[List[str]], k: int) -> List[str]:
    """Reciprocal rank fusion: a key high in several lists beats one high in a single list."""
    score: Counter = Counter()
    for ranking in rankings:
        for rank, key in enumerate(ranking):
            score[key] += 1.0 / (RRF_OFFSET + rank + 1)
    return [key for key, _ in sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


def gate_decision(lexical: List[Tuple[str, float]], semantic: List[Tuple[str, float]], gate: Gate = Gate()) -> str:
    """``sure`` (answer without a judge), ``nothing`` (return nothing without a judge) or ``ask`` (one judge call)."""
    top_lex = lexical[0][1] if lexical else 0.0
    top_vec = semantic[0][1] if semantic else 0.0
    if lexical and semantic and lexical[0][0] == semantic[0][0] and (top_vec >= gate.sure_vector or top_lex >= gate.sure_lexical):
        return "sure"
    if top_vec < gate.nothing_vector and top_lex < gate.nothing_lexical:
        return "nothing"
    return "ask"


def parse_ids(text: str, offered: set) -> Optional[List[str]]:
    """The offered keys a model answered with, in its order, or None when the answer is not ``{"ids": [...]}``."""
    match = re.search(r"\{.*\}", text or "", re.S)
    try:
        found = json.loads(match.group(0))["ids"] if match else None
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(found, list):
        return None
    out: List[str] = []
    for key in found:
        if isinstance(key, str) and key in offered and key not in out:
            out.append(key)
    return out


def view_line(view: View, line_text: Optional[int] = LINE_TEXT) -> str:
    """The line a judge reads for one candidate: kind, key, title, and the text clipped to ``line_text`` characters
    (None keeps the whole text)."""
    text = " ".join((view.text or "").split())
    if line_text is not None:
        text = text[:line_text]
    return f"{view.kind} {view.key}: {view.title}" + (f". {text}" if text and text != view.title else "")


def ask(judge: Judge, task: str, keys: List[str], by_key: Mapping[str, View], limit: int,
        line_text: Optional[int] = LINE_TEXT) -> Optional[List[str]]:
    """One judge call over ``keys``; None when it fails or answers unreadably, so the caller keeps the candidates."""
    try:
        reply = judge(task, [view_line(by_key[k], line_text) for k in keys], limit)
    except Exception:  # noqa: BLE001  a failed call must never lose the candidates
        log.debug("judge failed", exc_info=True)
        return None
    if isinstance(reply, str):
        return parse_ids(reply, set(keys))
    if reply is None:
        return None
    return [k for k in dict.fromkeys(reply) if k in set(keys)]


def served_by_solution(views: Sequence[View]) -> set:
    """Keys of the problems and intents some solution serves: linked to one in either direction, or (an intent) the intent
    a solution belongs to. Everything else of those kinds is "no solution yet"."""
    by_key = {v.key: v for v in views}
    served = set()
    for v in views:
        if v.kind == "solution":
            served.update(r for r in v.links if r in by_key and by_key[r].kind in NO_SOLUTION_KINDS)
            if v.intent:
                served.add(v.intent)
        elif v.kind in NO_SOLUTION_KINDS and any(r in by_key and by_key[r].kind == "solution" for r in v.links):
            served.add(v.key)
    return served


def link_order(views: Sequence[View], link_kinds: Optional[Sequence[str]] = None) -> Dict[str, List[str]]:
    """Each view's links in the order they are brought in. With ``link_kinds`` only views of those kinds are links, one of
    each kind before a second of any, and the view's own intent counts as a link."""
    by_key = {v.key: v for v in views}
    out = {}
    for v in views:
        if link_kinds is None:
            out[v.key] = [r for r in v.links if r in by_key]
            continue
        refs = list(v.links) + ([v.intent] if v.intent and v.intent != v.key else [])
        per_kind = {k: [r for r in dict.fromkeys(refs) if r in by_key and by_key[r].kind == k] for k in link_kinds}
        ordered: List[str] = []
        for step in range(max((len(x) for x in per_kind.values()), default=0)):
            ordered += [per_kind[k][step] for k in link_kinds if step < len(per_kind[k])]
        out[v.key] = ordered
    return out


def finish(result: Selection, views: Sequence[View], chosen: List[str], expand: int,
           link_kinds: Optional[Sequence[str]] = None) -> Selection:
    """Add the ranked views and, after each, up to ``expand`` linked ones; mark the "no solution yet" views."""
    by_key = {v.key: v for v in views}
    order = link_order(views, link_kinds)
    keys: List[str] = list(chosen)
    brought: Dict[str, str] = {}
    for key in chosen:
        added = 0
        for ref in order.get(key, []):
            if added < expand and ref not in keys:
                keys.append(ref)
                brought[ref] = key
                added += 1
    served = served_by_solution(views)
    for key in keys:
        v = by_key[key]
        result.items.append(Found(kind=v.kind, id=v.id, source=v.source, title=v.title, key=key,
                                  linked_from=brought.get(key, ""), no_solution=v.kind in NO_SOLUTION_KINDS and key not in served))
    top = next((i for i in result.items if not i.linked_from and i.source == RECORD_SOURCE), None)
    if top is not None and top.no_solution:
        result.no_solution_yet = top.key
    return result


def propose(task: str, views: Sequence[View], vector_search: Optional[VectorSearch], k_lexical: int, k_vector: int,
            kinds: Optional[Sequence[str]], tags: Optional[Sequence[str]], tag_table: Optional[TagTable], tag_mode: str):
    lexical = lexical_scored(views, task, k_lexical, kinds)
    semantic = semantic_scored(vector_search, task, k_vector, {v.key: v.kind for v in views}, kinds)
    rankings = [r for r in ([k for k, _ in lexical], [k for k, _ in semantic]) if r]
    candidates = fuse(rankings, k_lexical + k_vector)
    if tags:
        by_key = {v.key: v for v in views}
        wanted = (tag_table or TagTable()).expand(tags)
        tagged = [k for k in candidates if wanted & set(by_key[k].tags)]
        candidates = tagged if tag_mode == "filter" else fuse(rankings + ([tagged] if tagged else []), k_lexical + k_vector)
    sources = {k: [n for n, r in (("lexical", lexical), ("vector", semantic)) if any(k == x for x, _ in r)] for k in candidates}
    return lexical, semantic, candidates, sources


@solution("spec-search")
def search(task: str, views: Sequence[View], *, judge: Optional[Judge] = None, vector_search: Optional[VectorSearch] = None,
           strategy: str = "gated", k_lexical: int = 15, k_vector: int = 15, max_ranked: Optional[int] = None, expand: int = 1,
           ranked_kinds: Optional[Sequence[str]] = None, link_kinds: Optional[Sequence[str]] = None,
           tags: Optional[Sequence[str]] = None, tag_table: Optional[TagTable] = None, tag_mode: str = "boost",
           gate: Gate = Gate(), batch_size: int = 10, max_workers: int = 4, unjudged_top: int = 3,
           lexical_top: int = 3, line_text: Optional[int] = LINE_TEXT) -> Selection:
    """The views ``task`` concerns, as a ``Selection`` (ranked items best first, each followed by the items it links).
    ``strategy`` is ``gated``, ``judge-all`` or ``lexical``; see the module. Nothing is called but the injected
    ``vector_search`` and ``judge``."""


def checked(strategy: str, tag_mode: str) -> None:
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy is one of {STRATEGIES}, not {strategy!r}")
    if tag_mode not in TAG_MODES:
        raise ValueError(f"tag_mode is one of {TAG_MODES}, not {tag_mode!r}")


@implementation("spec-search", "lexical-vector-gated")
def gated(task: str, views: Sequence[View], *, judge: Optional[Judge] = None, vector_search: Optional[VectorSearch] = None,
          strategy: str = "gated", k_lexical: int = 15, k_vector: int = 15, max_ranked: Optional[int] = None, expand: int = 1,
          ranked_kinds: Optional[Sequence[str]] = None, link_kinds: Optional[Sequence[str]] = None,
          tags: Optional[Sequence[str]] = None, tag_table: Optional[TagTable] = None, tag_mode: str = "boost",
          gate: Gate = Gate(), batch_size: int = 10, max_workers: int = 4, unjudged_top: int = 3,
          lexical_top: int = 3, line_text: Optional[int] = LINE_TEXT) -> Selection:
    """Lexical plus vector candidates, fused, then the gate: a clear case and an empty case are answered with no judge
    call, any other costs one call over the best ``gate.pool`` candidates. ``strategy`` ``judge-all`` and ``lexical`` run
    the other two stagings with the same arguments."""
    checked(strategy, tag_mode)
    by_key = {v.key: v for v in views}
    if strategy == "lexical":
        top = [k for k, _ in lexical_scored(views, task, min(k_lexical, lexical_top), ranked_kinds)]
        result = Selection(candidates=list(top), route="lexical", sources={k: ["lexical"] for k in top})
        return finish(result, views, top[:max_ranked] if max_ranked else top, expand, link_kinds)
    lexical, semantic, candidates, sources = propose(task, views, vector_search, k_lexical, k_vector, ranked_kinds, tags,
                                                     tag_table, tag_mode)
    result = Selection(candidates=candidates, sources=sources)
    cap = max_ranked or None
    take = lambda keys: keys[:cap] if cap else keys   # noqa: E731
    fallback = cap or unjudged_top
    if not candidates:
        result.route = "nothing"
        return result
    if strategy == "judge-all":
        if judge is None:
            result.route = "unjudged"
            return finish(result, views, take(list(candidates)), expand, link_kinds)
        batches = [candidates[i:i + batch_size] for i in range(0, len(candidates), batch_size)]
        with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(batches)))) as pool:
            verdicts = list(pool.map(lambda b: ask(judge, task, b, by_key, cap or len(b), line_text), batches))
        result.route, result.calls = "judged", len(batches)
        picked = set()
        for batch, verdict in zip(batches, verdicts):
            if verdict is None:
                result.failed_batches += 1
                picked.update(batch)           # keep the batch rather than lose it
            else:
                picked.update(verdict)
        return finish(result, views, take([k for k in candidates if k in picked]), expand, link_kinds)
    route = gate_decision(lexical, semantic, gate)
    if route == "nothing":
        result.route = "nothing"
        return result
    if route == "sure":
        agreed = {k for k, _ in lexical[:gate.agree_rank]} & {k for k, _ in semantic[:gate.agree_rank]}
        result.route = "sure"
        return finish(result, views, take([k for k in candidates if k in agreed]), expand, link_kinds)
    pool_keys = candidates[:gate.pool]
    if judge is None:
        result.route = "unjudged"
        return finish(result, views, pool_keys[:fallback], expand, link_kinds)
    result.route, result.calls = "judged", 1
    verdict = ask(judge, task, pool_keys, by_key, fallback, line_text)
    if verdict is None:
        result.failed_batches = 1
        verdict = pool_keys[:fallback]          # a failed call keeps the best few rather than nothing
    return finish(result, views, take([k for k in pool_keys if k in set(verdict)]), expand, link_kinds)


@implementation("spec-search", "lexical-only")
def lexical_only(task: str, views: Sequence[View], *, judge: Optional[Judge] = None, vector_search: Optional[VectorSearch] = None,
                 strategy: str = "lexical", k_lexical: int = 15, k_vector: int = 15, max_ranked: Optional[int] = None,
                 expand: int = 1, ranked_kinds: Optional[Sequence[str]] = None, link_kinds: Optional[Sequence[str]] = None,
                 tags: Optional[Sequence[str]] = None, tag_table: Optional[TagTable] = None, tag_mode: str = "boost",
                 gate: Gate = Gate(), batch_size: int = 10, max_workers: int = 4, unjudged_top: int = 3,
                 lexical_top: int = 3, line_text: Optional[int] = LINE_TEXT) -> Selection:
    """The baseline: the lexical top three, no vector search and no judge. Free and instant; shows what the rest adds."""
    return gated(task, views, strategy="lexical", k_lexical=k_lexical, max_ranked=max_ranked, expand=expand,
                 ranked_kinds=ranked_kinds, link_kinds=link_kinds, lexical_top=lexical_top)


def render(result: Selection, budget: int = 4000) -> str:
    """One line per item, kind first; a linked item says what brought it. The "no solution yet" line leads when set. Lines
    past ``budget`` characters are counted, not shown."""
    lines = []
    if result.no_solution_yet:
        lines.append(f"NO SOLUTION YET for {result.no_solution_yet}: define one (a solution record that addresses it), "
                     "then record what you did on the record.")
    for item in result.items:
        line = f"{item.kind} {item.key}: {item.title}"
        if item.linked_from:
            line += f"  (linked from {item.linked_from})"
        if item.no_solution:
            line += "  [no solution yet]"
        lines.append(line)
    out, used = [], 0
    for n, line in enumerate(lines):
        if used + len(line) + 1 > budget and out:
            out.append(f"({len(lines) - n} more not shown)")
            break
        out.append(line)
        used += len(line) + 1
    return "\n".join(out)
