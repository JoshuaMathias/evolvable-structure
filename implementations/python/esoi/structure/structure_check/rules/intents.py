"""Rules about intents as containers: S28 and S29, S46 (a name is a name, not a handle), S48 and S49 (the role of a solution against its siblings). They apply only where the structure folder holds an ``intent.csv``.

S28 the intent folders and the link from a sub-intent to the implementation it arises from, S29 ids across the tree
and the solutions an implementation builds on. The record rules (R1 to R7, inside S26) check each record type.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.records import FILES, MAY_BE_EMPTY
from esoi.structure.intent_registry.registry import adopts
from esoi.structure.intent_registry.tables import ids
from esoi.structure.structure_check.rules.base import Context, RuleGroup
from esoi.structure.structure_quality.interface import ARMS_SHARE_LITTLE, OVERLAP, OVERLAP_WORDS, content, mean_overlap

CROSS_PROJECT = re.compile(r"^@[\w.-]+/[\w.-]+$")
CROSS_PROJECT_IMPLEMENTS = re.compile(r"^@[\w.-]+/[\w.-]+(:[\w.-]+)?$")

SUMMARIES = {
    "S28": "Each intent folder has one intent.csv row with a unique intent_id and every field of the intent template; the "
           "top intent is a root (implements is empty, or names another project's solution as @project_id/solution_id); every intent below it is an implementation of a solution of its parent: a sub-intent is in a folder named by its intent_id, "
           "names, in implements, an implementation of its parent intent, that implementation names it back in "
           "sub_intent, and the sub-intent states the opportunities that justify it.",
    "S29": "A record id is used once across the whole tree (also across record types and intents), and every "
           "uses_solution_ids entry names a solution somewhere in the tree other than the implementation's own, or is written "
           "@project_id/solution_id for a solution of another project (listed in the local ESOI index, not read here).",
    "S46": "Advisory: a record's `name` is the human-readable label that leads every generated page, not its handle: a name that is missing, equals its "
           "own id (or the arm part of it), is the id with a suffix or after a colon, or is written kebab-case or snake_case is informed, for intents, "
           "solutions, implementations, metrics, ideals, problems and components (waive as the record id).",
    "S48": "Advisory role scoping: a solution with siblings states what it is not responsible for (out_of_scope) and who owns that (`delegates_to` "
           "or a named sibling; `none` says nothing is delegated), two siblings do not overlap strongly in purpose and description, and a container names the `change_driver` that moves its "
           "metric (waive as the solution id, or a+b for a pair).",
    "S49": "Advisory review prompt: a solution with three or more implementations whose descriptions share little is read for one purpose and one level "
           "of specificity (a solution holds alternatives of the same job); a prompt, never a verdict (waive as the solution id).",
}

CHANGE_DRIVERS = "outside systems, the system's own data model or code, ML task accuracy, alignment with humans or policies"


def named_in(text: str, row) -> bool:
    low = (text or "").lower()
    for ident in (row.get("solution_id", ""), " ".join(row.get("name", "").split())):
        if ident and re.search(r"(?<![\w-])" + re.escape(ident.lower()) + r"(?![\w-])", low):
            return True
    return False


def exclusion_problems(sid: str, intent: str, row, siblings: list, scoped: bool) -> List[str]:
    """S48 for a solution that states no exclusions, or states them without naming who owns them."""
    scope, delegates = (row.get("out_of_scope") or "").strip(), ids(row.get("delegates_to", ""))
    if siblings and not scope:
        return [f"S48 {sid}: it has {len(siblings)} sibling solution(s) in {intent} but states no exclusions (out_of_scope is empty); next: "
                "say what it is NOT responsible for and which sibling owns that (name the owner in `delegates_to`), or why nothing is excluded"]
    if scoped and siblings and scope and not delegates and not any(named_in(scope, s) for s in siblings):
        return [f"S48 {sid}: out_of_scope says what it is not responsible for but not who owns it (it names no sibling); next: name the "
                "owning sibling in `delegates_to`, or record that nothing owns it, which is a gap in the hierarchy"]
    return []


def row_role_problems(ctx: Context, row, group: list, intent: str, scoped: bool, known: set, containers: set) -> List[str]:
    """S48 for one solution: exclusions stated, an owner named for them, delegates that exist, a change driver for a container."""
    sid = row.get("solution_id", "")
    if not sid or ctx.waived("S48", sid) or adopts(row):   # the library states an adopted solution's role
        return []
    out = exclusion_problems(sid, intent, row, [s for s in group if s is not row], scoped)
    out += [f"S48 {sid}: delegates_to names {target}, which is no solution; next: name the sibling that owns that part of the job"
            for target in ids(row.get("delegates_to", "")) if target != "none" and target not in known]
    if sid in containers and not (row.get("change_driver") or "").strip():
        out.append(f"S48 {sid}: it is a container (an implementation of it is a sub-intent) but names no change_driver; next: say what kind "
                   f"of change moves its metric: {CHANGE_DRIVERS}")
    return out


def overlap_problems(ctx: Context, group: list) -> List[str]:
    """S48 for each pair of sibling solutions whose purpose and description texts overlap strongly."""
    out: List[str] = []
    words = [(row, content(" ".join([row.get("purpose", ""), row.get("description", "")]))) for row in group if not adopts(row)]
    for i, (a, wa) in enumerate(words):
        for b, wb in words[i + 1:]:
            shared = wa & wb
            if len(shared) >= OVERLAP_WORDS and len(shared) / max(1, len(wa | wb)) >= OVERLAP:
                ia, ib = a.get("solution_id", ""), b.get("solution_id", "")
                if ctx.waived("S48", ia) or ctx.waived("S48", ib) or ctx.waived("S48", f"{ia}+{ib}"):
                    continue
                out.append(f"S48 {ia}+{ib}: their purpose and description texts overlap strongly ({', '.join(sorted(shared)[:6])}); next: merge them, "
                           "split the job so each owns one role, or let one delegate to the other (delegates_to). Also ask whether either exists only "
                           "for a capability the other, or the world, already provides")
    return out


def role_scope(ctx: Context) -> List[str]:
    """S48: the role of each solution against its siblings: what it is not responsible for and who owns that, overlap of purposes, and the
    kind of change that moves a container's metric. Informing only: the texts are judged by people, these are the prompts."""
    out: List[str] = []
    rows = ctx.registry.every_solution()
    known, containers, scoped = role_facts(ctx, rows)
    for intent, group in solutions_by_intent(rows).items():
        if not scoped and len(group) > 1 and intent and not ctx.waived("S48", intent):
            out.append(unscoped_line(intent, len(group)))
        for row in group:
            out += row_role_problems(ctx, row, group, intent, scoped, known, containers)
        out += overlap_problems(ctx, group)
    return out


