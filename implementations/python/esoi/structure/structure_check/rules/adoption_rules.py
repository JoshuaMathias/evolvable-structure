"""S53: a repository that adopts solutions from a library keeps the library's jobs as references and its own jobs as full records. Advisory: informs, never fails.

The records and the reasons are in ``docs/explanation/adopting-solutions-from-a-library.md``. A row of ``solutions.csv`` with an ``adopts`` cell
(``@library/solution_id``) is ADOPTED; one with a ``specializes`` cell is SPECIALIZED; any other is the repository's OWN. The library is the one
``[adopts.<library>] repo`` names. S53 informs of

* a reference that does not resolve (no such library configured, the library cannot be read, it has no such solution);
* an adopted row that carries what the library already says (a description, purpose, approach, scope, milestones, problems, ideals, role);
* an own solution whose purpose and description say the same job as a solution of a configured library (a person decides; the finding asks);
* an arm under an adopted solution whose code does not declare ``@implementation("<the library's solution id>", ...)``, so the library's
  interface does not reach it.

A waiver excuses one key: the local solution id (or ``own+@library/solution`` for one overlap).
"""
from __future__ import annotations

import ast
from typing import Dict, List, Optional

from esoi.structure.library_adoption import resolve
from esoi.structure.intent_registry.parsed_source import nodes_of, tree_of
from esoi.structure.structure_check.rules.base import Context, RuleGroup
from esoi.structure.structure_quality.overlap import OVERLAP, OVERLAP_WORDS, content

SUMMARIES = {
    "S53": "Advisory adoption: a reference `adopts` or `specializes` (`@library/solution_id`, library named in `[adopts.<library>]`) resolves to a "
           "solution of a readable library; an adopted row holds no description, purpose, approach, scope, milestones, problems, ideals or role of its "
           "own (it does take the application's own arms, metrics, ports and components, and its id resolves like any solution's); an own solution does not say the same job as a library solution; an arm under an adopted solution declares the library's solution "
           "id (waive as the local solution id, or own+@library/solution_id for one overlap).",
}

#: What the library already says about an adopted solution: the application records none of it.
INHERITED = ("description", "purpose", "approach", "out_of_scope", "milestones", "knowledge", "measures_of_success",
             "problem_ids", "ideal_ids", "delegates_to", "change_driver")


def restated(ctx: Context) -> List[str]:
    """An adopted row that carries a field the library defines."""
    out: List[str] = []
    for row in ctx.registry.adopted:
        sid = row.get("solution_id", "")
        filled = [k for k in INHERITED if (row.get(k) or "").strip()]
        if filled and not ctx.waived("S53", sid):
            out.append(f"S53 {sid}: it adopts {row.get('adopts', '').strip()} but records {', '.join(filled)} of its own, which the library already says; "
                       "next: empty those cells (the library's words are shown on the page), or make this a specialized solution (`specializes`) "
                       "if it is a different job")
    return out


def overlapping(ctx: Context, libraries: resolve.Libraries) -> List[str]:
    """An own solution whose purpose and description share most of their content words with a library solution."""
    out: List[str] = []
    for lib in libraries.every():
        if lib.registry is None:
            continue
        theirs = [(r, content(" ".join([r.get("purpose", ""), r.get("description", "")]))) for r in lib.registry.every_solution()]
        for own in ctx.registry.every_solution():
            sid = own.get("solution_id", "")
            if (own.get("specializes") or "").strip() or ctx.waived("S53", sid):
                continue
            words = content(" ".join([own.get("purpose", ""), own.get("description", "")]))
            for row, other in theirs:
                shared = words & other
                key = f"{sid}+@{lib.name}/{row.get('solution_id', '')}"
                if len(shared) >= OVERLAP_WORDS and len(shared) / max(1, len(words | other)) >= OVERLAP and not ctx.waived("S53", key):
                    out.append(f"S53 {sid}: its purpose and description say much the same job as {row.get('solution_id', '')} of the library {lib.name} "
                               f"({', '.join(sorted(shared)[:6])}); next: adopt it (`adopts` = @{lib.name}/{row.get('solution_id', '')}) and move your "
                               "code in as an arm, specialize it (`specializes`) if it needs this application's data, or waive it with the reason the job differs")
    return out


def declared_for(path_text: str, ctx: Context) -> Optional[set]:
    """The solution ids the module at ``path_text`` declares an implementation of with ``@implementation("<id>", ...)``; None when it cannot be read."""
    path = ctx.root / path_text.partition("::")[0].strip()
    tree = tree_of(path)
    if tree is None:
        return None
    found = set()
    for node in nodes_of(tree):
        for deco in getattr(node, "decorator_list", []):
            if isinstance(deco, ast.Call) and getattr(deco.func, "id", getattr(deco.func, "attr", "")) == "implementation" \
                    and deco.args and isinstance(deco.args[0], ast.Constant):
                found.add(str(deco.args[0].value))
    return found


def arms(ctx: Context, refs: Dict[str, resolve.Reference]) -> List[str]:
    """An arm with code under an adopted solution that does not declare the library's solution id."""
    out: List[str] = []
    for impl in ctx.registry.implementations:
        ref = refs.get(impl.get("solution_id", ""))
        path = (impl.get("filepath") or "").strip()
        if ref is None or not path or ctx.waived("S53", impl.get("implementation_id", "")):
            continue
        declared = declared_for(path, ctx)
        if declared is None or ref.solution_id not in declared:
            out.append(f"S53 {impl.get('implementation_id', '')}: it is an arm of the adopted solution {ref.local_id}, but {path.partition('::')[0]} does not "
                       f"declare @implementation(\"{ref.solution_id}\", ...), so the interface of {ref.solution_id} in the library {ref.library} does not "
                       "reach it; next: declare the library's solution id and follow its interface")
    return out


def run(ctx: Context) -> List[str]:
    refs, malformed = resolve.references(ctx.config, ctx.registry)
    if not refs and not malformed and not ctx.config.adopts:
        return []
    libraries = resolve.Libraries(ctx.config)
    found = [f"S53 {line}; next: write `@library/solution_id`, name the library under `[adopts.<library>]` in the configuration, and "
             "check the solution id" for line in resolve.unresolved(ctx.config, ctx.registry) if not ctx.waived("S53", line.split(":", 1)[0].split(" ")[0])]
    found += restated(ctx) + overlapping(ctx, libraries)
    found += arms(ctx, {r.local_id: r for r in refs if r.kind == "adopts"})
    ctx.advisory.extend(found)
    return []


GROUP = RuleGroup(SUMMARIES, run)
