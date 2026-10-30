"""The slice of the specification a piece of work serves: its next priority and the metric that measures it, found without a model.

``esoi.spec_index`` finds the records a request concerns. A task needs less than that and says it more exactly: which
solution the work serves, that solution's NEXT milestone (its milestones are in priority order, so the next one is the first
that is neither met nor archived), and the solution's authoritative metric with the command that records it. That is a
``SpecSlice``. It is small enough to sit in a brief, and it is what a metric before and after is taken against
(``esoi.metric_meter``, ``esoi.iteration``).

Nothing here calls a model and nothing guesses:

  * the records are the repository's own ``esoi/`` files, found from the working folder; with no working folder, or outside a
    repository that has records, the answer is ``None``;
  * the solution is chosen by a ``Chooser`` (default: ``lexical_choice``, the best lexical matches of the specification index)
    and only when it is clear: the chooser is sure, or every candidate it offers belongs to one solution. An ambiguous request
    gets no slice, because a wrong metric measured with confidence is worse than none;
  * a milestone's target is a number only when its text holds exactly one number; otherwise it is ``None``. A percent is read
    as a fraction (``100%`` is 1.0), the scale of a pass rate or a share;
  * a metric is the solution's ``authoritative_metric_id``, or its only metric; a solution with several and no named one gets
    none.

A milestone is met when it carries the marker ``esoi.fields`` reads (``[met: DATE]``), and archived when its text begins with
``Archived`` (or ``(archived)`` or ``[archived]``).

``RepoSliceSource`` runs the lookup in a thread with a timeout and never raises. Every setting is an argument: the way the
repository is found from a folder, where the index is cached, the time limit. The library reads no environment.
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple

from . import config as config_module, fields, registry as registry_module, spec_index
from .tables import ids

log = logging.getLogger("esoi.spec_slice")

SLICE_TIMEOUT_SECONDS = 3.0   # the lookup is local and lexical (tens of milliseconds); a brief never waits long for it
MILESTONE_CHARS = 280
# Records that state intent are candidates; implementations are reached through their solution.
CANDIDATE_KINDS = ("intent", "problem", "ideal", "solution", "metric")
LEXICAL_PICKS = 3        # how many of the best lexical matches the default chooser offers
MIN_LEXICAL_SCORE = 12.0  # a best match scoring below this is no evidence the request concerns anything

ARCHIVED_MARK = re.compile(r"^[\(\[]?\s*archived\b[\)\]]?\s*[:\-]?\s*", re.IGNORECASE)
NUMBER_TOKEN = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(%?)(?![\w])")


@dataclass(frozen=True)
class Milestone:
    number: int
    text: str
    archived: bool = False
    met: bool = False


@dataclass(frozen=True)
class SpecSlice:
    """What a task serves. ``root`` is where the records were found (never sent to a consumer: see ``to_dict``)."""
    root: str
    solution_id: str
    solution_name: str = ""
    milestone: str = ""                  # the next open milestone's text; "" when the solution has none
    milestone_number: int = 0
    target: Optional[float] = None       # the one number in the milestone, or None
    target_text: str = ""
    metric_id: str = ""
    metric_name: str = ""
    metric_command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"solution_id": self.solution_id, "solution_name": self.solution_name, "milestone": self.milestone,
                "milestone_number": self.milestone_number, "target": self.target, "target_text": self.target_text,
                "metric_id": self.metric_id, "metric_name": self.metric_name}


@dataclass(frozen=True)
class Chosen:
    """What a chooser settled on: record ids best first (the selected records, not ones brought in as links), and whether it is
    sure of the best one."""
    ids: Tuple[str, ...] = ()
    sure: bool = False


Chooser = Callable[[str, Dict[str, Any]], Chosen]   # (request, specification index) -> Chosen


class SliceSource(Protocol):
    """Where a task's slice comes from. ``None`` means there is none to give (not a repository with records, or unclear)."""

    def slice_for(self, request: str, working_dir: Optional[str] = None) -> Optional[SpecSlice]:
        ...


def milestone(number: int, text: str, met: bool = False) -> Milestone:
    text = text.strip()
    archived = ARCHIVED_MARK.match(text)
    return Milestone(number, text[archived.end():].strip() if archived else text, bool(archived), met)


