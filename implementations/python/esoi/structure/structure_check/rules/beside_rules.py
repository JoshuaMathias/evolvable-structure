"""Rule S40, advisory: where a repository that keeps its records beside the code deviates from the standard.

It runs only where ``esoi.toml`` lists ``[records] beside_code`` (the repository opted in) and never fails a check: each finding
goes to ``esoi check --findings`` with its next action. The standard is ``docs/reference/records-beside-code.md``. Findings:

* a solution whose spec row and code are in folders more than one link apart (the row is in one folder, the code of an
  implementation in another that is neither its parent nor its child);
* a folder that holds the code of an implementation but has no ``README.md`` (the page is written from the records the folder holds).
  A folder of arms owned by an intent elsewhere (``<evaluation_dir>/*/impls``, or a glob under ``[records] arm_folders``) is covered
  by the README ``esoi readmes`` generates for it, which lists the arms and links to the owner's README; the finding then only asks
  to run ``esoi readmes``, and the link distance of its code is measured through that owner link;
* a record kept in two places;
* a reference or registry implementation (a CSV or markdown file that lists the files, services or practices that implement a solution)
  that lists a path that does not resolve or names a row that does not exist, and code that declares a solution but is missing from
  the registry that lists its implementations (also where ``[rules.S40] enabled = true`` without ``beside_code``).

A waiver excuses one key: the solution id, the folder's path from the repository root, or the record id.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from esoi.structure.intent_registry import besidecode, implementedby, intents
from esoi.structure.intent_registry.specify_from_code import declarations
from esoi.structure.structure_check.rules.base import Context, RuleGroup

SUMMARIES = {
    "S40": "Opt-in by `[records] beside_code` (or `[rules.S40] enabled = true`): a solution's spec row and the code of its implementations are in the same folder or one "
           "link apart; a folder that holds an implementation's code has a README.md; a record lives in one place; a reference or registry implementation lists only paths that resolve and every code file "
           "that declares the solution (advisory; waive as the solution id, the folder's path, the implementation id or the record id).",
}


def distance(a: Path, b: Path) -> int:
    """How many folder links lie between two folders of one tree (0 when they are the same folder)."""
    a, b = a.resolve(), b.resolve()
    shared = len(besidecode.common([a, b]).parts)
    return (len(a.parts) - shared) + (len(b.parts) - shared)


def reach(arms: Dict[Path, list], spec: Path, code: Path, row_folder: Path, shared: bool = False) -> int:
    """The link distance from a solution's spec folder to its code. A folder of arms owned by an intent has a generated README that
    links to the owner's README, so its code is one link past the folder that holds the row. Code in a shared layer the intent's own
    code imports (``shared``, see ``besidecode.shared_layer_reaches``) is one link from the intent."""
    if shared:
        return 1
    if code in arms and any(folder.resolve() == row_folder.resolve() for _, folder in arms[code]):
        return distance(spec, row_folder) + 1
    return distance(spec, code)


def shared_in(config, spec: Path, code_file: str, graph: Dict[str, set], intent_code: Dict[Path, set],
              solution_id: str = "", interface: str = "", resolved: Dict[str, Path] = None) -> bool:
    """Whether ``code_file`` is in a shared layer that the code of the intent holding ``spec`` imports. ``resolved`` maps each file of
    the graph to its resolved path, worked out once by the caller for every solution it asks about."""
    if not graph or not code_file:
        return False
    resolved = resolved if resolved is not None else {rel_file: (config.root / rel_file).resolve() for rel_file in graph}
    here = spec.resolve()
    mine = {rel_file for rel_file, path in resolved.items() if path.is_relative_to(here)} | intent_code.get(here, set())
    return besidecode.shared_layer_reaches(config, spec, code_file, graph, mine, solution_id, interface)


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
    interfaces = {r.get("solution_id", "").strip(): (r.get("interface_name", "") or "").strip() for r, _, _ in held["solutions.csv"]}
    moves = {(m.file, m.ident): m.target for m in besidecode.plan(config)}
    arms = besidecode.arm_folders(config)
    codes: Dict[str, List[Tuple[Path, Path, str]]] = {}
    graph = besidecode.import_graph(config) if config.package else {}
    intent_code: Dict[Path, set] = {}
    resolved = {rel_file: (config.root / rel_file).resolve() for rel_file in graph}
    for row, folder, _ in held["implementations.csv"]:
        here = besidecode.code_folder(config, row.get("filepath", ""))
        if here is not None:
            codes.setdefault(row.get("solution_id", "").strip(), []).append((here, folder, besidecode.root_relative_file(config, row.get("filepath", ""))))
            intent_code.setdefault(folder.resolve(), set()).add(besidecode.root_relative_file(config, row.get("filepath", "")))
            if not (here / "README.md").is_file() and not ctx.waived("S40", rel(config, here)):
                if here in arms:
                    owners = ", ".join(sorted({o for o, _ in arms[here]}))
                    out.append(f"S40 {rel(config, here)}: holds arms owned by {owners} but its generated README.md is not written; "
                               "next: run `esoi readmes`")
                else:
                    out.append(f"S40 {rel(config, here)}: holds the code of {row.get('implementation_id', '')} but has no README.md; "
                               "next: run `esoi records place --apply`, which moves the records here and writes the page, "
                               "or list this folder under [records] beside_code (or [records] arm_folders when the record "
                               "belongs to an intent elsewhere)")
    out = list(dict.fromkeys(out))
    for sid, folder in sorted(solution_folder.items()):
        near: Dict[Path, bool] = {}
        for c, row_folder, code_file in codes.get(sid, []):   # one file of the solution in a shared layer the intent reaches covers its arms there
            near[c] = near.get(c, False) or shared_in(config, folder, code_file, graph, intent_code, sid, interfaces.get(sid, ""), resolved)
        far = sorted({rel(config, c) for c, row_folder, code_file in codes.get(sid, []) if reach(arms, folder, c, row_folder, near[c]) > 1})
        if far and not ctx.waived("S40", sid):
            target = moves.get(("solutions.csv", sid))
            action = (f"run `esoi records place --apply` (it moves the row to {rel(config, target)})" if target is not None
                      else "list the folder that holds its code under [records] beside_code, then run `esoi records place --apply`")
            out.append(f"S40 {sid}: its spec is in {rel(config, folder)} and its code in {', '.join(far)}, more than one link apart; next: {action}")
    return out


def reference_findings(ctx: Context) -> List[str]:
    """A reference or registry implementation that lists a path that does not resolve (or names a row that does not exist), and code
    that declares a solution but is missing from the registry that lists its implementations."""
    try:
        declared = declarations.scan(ctx.config)
    except (OSError, ValueError):
        declared = None
    return [line for key, line in implementedby.problems(ctx.config, ctx.registry, declared) if not ctx.waived("S40", key)]


def run(ctx: Context) -> List[str]:
    """The findings go to ``ctx.advisory``; none is a problem. The layout findings need ``beside_code``; the findings about what an
    implementation lists run wherever S40 runs (``beside_code`` set, or ``[rules.S40] enabled = true``)."""
    config = ctx.config
    if not config.intent_mode or config.is_disabled("S40"):
        return []
    if config.records.get("beside_code"):
        ctx.advisory.extend(findings(ctx))
    if config.records.get("beside_code") or config.enabled("S40"):
        ctx.advisory.extend(reference_findings(ctx))
    return []


GROUP = RuleGroup(SUMMARIES, run)