def role_facts(ctx: Context, rows: list) -> tuple:
    """The solution ids, the ids of containers (an implementation of them is a sub-intent), and whether the repository records ``delegates_to``."""
    known = {r.get("solution_id", "") for r in rows}
    containers = {r.get("solution_id", "") for r in ctx.registry.implementations if (r.get("sub_intent") or "").strip()}
    scoped = any("delegates_to" in row for row in rows)   # a repository that has the column records who owns what each solution excludes
    return known, containers, scoped


def solutions_by_intent(rows: list) -> Dict[str, list]:
    """The solution rows grouped by the intent that holds them."""
    by_intent: Dict[str, list] = defaultdict(list)
    for row in rows:
        by_intent[row.get("intent_id", "")].append(row)
    return by_intent


def unscoped_line(intent: str, count: int) -> str:
    """The S48 line for an intent with sibling solutions in a repository that records no ``delegates_to`` at all."""
    return (f"S48 {intent}: its {count} solutions have siblings, but no solution records `delegates_to` (who owns what each one is not "
            "responsible for); next: add the `delegates_to` and `change_driver` columns to solutions.csv and scope each role "
            "(docs/how-to/scope-the-role-of-a-solution.md)")


def review_prompts(ctx: Context) -> List[str]:
    """S49: a review prompt, not a verdict, for each solution with three or more implementations whose descriptions share little: read the list for
    one purpose and one level of specificity (a general solution's arms do the same job)."""
    out: List[str] = []
    by_solution: Dict[str, list] = defaultdict(list)
    for impl in ctx.registry.implementations:
        by_solution[impl.get("solution_id", "")].append(impl)
    for sid, impls in sorted(by_solution.items()):
        if len(impls) < 3 or not sid or ctx.waived("S49", sid):
            continue
        mean = mean_overlap(" ".join([i.get("name", ""), i.get("description", "")]) for i in impls)
        if mean < ARMS_SHARE_LITTLE:
            names = "; ".join(" ".join(i.get("name", "").split()) or i.get("implementation_id", "") for i in impls[:8])
            out.append(f"S49 {sid}: review prompt: read its {len(impls)} implementations for one purpose and one level of specificity ({names}). "
                       "A solution holds alternatives that do the SAME job; arms that serve different purposes mean it is mis-defined: split by purpose "
                       "(a general solution with general arms, specific solutions nested beneath or composed by it) and name the general alternatives missing")
    return out


