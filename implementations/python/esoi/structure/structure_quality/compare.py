"""Compare two structures: the balanced number and each dimension before and after, the offenders fixed and introduced, and the per-solution
deltas of scope and coupling. A restructuring (a merge, a split, an adoption, an interface change, a moved module) is an alternative structure; this
is how the two are measured against each other, and the change is kept only when the number holds or rises.

Each side is a folder, or a git reference of the repository (a branch, a tag or a commit): a reference is checked out into a temporary worktree that is
removed afterwards. The files are read through the shared per-file cache (``project.FACTS``), so a file the two sides share is read once and
the second side costs only what changed. The assessor is passed in by the caller that holds the records (it adds the flow dimension), so this module
never imports the check that calls it.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from esoi.structure.structure_quality import coupling, scope
from esoi.structure.structure_quality.balance import WEIGHTS, Budgets
from esoi.structure.structure_quality.project import load

Assessor = Callable[[Path, int], Dict[str, Any]]
TOLERANCE = 0.0005   # a drop smaller than this is rounding, not a loss
SHOWN = 8
PATHS = re.compile(r"(?:[\w.-]+/)+([\w.-]+\.py)")


def same_offender(text: str) -> str:
    """An offender with its folders left out, so a module that only moved is neither fixed nor introduced."""
    return PATHS.sub(r"\1", text)


@contextmanager
def checked_out(side: str, repo: Path) -> Iterator[Path]:
    """The folder of one side: the folder itself, or a temporary worktree of the git reference in ``repo``, removed on the way out."""
    if Path(side).is_dir():
        yield Path(side).resolve()
        return
    found = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{side}^{{commit}}"], capture_output=True, text=True)
    if found.returncode != 0:
        raise ValueError(f"{side!r} is neither a folder nor a git reference of {repo}")
    parent = Path(tempfile.mkdtemp(prefix="esoi-sq-"))
    folder = parent / "tree"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(folder), found.stdout.strip()], capture_output=True, text=True, check=True)
    try:
        yield folder
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(folder)], capture_output=True, text=True)
        try:
            parent.rmdir()
        except OSError:
            pass


def coupling_by_unit(path: Path) -> Dict[str, float]:
    """Per unit that imports from another unit: the share of those imports that land on a declared entry point or on the shared kernel with shared names (1.0 when all do)."""
    total: Dict[str, int] = defaultdict(int)
    through: Dict[str, int] = defaultdict(int)
    for edge, verdict in coupling.classified(load(path), Budgets())[0]:
        total[edge[0]] += 1
        if verdict in ("entry", "kernel"):
            through[edge[0]] += 1
    return {u: round(through[u] / n, 4) for u, n in total.items()}


def scope_by_solution(path: Path) -> Dict[str, float]:
    """Per solution that has arms: the share of its arms that implement its whole interface."""
    total: Dict[str, int] = defaultdict(int)
    good: Dict[str, int] = defaultdict(int)
    for _, _, sid, problems in scope.arms_on_interface(load(path)):
        total[sid] += 1
        good[sid] += 0 if problems else 1
    return {s: round(good[s] / n, 4) for s, n in total.items()}


def deltas(before: Dict[str, float], after: Dict[str, float]) -> List[Tuple[str, Optional[float], Optional[float]]]:
    rows = [(k, before.get(k), after.get(k)) for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)]
    return sorted(rows, key=lambda r: ((r[2] if r[2] is not None else 0.0) - (r[1] if r[1] is not None else 0.0), r[0]))


def common_score(before: Dict[str, Any], after: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], List[str]]:
    """The two balanced numbers over the dimensions measured on both sides, so a dimension measured on one side only cannot move the comparison."""
    names = [n for n in WEIGHTS if before["dimensions"][n]["score"] is not None and after["dimensions"][n]["score"] is not None]
    weight = sum(WEIGHTS[n] for n in names)
    if not weight:
        return None, None, names
    one = lambda report: round(sum(WEIGHTS[n] * report["dimensions"][n]["score"] for n in names) / weight, 4)
    return one(before), one(after), names


def compare(before: str, after: str, assess: Assessor, repo: str = ".", stage: int = 1) -> Dict[str, Any]:
    """``before`` and ``after`` are folders or git references of ``repo``; ``assess(folder, stage)`` returns one side's report."""
    with checked_out(before, Path(repo)) as one, checked_out(after, Path(repo)) as two:
        first, second = assess(one, stage), assess(two, stage)
        scope_rows = deltas(scope_by_solution(one), scope_by_solution(two))
        coupling_rows = deltas(coupling_by_unit(one), coupling_by_unit(two))
    old, new, names = common_score(first, second)
    fixed: Dict[str, List[str]] = {}
    introduced: Dict[str, List[str]] = {}
    for name in WEIGHTS:
        was, now = first["dimensions"][name]["offenders"], second["dimensions"][name]["offenders"]
        was_keys, now_keys = {same_offender(o) for o in was}, {same_offender(o) for o in now}
        fixed[name] = [o for o in was if same_offender(o) not in now_keys]
        introduced[name] = [o for o in now if same_offender(o) not in was_keys]
    holds = old is not None and new is not None and new >= old - TOLERANCE
    return {"before": first, "after": second, "common_before": old, "common_after": new, "common_dimensions": names, "holds": holds,
            "fixed": fixed, "introduced": introduced, "scope_by_solution": scope_rows, "coupling_by_unit": coupling_rows}


def number(value: Optional[float]) -> str:
    return "not measured" if value is None else f"{value:.3f}"


def lines(result: Dict[str, Any], shown: int = SHOWN) -> List[str]:
    first, second = result["before"], result["after"]
    out = [f"structure quality before {number(first['score'])} after {number(second['score'])}; over the {len(result['common_dimensions'])} dimensions measured on "
           f"both sides: before {number(result['common_before'])} after {number(result['common_after'])}"]
    for name, weight in WEIGHTS.items():
        a, b = first["dimensions"][name]["score"], second["dimensions"][name]["score"]
        change = "" if a is None or b is None else f"  {b - a:+.3f}"
        out.append(f"  {name:<9}{number(a):>14}{number(b):>14}{change}  weight {weight:.2f}")
    for label, key in (("offenders fixed", "fixed"), ("offenders introduced", "introduced")):
        every = [(n, o) for n, os in result[key].items() for o in os]
        out.append(f"{label}: {len(every)}")
        out += [f"  {n}: {o}" for n, o in every[:shown]]
        if len(every) > shown:
            out.append(f"  ... and {len(every) - shown} more")
    for label, rows in (("scope per solution (arms that implement the whole interface)", result["scope_by_solution"]),
                        ("coupling per unit (imports of other units that land on an entry point or the shared kernel)", result["coupling_by_unit"])):
        out.append(f"{label}: {len(rows)} changed")
        out += [f"  {k}: {number(a)} -> {number(b)}" for k, a, b in rows[:shown]]
        if len(rows) > shown:
            out.append(f"  ... and {len(rows) - shown} more")
    out.append("keep the change: the number holds or rises" if result["holds"] else
               "the number falls: keep the change only with the reason stated in the commit (what the lower number does not see, and why the structure is better)")
    return out