def parse_milestones(cell: str) -> List[Milestone]:
    """The ordered milestones of a solution's ``milestones`` cell: ``1. text. 2. text.``, or one unnumbered text.

    Read by ``esoi.fields.parse_milestones`` in order: a numbered list is read only when the cell starts with ``1.`` and the
    numbers run 1, 2, 3, so a number inside a sentence never splits one."""
    parsed = fields.parse_milestones(" ".join((cell or "").split()), in_order=True)
    return [milestone(i, str(m["text"]), bool(m["met"])) for i, m in enumerate(parsed, 1)]


def next_milestone(cell: str) -> Optional[Milestone]:
    """The first milestone that is neither met nor archived, or None."""
    return next((m for m in parse_milestones(cell) if not m.archived and not m.met and m.text), None)


def target_of(text: str) -> Tuple[Optional[float], str]:
    """``(value, token)`` when the text holds exactly one number, else ``(None, "")``. A percent is a fraction."""
    found = list(NUMBER_TOKEN.finditer(text or ""))
    if len(found) != 1:
        return None, ""
    value = float(found[0].group(1))
    return (value / 100 if found[0].group(2) else value), found[0].group(0)


def lexical_choice(request: str, index: Dict[str, Any], picks: int = LEXICAL_PICKS, min_score: float = MIN_LEXICAL_SCORE,
                   kinds: Sequence[str] = CANDIDATE_KINDS) -> Chosen:
    """The default chooser: the best ``picks`` lexical matches of the wanted kinds, or nothing when even the best scores below
    ``min_score``. Never sure: a lexical match alone is not agreement between two searches."""
    hits = [h for h in spec_index.find_specs(index, request, k=len(index["entries"])) if h["kind"] in kinds]
    if not hits or hits[0]["score"] < min_score:
        return Chosen()
    return Chosen(tuple(h["id"] for h in hits[:picks]))


def solutions_of(chosen: Chosen, index: Dict[str, Any]) -> List[str]:
    """The solution ids a choice settles on: the best one when the chooser is sure, the only one otherwise.

    A solution is itself, a metric or an implementation is the solution it belongs to; a problem or an ideal serves several
    solutions and names none."""
    by_id = {e["id"]: e for e in index["entries"]}
    found: List[str] = []
    for entry_id in chosen.ids:
        entry = by_id.get(entry_id)
        if entry is None:
            continue
        if entry["kind"] == "solution":
            owners = [entry_id]
        elif entry["kind"] in ("metric", "implementation"):
            owners = [ref for ref in entry["refs"] if by_id.get(ref, {}).get("kind") == "solution"]
        else:
            owners = []
        found.extend(o for o in owners if o not in found)
    return found[:1] if chosen.sure or len(found) == 1 else []


def authoritative_metric(solution: Dict[str, str], metrics: Dict[str, Dict[str, str]]) -> Optional[Dict[str, str]]:
    """The solution's named authoritative metric record, else its only metric, else None."""
    named = (solution.get("authoritative_metric_id") or "").strip()
    linked = ids(solution.get("metric_ids", ""))
    return metrics.get(named or (linked[0] if len(linked) == 1 else ""))


def nearest_root(working_dir: Optional[str]) -> Optional[Path]:
    """The repository whose records apply to a folder: the folder of the nearest configuration at or above it. None for no
    folder (the process's own folder is not one: it would be a guess about where the work happens)."""
    if not working_dir:
        return None
    found = config_module.find(Path(working_dir))
    return found.parent if found else None


def index_of(config: Any, cache_dir: Optional[Path] = None) -> Dict[str, Any]:
    """The specification index of the repository: rebuilt each time, or kept in ``cache_dir`` until a record file changes."""
    if cache_dir is None:
        return spec_index.build(config)
    name = hashlib.sha256(str(Path(config.root).resolve()).encode()).hexdigest()[:12] + ".json"
    return spec_index.cached(config, Path(cache_dir) / name)