HANDLE_STYLE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)+$")


def handle_reason(ident: str, name: str) -> str:
    """Why a name is a handle (missing, the id again or with a suffix, written like an id), or an empty string when it is a name."""
    tail = ident.split(":", 1)[-1].lower()
    low = name.lower()
    if not name:
        return "is missing"
    if low in (ident.lower(), tail) or low.startswith(ident.lower() + ":") or low.startswith(ident.lower() + " (") \
            or low.startswith(tail + ":"):
        return "is the id again, or the id with a suffix"
    if HANDLE_STYLE.match(name):
        return "is written like an id (kebab-case or snake_case)"
    return ""


def handle_names(ctx: Context) -> List[str]:
    """S46: a record's name that is missing, only its id again, its id plus a suffix, or kebab-case or snake_case is a handle, not a name."""
    out: List[str] = []
    registry = ctx.registry
    kinds = (("intent", [i.row for i in intents.discover(ctx.config)], "intent_id"), ("solution", registry.authored(), "solution_id"),
             ("implementation", registry.implementations, "implementation_id"), ("metric", registry.metrics, "metric_id"),
             ("ideal", registry.ideals, "ideal_id"), ("problem", registry.problems, "problem_id"),
             ("component", registry.components, "component_id"))
    for kind, rows, key in kinds:
        for row in rows:
            ident, name = row.get(key, "").strip(), " ".join(row.get("name", "").split())
            if not ident or ctx.waived("S46", ident):
                continue
            why = handle_reason(ident, name)
            if why:
                out.append(f"S46 {ident}: the {kind}'s name {name!r} {why}, which is a handle, not a name; next: write the human name a reader says "
                           "(`Mind`, `Card store`): it leads every generated page, diagram and table, and the id stays beside it as the handle")
    return out


def sub_intent_shape_problems(intent) -> List[str]:
    """S28 for a sub-intent: its folder is named by its id and it states its own opportunities."""
    bad: List[str] = []
    if intent.folder.name != intent.intent_id:
        bad.append(f"S28 {intent.intent_id}: its folder is named {intent.folder.name!r}; a sub-intent's folder is "
                   "named by its intent_id (rename the folder, or the id with every record that names it)")
    if not intent.row.get("opportunities", "").strip():
        bad.append(f"S28 {intent.intent_id}: a sub-intent states in `opportunities` the opportunities that do not emerge "
                   "directly from its parent intent or the solution it implements (risks and uncertainties alone "
                   "belong in an implementation's disadvantages or the solution's metric)")
    return bad


def field_problems(intent, template: List[str], where: str) -> List[str]:
    """S28 for the fields of one intent record: template fields left empty and the old ``opportunity`` column."""
    bad: List[str] = []
    empty = [k for k in template if not intent.row.get(k, "").strip() and k not in MAY_BE_EMPTY["intent"]]
    if empty:
        bad.append(f"S28 {intent.intent_id}: template field(s) not filled: {', '.join(empty)}"
                   + (" (the top intent is why this project exists, in its own words; the structure it applies is a "
                      "solution inside it)" if intent.is_top else ""))
    if "opportunity" in intent.row:
        bad.append(f"S28 {intent.intent_id}: {where} has the old column `opportunity`, renamed `opportunities` "
                   "(rename it in the header; the values stay)")
    return bad


def intent_problems(ctx: Context, intent, template: List[str], by_id: Dict[str, "intents.Intent"]) -> List[str]:
    """S28 for one intent folder: one record, an id used once, the template filled, `implements` and `opportunities` as its level needs."""
    bad: List[str] = []
    where = str(intent.folder.relative_to(ctx.config.root)) + "/intent.csv"
    if intent.rows != 1:
        bad.append(f"S28 {where}: holds {intent.rows} rows; an intent has exactly one record")
    if not intent.intent_id:
        return bad + [f"S28 {where}: intent_id is empty"]
    if intent.intent_id in by_id:
        bad.append(f"S28 {where}: intent_id {intent.intent_id} is already used by another intent")
    by_id[intent.intent_id] = intent
    bad += field_problems(intent, template, where)
    implements = intent.row.get("implements", "").strip()
    if intent.is_top:
        if implements and not CROSS_PROJECT_IMPLEMENTS.match(implements):
            bad.append(f"S28 {intent.intent_id}: the top intent is a root: it implements nothing of this repository. It may "
                       "name the solution of another project's intent it implements, written @project_id/solution_id "
                       f"(optionally :implementation), and says {implements!r}")
        return bad
    return bad + sub_intent_shape_problems(intent)


