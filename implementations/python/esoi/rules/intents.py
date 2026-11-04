"""Rules about intents as containers: S28 and S29, and S46 (a solution's name is a name, not its handle). They apply only where the structure folder holds an ``intent.csv``.

S28 the intent folders and the link from a sub-intent to the implementation it arises from, S29 ids across the tree
and the solutions an implementation builds on. The record rules (R1 to R7, inside S26) check each record type.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from .. import intents
from ..records import FILES, MAY_BE_EMPTY
from ..tables import ids
from .base import Context, RuleGroup

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
           "solutions, implementations, metrics, ideals and problems (waive as the record id).",
}

HANDLE_STYLE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)+$")


def handle_names(ctx: Context) -> List[str]:
    """S46: a record's name that is missing, only its id again, its id plus a suffix, or kebab-case or snake_case is a handle, not a name."""
    out: List[str] = []
    registry = ctx.registry
    kinds = (("intent", [i.row for i in intents.discover(ctx.config)], "intent_id"), ("solution", registry.every_solution(), "solution_id"),
             ("implementation", registry.implementations, "implementation_id"), ("metric", registry.metrics, "metric_id"),
             ("ideal", registry.ideals, "ideal_id"), ("problem", registry.problems, "problem_id"))
    for kind, rows, key in kinds:
        for row in rows:
            ident, name = row.get(key, "").strip(), " ".join(row.get("name", "").split())
            if not ident or ctx.waived("S46", ident) or (kind == "problem" and "name" not in row):
                continue
            tail = ident.split(":", 1)[-1].lower()
            low = name.lower()
            if not name:
                why = "is missing"
            elif low in (ident.lower(), tail) or low.startswith(ident.lower() + ":") or low.startswith(ident.lower() + " ") \
                    or low.startswith(tail + ":"):
                why = "is the id again, or the id with a suffix"
            elif HANDLE_STYLE.match(name):
                why = "is written like an id (kebab-case or snake_case)"
            else:
                continue
            out.append(f"S46 {ident}: the {kind}'s name {name!r} {why}, which is a handle, not a name; next: write the human name a reader says "
                       "(`Mind`, `Card store`): it leads every generated page, diagram and table, and the id stays beside it as the handle")
    return out


def run(ctx: Context) -> List[str]:
    config = ctx.config
    if not config.intent_mode:
        return []
    bad: List[str] = []
    found = intents.discover(config)
    template = [r["field_key"] for r in ctx.template.get("intent", []) if r["group"] == "specify" and r["required"] == "yes"]
    by_id: Dict[str, intents.Intent] = {}
    for intent in found:
        where = str(intent.folder.relative_to(config.root)) + "/intent.csv"
        if intent.rows != 1:
            bad.append(f"S28 {where}: holds {intent.rows} rows; an intent has exactly one record")
        if not intent.intent_id:
            bad.append(f"S28 {where}: intent_id is empty")
            continue
        if intent.intent_id in by_id:
            bad.append(f"S28 {where}: intent_id {intent.intent_id} is already used by another intent")
        by_id[intent.intent_id] = intent
        empty = [k for k in template if not intent.row.get(k, "").strip() and k not in MAY_BE_EMPTY["intent"]]
        if empty:
            bad.append(f"S28 {intent.intent_id}: template field(s) not filled: {', '.join(empty)}"
                       + (" (the top intent is why this project exists, in its own words; the structure it applies is a "
                          "solution inside it)" if intent.is_top else ""))
        implements = intent.row.get("implements", "").strip()
        opportunities = intent.row.get("opportunities", "").strip()
        if "opportunity" in intent.row:
            bad.append(f"S28 {intent.intent_id}: {where} has the old column `opportunity`, renamed `opportunities` "
                       "(rename it in the header; the values stay)")
        if intent.is_top:
            if implements and not CROSS_PROJECT_IMPLEMENTS.match(implements):
                bad.append(f"S28 {intent.intent_id}: the top intent is a root: it implements nothing of this repository. It may "
                           "name the solution of another project's intent it implements, written @project_id/solution_id "
                           f"(optionally :implementation), and says {implements!r}")
            continue
        if intent.folder.name != intent.intent_id:
            bad.append(f"S28 {intent.intent_id}: its folder is named {intent.folder.name!r}; a sub-intent's folder is "
                       "named by its intent_id (rename the folder, or the id with every record that names it)")
        if not opportunities:
            bad.append(f"S28 {intent.intent_id}: a sub-intent states in `opportunities` the opportunities that do not emerge "
                       "directly from its parent intent or the solution it implements (risks and uncertainties alone "
                       "belong in an implementation's disadvantages or the solution's metric)")
    records = {r.get("implementation_id", ""): r for r in ctx.registry.implementations}
    for intent in found:
        if intent.is_top or not intent.intent_id:
            continue
        implements = intent.row.get("implements", "").strip()
        record = records.get(implements)
        if record is None:
            bad.append(f"S28 {intent.intent_id}: implements {implements!r}, which is not an implementation record")
            continue
        if record.get("intent_id", "") != intent.parent:
            bad.append(f"S28 {intent.intent_id}: implements {implements}, which lives in {record.get('intent_id', '')!r}, "
                       f"not in its parent intent {intent.parent!r}")
        if record.get("sub_intent", "").strip() != intent.intent_id:
            bad.append(f"S28 {implements}: the implementation a sub-intent arises from names it in `sub_intent` "
                       f"({intent.intent_id}), and this one says {record.get('sub_intent', '').strip()!r}")
    for iid, record in records.items():
        sub = record.get("sub_intent", "").strip()
        if not sub:
            continue
        if sub not in by_id:
            bad.append(f"S28 {iid}: sub_intent names {sub!r}, which is not an intent")
        elif by_id[sub].row.get("implements", "").strip() != iid:
            bad.append(f"S28 {iid}: sub_intent names {sub}, whose intent.csv implements "
                       f"{by_id[sub].row.get('implements', '').strip()!r}")

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
    if not config.is_disabled("S46"):
        ctx.advisory.extend(handle_names(ctx))
    return bad


GROUP = RuleGroup(SUMMARIES, run)