def slice_from_root(request: str, root: Path, choose: Chooser = lexical_choice,
                    cache_dir: Optional[Path] = None) -> Optional[SpecSlice]:
    """The slice for a request in the repository at ``root``, or None. Raises on a repository that cannot be read."""
    config = config_module.load(Path(root))
    index = index_of(config, cache_dir)
    wanted = solutions_of(choose(request, index), index)
    if not wanted:
        return None
    loaded = registry_module.load(config)
    solution = next((r for r in loaded.every_solution() if r.get("solution_id") == wanted[0]), None)
    if solution is None:
        return None
    metric = authoritative_metric(solution, {m.get("metric_id", ""): m for m in loaded.metrics}) or {}
    step = next_milestone(solution.get("milestones", ""))
    if step is None and not metric:
        return None
    value, token = target_of(step.text if step else "")
    return SpecSlice(root=str(config.root), solution_id=wanted[0], solution_name=solution.get("name", ""),
                     milestone=step.text if step else "", milestone_number=step.number if step else 0, target=value,
                     target_text=token, metric_id=metric.get("metric_id", ""), metric_name=metric.get("name", ""),
                     metric_command=metric.get("command", ""))


def describe_metric(metric_id: str, working_dir: Optional[str] = None,
                    find_root: Callable[[Optional[str]], Optional[Path]] = nearest_root) -> Dict[str, str]:
    """``{"name", "solution_id"}`` of a metric record in the repository around ``working_dir``, ``{}`` when unknown."""
    try:
        root = find_root(working_dir)
        if root is None or not metric_id:
            return {}
        loaded = registry_module.load(config_module.load(Path(root)))
        record = next((m for m in loaded.metrics if m.get("metric_id") == metric_id), None)
        if record is None:
            return {}
        owners = [r["solution_id"] for r in loaded.every_solution() if metric_id in ids(r.get("metric_ids", ""))]
        return {"name": record.get("name", ""), "solution_id": owners[0] if len(owners) == 1 else ""}
    except Exception:  # noqa: BLE001  an unreadable record set describes nothing
        log.debug("metric not described", exc_info=True)
        return {}


class RepoSliceSource:
    """The slice from the repository's ESOI records, with a time limit. Never raises.

    ``find_root(working_dir)`` says which repository applies (default: the nearest configuration above the folder, none for no
    folder); ``choose`` picks the records a request concerns; ``cache_dir`` keeps the index between calls."""

    def __init__(self, timeout_seconds: float = SLICE_TIMEOUT_SECONDS, *,
                 find_root: Callable[[Optional[str]], Optional[Path]] = nearest_root, choose: Chooser = lexical_choice,
                 cache_dir: Optional[Path] = None):
        self.timeout_seconds = timeout_seconds
        self.find_root, self.choose, self.cache_dir = find_root, choose, cache_dir

    def slice_for(self, request: str, working_dir: Optional[str] = None) -> Optional[SpecSlice]:
        try:
            root = self.find_root(working_dir)
        except Exception:  # noqa: BLE001
            log.debug("repository not found", exc_info=True)
            return None
        if root is None:
            return None   # nothing is read and no thread is started
        box: Dict[str, Optional[SpecSlice]] = {}

        def look() -> None:
            try:
                box["found"] = slice_from_root(request, root, self.choose, self.cache_dir)
            except Exception:  # noqa: BLE001  a missing or odd record set means no slice, never a failed run
                log.debug("no specification slice", exc_info=True)

        worker = threading.Thread(target=look, name="spec-slice", daemon=True)
        worker.start()
        worker.join(self.timeout_seconds)
        return box.get("found")


def next_priority_block(found: SpecSlice, closing: str = "") -> str:
    """The short block a brief carries: the next milestone and the metric, then ``closing`` (what the consumer asks of the worker)."""
    metric = (f"{found.metric_name or found.metric_id} (metric_id {found.metric_id})" if found.metric_id
              else "none is named for this solution; record the one that applies")
    lines = [f"NEXT PRIORITY for this work (solution_id {found.solution_id}):",
             "Milestone: " + (found.milestone[:MILESTONE_CHARS] if found.milestone else "none is set for this solution"),
             f"Metric: {metric}"]
    return "\n".join(lines + ([closing] if closing else []))
