"""The 2026-10-26 field change: how a solution's tags carry their risk ids, and how records written before it migrate.

Solutions: ``scoped_purpose`` is replaced by ``description``, ``purpose``, ``approach`` and ``out_of_scope``; the flat
``risk_addressed`` column is replaced by ``risk_ids`` inside each tag. Metrics: ``scoped_purpose`` is renamed ``purpose``
and ``disadvantages`` is new. The words of the author's SKILL.md define each field; nothing here writes new wording.

Tags in a CSV cell
------------------
A solution's ``tags`` cell holds a JSON array, exactly the shape the JSON APIs and the database use::

    [{"tag": "dedup", "risk_ids": ["R1", "prob-x"]}, {"tag": "python", "risk_ids": []}]

Consumers never parse that cell by hand: ``parse_tags`` reads it, ``format_tags`` writes it. ``parse_tags`` also reads a
cell written before the change (plain labels separated by ``;``) as tags with no risk ids.

Migration (mechanical, no invented wording)
-------------------------------------------
``upgrade_row`` is applied when records are read, so a file that still has ``scoped_purpose`` keeps loading (``esoi check``
reports its old header until it is migrated). ``migrate_folder`` rewrites a records folder in place; ``esoi fields migrate``
runs it. Standard library only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .tables import SEP, read_csv, read_header, write_csv

Row = Dict[str, str]
Tag = Dict[str, object]

OLD = "scoped_purpose"
FLAT_RISK = "risk_addressed"
NEW_SOLUTION_COLUMNS = ["description", "purpose", "approach", "out_of_scope"]
NEW_METRIC_COLUMNS = ["purpose", "disadvantages"]


# ---- tags ---------------------------------------------------------------------------------------------------------

def parse_tags(cell: Optional[str]) -> List[Tag]:
    """The tags of a ``tags`` cell as ``[{"tag": label, "risk_ids": [problem ids]}]``. An empty cell is no tags. A cell that
    is not JSON is the older form, labels separated by ``;``, and gives tags with no risk ids. Raises ``ValueError`` for
    JSON that is not a list of tags."""
    text = (cell or "").strip()
    if not text:
        return []
    if not text.startswith(("[", "{")):
        return [{"tag": label.strip(), "risk_ids": []} for label in text.split(SEP) if label.strip()]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"tags cell is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("tags cell must be a JSON list of {\"tag\", \"risk_ids\"} objects")
    out: List[Tag] = []
    for item in data:
        if isinstance(item, str):
            out.append({"tag": item.strip(), "risk_ids": []})
        elif isinstance(item, dict) and isinstance(item.get("tag"), str):
            risks = item.get("risk_ids") or []
            if not isinstance(risks, list) or not all(isinstance(r, str) for r in risks):
                raise ValueError(f"risk_ids of tag {item['tag']!r} must be a list of strings")
            out.append({"tag": item["tag"].strip(), "risk_ids": [r.strip() for r in risks if r.strip()]})
        else:
            raise ValueError(f"not a tag: {item!r}")
    return out


def format_tags(tags: Iterable[Tag]) -> str:
    """The ``tags`` cell for these tags (``parse_tags`` reads it back). No tags is an empty cell."""
    clean = [{"tag": str(t["tag"]).strip(), "risk_ids": [str(r).strip() for r in (t.get("risk_ids") or []) if str(r).strip()]}
             for t in tags if str(t.get("tag", "")).strip()]
    return json.dumps(clean, ensure_ascii=False, separators=(", ", ": ")) if clean else ""


# ---- splitting the old text ---------------------------------------------------------------------------------------

SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
EXCLUSION = re.compile(r"^(?:it\s+|this\s+|they\s+)?(?:intentionally\s+|deliberately\s+)?"
                       r"(?:avoids?|is\s+not|are\s+not|does\s+not|do\s+not|cannot|never|excludes?|not)\b", re.I)
BLIND = re.compile(r"\b(?:cannot|can't|can not|does not|doesn't|do not|never)\s+(?:see|detect|tell|capture|measure)\b|\bblind\s+spots?\b|"
                   r"\bis\s+blind\b|\bmisses\b", re.I)


def sentences(text: str) -> List[str]:
    return [s.strip() for s in SENTENCE.split((text or "").strip()) if s.strip()]


def split_solution_text(text: str) -> Tuple[str, str]:
    """``(purpose, out_of_scope)`` from an old solution ``scoped_purpose``: sentences that state exclusions go to
    ``out_of_scope``, the rest to ``purpose``. Sentences are moved whole and in order."""
    purpose: List[str] = []
    excluded: List[str] = []
    for sentence in sentences(text):
        (excluded if EXCLUSION.match(sentence) else purpose).append(sentence)
    return " ".join(purpose), " ".join(excluded)


def split_metric_text(text: str) -> Tuple[str, str]:
    """``(purpose, disadvantages)`` from an old metric ``scoped_purpose``: a sentence that says what the metric cannot see
    goes to ``disadvantages``, the rest to ``purpose``. With no such sentence, disadvantages is empty."""
    purpose: List[str] = []
    blind: List[str] = []
    for sentence in sentences(text):
        (blind if BLIND.search(sentence) else purpose).append(sentence)
    return " ".join(purpose), " ".join(blind)


# ---- rows ---------------------------------------------------------------------------------------------------------

def upgrade_row(entity: str, row: Row) -> Row:
    """A solution or metric row in the current fields. A row that already has them is returned as it is; a row with the old
    ``scoped_purpose`` gets the split text in the new fields (a new field that already has text is never overwritten) and
    loses ``scoped_purpose``; a flat ``risk_addressed`` is dropped after being attached to the tags when there is exactly one
    tag. Other entities are returned unchanged."""
    if entity not in ("solution", "metric") or (OLD not in row and FLAT_RISK not in row):
        return row
    out = dict(row)
    if OLD in out:
        old = out.pop(OLD)
        first, second = (split_solution_text(old) if entity == "solution" else split_metric_text(old))
        second_key = "out_of_scope" if entity == "solution" else "disadvantages"
        if not out.get("purpose", "").strip():
            out["purpose"] = first
        if not out.get(second_key, "").strip():
            out[second_key] = second
    if entity == "solution":
        flat = out.pop(FLAT_RISK, "")
        tags = parse_tags(out.get("tags", "")) if not out.get("tags", "").lstrip().startswith("[") else None
        if tags is not None:
            risks = [r for r in flat.split(SEP) if r.strip()]
            if len(tags) == 1 and risks:
                tags[0]["risk_ids"] = [r.strip() for r in risks]
            out["tags"] = format_tags(tags)
    return out


def upgrade_rows(entity: str, rows: List[Row]) -> List[Row]:
    return [upgrade_row(entity, row) for row in rows]


def migrated_header(entity: str, header: List[str]) -> List[str]:
    """The header of a records file after migration: new columns take the place of the old one, in template order."""
    new = NEW_SOLUTION_COLUMNS if entity == "solution" else NEW_METRIC_COLUMNS
    out: List[str] = []
    for column in header:
        if column == OLD:
            out += [c for c in (new if entity == "solution" else ["purpose"]) if c not in header and c not in out]
        elif column == FLAT_RISK:
            continue
        else:
            out.append(column)
    if entity == "solution":
        if "description" not in out:
            out.insert(out.index("name") + 1 if "name" in out else 0, "description")
        for column in NEW_SOLUTION_COLUMNS:
            if column not in out:
                out.append(column)
        if "tags" not in out:
            out.insert(out.index("measures_of_success") + 1 if "measures_of_success" in out else len(out), "tags")
    else:
        for column in NEW_METRIC_COLUMNS:
            if column not in out:
                out.insert(out.index("record") + 1 if column == "disadvantages" and "record" in out else len(out), column)
    return out


FILES = {"solution": "solutions.csv", "metric": "metrics.csv"}


def migrate_folder(folder: Path, apply: bool = True) -> List[str]:
    """Migrate the ``solutions.csv`` and ``metrics.csv`` of one records folder in place (mechanical split only; see the
    module text). Returns one line per file that changed or would change; a folder already current returns nothing."""
    done: List[str] = []
    for entity, name in FILES.items():
        path = Path(folder) / name
        if not path.is_file():
            continue
        header = read_header(path)
        if OLD not in header and FLAT_RISK not in header and (entity == "metric" and "disadvantages" in header and "purpose" in header
                or entity == "solution" and all(c in header for c in NEW_SOLUTION_COLUMNS + ["tags"])):
            continue
        rows = upgrade_rows(entity, read_csv(path))
        new_header = migrated_header(entity, header)
        if apply:
            write_csv(path, new_header, rows)
        done.append(f"{path}: {len(rows)} record(s), columns {', '.join(c for c in new_header if c not in header) or 'unchanged'}"
                    + ("" if apply else " (dry run)"))
    return done


def migrate_tree(folders: Iterable[Path], apply: bool = True) -> List[str]:
    out: List[str] = []
    for folder in folders:
        out += migrate_folder(folder, apply)
    return out
