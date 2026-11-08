"""Which solutions a request, a change or a candidate concerns: a multi-label classification over a repository's records.

Each arm takes the specification index and a text and returns solution ids best first, each with a score and the records that
reached it. The arms compete on ``metric-solution-relevance`` (recall of the solutions that needed consideration counts most, since a
missed solution is a skipped consideration). No arm here calls a model; a model classifier is the next arm, measured by its caller.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.understanding.spec_search import spec_index

DEFAULT_LIMIT = 5
KEEP_SHARE = 0.25   # a solution scoring under this share of the best one is left out: noise costs each pass it would start


def owners(entry: Dict[str, Any], solution_ids: set) -> List[str]:
    """The solutions one index entry speaks for: itself, an implementation's solution, or the solutions it links to."""
    if entry["kind"] == "solution":
        return [entry["id"]]
    if entry["kind"] == "implementation":
        sid = entry["id"].split(":", 1)[0]
        return [sid] if sid in solution_ids else []
    return [ref for ref in entry["refs"] if ref in solution_ids]


def rank_solutions(index: Dict[str, Any], hits: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """Solutions best first, each scored by the sum of its hits' scores (a linked hit counts half), with the records that reached it."""
    by_id = {e["id"]: e for e in index["entries"]}
    solution_ids = {e["id"] for e in index["entries"] if e["kind"] == "solution"}
    scored: Dict[str, Dict[str, Any]] = {}
    for hit in hits:
        weight = hit["score"] if hit["score"] else 0.0
        for sid in owners(by_id[hit["id"]], solution_ids):
            found = scored.setdefault(sid, {"solution_id": sid, "score": 0.0, "via": []})
            found["score"] += weight if not hit.get("via") else weight / 2
            if hit["id"] not in found["via"]:
                found["via"].append(hit["id"])
    ranked = sorted(scored.values(), key=lambda s: (-s["score"], s["solution_id"]))
    top = ranked[0]["score"] if ranked else 0.0
    ranked = [s for s in ranked if s["score"] >= KEEP_SHARE * top]
    return [{**s, "score": round(s["score"], 3)} for s in ranked[:limit]]


@solution("solution-relevance", kind="event", example={"index": {"entries": [], "df": {}, "n": 0}, "text": "a request"})
def relevant_solutions(index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
    """The solutions a text concerns, best first, each ``{solution_id, score, via}``, from the specification index."""


@implementation("solution-relevance", "lexical_index")
def lexical_index(index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
    """The baseline: the field-weighted lexical hits of the index, each mapped to the solution it belongs to."""
    return rank_solutions(index, spec_index.find_specs(index, text, k=max(limit * 4, 12)), limit)


@implementation("solution-relevance", "index_with_links")
def index_with_links(index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
    """The lexical hits plus the records each hit links to, so a problem, metric or ideal that matched brings its solutions; a linked
    record scores half of the hit that brought it."""
    hits = spec_index.find_specs(index, text, k=max(limit * 4, 12))
    by_id = {e["id"]: e for e in index["entries"]}
    linked = [{"id": ref, "kind": by_id[ref]["kind"], "score": h["score"], "matched": [], "via": h["id"]}
              for h in hits for ref in by_id[h["id"]]["refs"] if by_id[ref]["kind"] in ("solution", "implementation")]
    return rank_solutions(index, hits + linked, limit)


ARMS: Dict[str, Callable[..., List[Dict[str, Any]]]] = {"lexical_index": lexical_index, "index_with_links": index_with_links}


def library_default() -> str:
    """The arm esoi's own records select, read from the selection snapshot shipped with the package: a library-internal choice, never
    resolved through the records of the repository that calls it (which hold no such solution)."""
    from esoi.runtime.implementation_selection.select import snapshot_defaults
    try:
        found = snapshot_defaults(Path(__file__).resolve().parents[2] / "esoi_selection.json").get("solution-relevance", "")
    except (OSError, ValueError, KeyError):
        found = ""
    return found if found in ARMS else "lexical_index"


def ranked(index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT, arm: str = "") -> List[Dict[str, Any]]:
    """The arm named, else the one esoi's own records select."""
    return ARMS[arm or library_default()](index, text, limit)




CLASSIFY_INSTRUCTIONS = (
    "You decide which solutions of a project a matter concerns, so each one gets its own consideration. A solution needs consideration "
    "when the matter would change it, use it, or be judged by its records. Missing a solution that needed consideration is worse than "
    "naming one extra. Reply with JSON only: {\"solutions\": [ids, most relevant first]}, at most LIMIT ids, using only the ids listed.")


def solution_lines(index: Dict[str, Any], only: Any = None) -> List[str]:
    """One line per solution of the index (or of ``only``): its id, its name and the summary the index holds."""
    wanted = set(only) if only is not None else None
    return [f"{e['id']}: {e['title']}. {e['summary']}" for e in index["entries"]
            if e["kind"] == "solution" and (wanted is None or e["id"] in wanted)]


def classification_prompt(index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT, only: Any = None) -> str:
    """The prompt a model arm sends: the instructions, the solutions it may choose from and the matter. No model is called here."""
    return (CLASSIFY_INSTRUCTIONS.replace("LIMIT", str(limit)) + "\n\nSolutions:\n" + "\n".join(solution_lines(index, only))
            + f"\n\nThe matter:\n{text}\n")


def parse_ids(reply: str, known: Any) -> List[str]:
    """The known solution ids a model's reply names, in its order: from its JSON when it parses, else every known id it mentions."""
    import json
    import re
    known = list(known)
    found: List[str] = []
    match = re.search(r"\{.*\}", reply or "", re.S)
    try:
        listed = json.loads(match.group(0)).get("solutions", []) if match else []
    except (ValueError, AttributeError):
        listed = []
    for item in listed if isinstance(listed, list) else []:
        if isinstance(item, str) and item in known and item not in found:
            found.append(item)
    if not found:
        found = sorted((k for k in known if re.search(r"(?<![\w-])" + re.escape(k) + r"(?![\w-])", reply or "")),
                       key=lambda k: (reply or "").find(k))
    return found


def model_arm(answer: Callable[[str], str], candidates: str = "") -> Callable[..., List[Dict[str, Any]]]:
    """A classifier that asks a model, through ``answer(prompt) -> reply`` the caller supplies: over every solution, or, with
    ``candidates`` naming a free arm, over that arm's wider candidate list (lexical recall first, then the model's judgement)."""
    def classify(index: Dict[str, Any], text: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
        only = [s["solution_id"] for s in ARMS[candidates](index, text, limit * 3)] if candidates else None
        if only is not None and not only:
            return []
        known = only if only is not None else [e["id"] for e in index["entries"] if e["kind"] == "solution"]
        picked = parse_ids(answer(classification_prompt(index, text, limit, only)), known)[:limit]
        return [{"solution_id": sid, "score": float(limit - n), "via": ["model"]} for n, sid in enumerate(picked)]
    return classify