def implements_problems(intent, records: Dict[str, Dict[str, str]]) -> List[str]:
    """S28 for one sub-intent: the implementation it says it arises from exists, lives in its parent, and names it back."""
    implements = intent.row.get("implements", "").strip()
    record = records.get(implements)
    if record is None:
        return [f"S28 {intent.intent_id}: implements {implements!r}, which is not an implementation record"]
    bad: List[str] = []
    if record.get("intent_id", "") != intent.parent:
        bad.append(f"S28 {intent.intent_id}: implements {implements}, which lives in {record.get('intent_id', '')!r}, "
                   f"not in its parent intent {intent.parent!r}")
    if record.get("sub_intent", "").strip() != intent.intent_id:
        bad.append(f"S28 {implements}: the implementation a sub-intent arises from names it in `sub_intent` "
                   f"({intent.intent_id}), and this one says {record.get('sub_intent', '').strip()!r}")
    return bad


def sub_intent_link_problems(found: list, records: Dict[str, Dict[str, str]], by_id) -> List[str]:
    """S28 for the link between a sub-intent and the implementation it arises from, in both directions."""
    bad: List[str] = []
    for intent in found:
        if not intent.is_top and intent.intent_id:
            bad += implements_problems(intent, records)
    for iid, record in records.items():
        sub = record.get("sub_intent", "").strip()
        if not sub:
            continue
        if sub not in by_id:
            bad.append(f"S28 {iid}: sub_intent names {sub!r}, which is not an intent")
        elif by_id[sub].row.get("implements", "").strip() != iid:
            bad.append(f"S28 {iid}: sub_intent names {sub}, whose intent.csv implements "
                       f"{by_id[sub].row.get('implements', '').strip()!r}")
    return bad


def shared_id_problems(ctx: Context, by_id) -> List[str]:
    """S29: an id is used by one kind of record, and no intent id is also a record id."""
    bad: List[str] = []
    users: Dict[str, List[str]] = defaultdict(list)
    for entity, (_, key) in FILES.items():
        rows = {"problem": ctx.registry.problems, "ideal": ctx.registry.ideals, "solution": ctx.registry.every_solution(),
                "implementation": ctx.registry.implementations, "metric": ctx.registry.metrics}[entity]
        for row in rows:
            if row.get(key):
                users[row[key]].append(f"{entity} in {row.get('intent_id', '')}")
    for rid, where in sorted(users.items()):
        kinds = {w.split(" in ")[0] for w in where}
        if len(kinds) > 1:
            bad.append(f"S29 {rid}: used by more than one kind of record ({'; '.join(where)}); ids are unique across the tree")
    for rid in sorted(by_id):
        if rid in users:
            bad.append(f"S29 {rid}: an intent id is also the id of a record ({'; '.join(users[rid])})")
    return bad


def uses_problems(ctx: Context, records: Dict[str, Dict[str, str]]) -> List[str]:
    """S29 for each solution an implementation builds on that is malformed, unknown or its own."""
    bad: List[str] = []
    solutions = {r.get("solution_id", "") for r in ctx.registry.every_solution()}
    for iid, record in records.items():
        for target in ids(record.get("uses_solution_ids", "")):
            if target.startswith("@"):
                if not CROSS_PROJECT.match(target):
                    bad.append(f"S29 {iid}: uses_solution_ids entry {target!r} is not written @project_id/solution_id")
            elif target not in solutions:
                bad.append(f"S29 {iid}: uses_solution_ids names {target!r}, which is not a solution in the tree")
            elif target == record.get("solution_id"):
                bad.append(f"S29 {iid}: builds on its own solution {target}")
    return bad


def run(ctx: Context) -> List[str]:
    config = ctx.config
    if not config.intent_mode:
        return []
    found = intents.discover(config)
    template = [r["field_key"] for r in ctx.template.get("intent", []) if r["group"] == "specify" and r["required"] == "yes"]
    by_id: Dict[str, intents.Intent] = {}
    bad: List[str] = []
    for intent in found:
        bad += intent_problems(ctx, intent, template, by_id)
    records = {r.get("implementation_id", ""): r for r in ctx.registry.implementations}
    bad += sub_intent_link_problems(found, records, by_id)
    bad += shared_id_problems(ctx, by_id)
    bad += uses_problems(ctx, records)
    if not config.is_disabled("S46"):
        ctx.advisory.extend(handle_names(ctx))
    if not config.is_disabled("S48"):
        ctx.advisory.extend(role_scope(ctx))
    if not config.is_disabled("S49"):
        ctx.advisory.extend(review_prompts(ctx))
    return bad


GROUP = RuleGroup(SUMMARIES, run)
