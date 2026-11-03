"""Rule S40, advisory: where a repository that keeps its records beside the code deviates from the standard.

It runs only where ``esoi.toml`` lists ``[records] beside_code`` (the repository opted in) and never fails a check: each finding
goes to ``esoi check --findings`` with its next action. The standard is ``docs/reference/records-beside-code.md``. Findings:

* a solution whose spec row and code are in folders more than one link apart (the row is in one folder, the code of an
  implementation in another that is neither its parent nor its child);
* a folder that holds the code of an implementation but has no ``README.md`` (the page is written from the records the folder holds);
* a record kept in two places.

A waiver excuses one key: the solution id, the folder's path from the repository root, or the record id.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .. import besidecode, intents
from .base import Context, RuleGroup

SUMMARIES = {
    "S40": "Opt-in by `[records] beside_code`: a solution's spec row and the code of its implementations are in the same folder or one "
           "link apart; a folder that holds an implementation's code has a README.md; a record lives in one place (advisory; waive as the "
           "solution id, the folder's path or the record id).",
}


def distance(a: Path, b: Path) -> int:
    """How many folder links lie between two folders of one tree (0 when they are the same folder)."""
    a, b = a.resolve(), b.resolve()
    shared = len(besidecode.common([a, b]).parts)
    return (len(a.parts) - shared) + (len(b.parts) - shared)


def rel(config, path: Path) -> str:
    return besidecode.relative_to_root(config, path)


def findings(ctx: Context) -> List[str]:
    config = ctx.config
    out: List[str] = []
    for name, ident, where in intents.duplicate_rows(config):
        if not ctx.waived("S40", ident):
            out.append(f"S40 {ident}: a row of {name} is kept in {len(where)} places ({', '.join(rel(config, w) for w in where)}); "
                       "next: delete the copies that are not in the folder that holds its code")
    held = besidecode.rows_by_file(config)
    solution_folder = {r.get("solution_id", "").strip(): folder for r, folder, _ in held["solutions.csv"]}
    moves = {(m.file, m.ident): m.target for m in besidecode.plan(config)}
    codes: Dict[str, List[Path]] = {}
    for row, folder, _ in held["implementations.csv"]:
        here = besidecode.code_folder(config, row.get("filepath", ""))
        if here is not None:
            codes.setdefault(row.get("solution_id", "").strip(), []).append(here)
            if not (here / "README.md").is_file() and not ctx.waived("S40", rel(config, here)):
                out.append(f"S40 {rel(config, here)}: holds the code of {row.get('implementation_id', '')} but has no README.md; "
                           "next: run `esoi records place --apply`, which moves the records here and writes the page, "
                           "or list this folder under [records] beside_code")
    for sid, folder in sorted(solution_folder.items()):
        far = sorted({rel(config, c) for c in codes.get(sid, []) if distance(folder, c) > 1})
        if far and not ctx.waived("S40", sid):
            target = moves.get(("solutions.csv", sid))
            action = (f"run `esoi records place --apply` (it moves the row to {rel(config, target)})" if target is not None
                      else "list the folder that holds its code under [records] beside_code, then run `esoi records place --apply`")
            out.append(f"S40 {sid}: its spec is in {rel(config, folder)} and its code in {', '.join(far)}, more than one link apart; next: {action}")
    return out


def run(ctx: Context) -> List[str]:
    """The findings go to ``ctx.advisory``; none is a problem."""
    if ctx.config.intent_mode and ctx.config.records.get("beside_code") and not ctx.config.is_disabled("S40"):
        ctx.advisory.extend(findings(ctx))
    return []


GROUP = RuleGroup(SUMMARIES, run)
