"""Score one solution of a laid-out repository: can a person navigate from its spec to its code? Model-free checks over the tree an
arm lays out. A case passes when every check passes; ``aggregate`` reports how many solutions passed each check.

* ``together``: the folder holding the solution's spec row and the folder of each implementation's code are the same folder or one
  link apart (parent and child). A solution with no code named has nothing to keep apart.
* ``clicks``: from the repository's top README, following links between README pages, the page of the folder that holds the
  solution's row, naming it, is within ``CLICKS`` clicks.
* ``implemented``: the page that names the solution links, in one hop, to each file that holds its implementations (a code file, or
  the reference or registry file an implementation names).
* ``unduplicated``: no record of the solution (its row, its implementations) is kept in two places.
* ``readme``: every folder that holds the code of one of its implementations has a README.md.
* ``pure``: laying the records out again writes the same READMEs (nothing hand-kept, no clock).
"""
import posixpath
import re
from collections import deque
from pathlib import Path

import navigable_fixture
from verdict_score import tally, verdict_row
from esoi.structure.intent_registry import besidecode, intents
from esoi.structure.structure_check.interface import distance

CHECKS = ("together", "clicks", "implemented", "unduplicated", "readme", "pure")
CLICKS = 3
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s#]+)")


def pages(root):
    return {p.resolve(): p.read_text(encoding="utf-8") for p in Path(root).rglob("README.md")}


def clicks_to(root, goal_folder, solution_id):
    """The fewest links from the top README to a README in ``goal_folder`` that names the solution (None when unreachable)."""
    texts = pages(root)
    start = (Path(root) / "README.md").resolve()
    if start not in texts:
        return None
    seen, queue = {start}, deque([(start, 0)])
    while queue:
        page, depth = queue.popleft()
        if page.parent == goal_folder.resolve() and f"`{solution_id}`" in texts[page]:
            return depth
        for target in LINK.findall(texts[page]):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            nxt = (page.parent / target).resolve()
            nxt = nxt / "README.md" if nxt.is_dir() else nxt
            if nxt in texts and nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, depth + 1))
    return None


def hop(root, goal_folder, solution_id, files):
    """Whether a README page in ``goal_folder`` that names the solution links to every file of ``files`` (repository-relative)."""
    wanted = {(Path(root) / f).resolve() for f in files if f}
    texts = [t for p, t in pages(root).items() if p.parent == goal_folder.resolve() and f"`{solution_id}`" in t]
    reached = {(goal_folder / target).resolve() for text in texts for target in LINK.findall(text)}
    return wanted <= reached


def verdicts(arm, args, again):
    cfg, loaded = navigable_fixture.load(args["repo"], arm)
    root, digest = navigable_fixture.layout(args["repo"], arm)
    held = besidecode.rows_by_file(cfg)
    sid = args["solution"]
    spec = next((folder for row, folder, _ in held["solutions.csv"] if row.get("solution_id", "").strip() == sid), None)
    if spec is None:
        raise LookupError(f"no solution {sid} in {args['repo']}")
    mine = [(row, folder) for row, folder, _ in held["implementations.csv"] if row.get("solution_id", "").strip() == sid]
    code = [c for c in (besidecode.code_folder(cfg, row.get("filepath", "")) for row, _ in mine) if c is not None]
    out = {"together": all(distance(spec, c) <= 1 for c in code)}
    reached = clicks_to(root, spec, sid)
    out["clicks"] = reached is not None and reached <= CLICKS
    out["implemented"] = hop(root, spec, sid, [besidecode.root_relative_file(cfg, row.get("filepath", "")) for row, _ in mine])
    ids = {sid, *(row.get("implementation_id", "").strip() for row, _ in mine)}
    out["unduplicated"] = not any(ident in ids for _, ident, _ in intents.duplicate_rows(cfg))
    out["readme"] = all((c / "README.md").is_file() for c in code)
    out["pure"] = digest == again
    return out


def score_case(fn, case):
    args = case["args"]
    try:
        first = fn("layout", dict(args, fresh=False))
        again = fn("layout", dict(args, fresh=True))["digest"]
        found = verdicts(first["arm"], args, again)
    except LookupError as exc:
        return dict(ok=False, got="unavailable", note=str(exc))
    return verdict_row(found, CHECKS)


def aggregate(rows):
    return tally(rows, CHECKS)
