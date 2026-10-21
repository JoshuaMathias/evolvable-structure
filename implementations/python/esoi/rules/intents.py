"""Rules about intents as containers: S28 and S29. They apply only where the structure folder holds an ``intent.csv``.

S28 the intent folders and the link from a sub-intent to the implementation it arises from, S29 ids across the tree
and the solutions an implementation builds on. The record rules (R1 to R5, inside S26) check each record type.
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

SUMMARIES = {
    "S28": "Each intent folder has one intent.csv row with a unique intent_id and every field of the intent template; the "
           "top intent leaves implements empty; a sub-intent is in a folder named by its intent_id, "
           "names, in implements, an implementation of its parent intent, that implementation names it back in "
           "sub_intent, and the sub-intent states the opportunities that justify it.",
    "S29": "A record id is used once across the whole tree (also across record types and intents), and every "
           "uses_solution_ids entry names a solution somewhere in the tree other than the implementation's own, or is written "
           "@project_id/solution_id for a solution of another project (listed in the local ESOI index, not read here).",
}


def run(ctx: Context) -> List[str]:
    config = ctx.config
    if not config.intent_mode:
        return []
    bad: List[str] = []
    found = intents.discover(config)
    template = [r["field_key"] for r in ctx.template.get("intent", []) if r["group"] == "specify"]
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
            if implements:
                bad.append(f"S28 {intent.intent_id}: the top intent is no implementation of anything; leave implements "
                           "empty")
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
    return bad


GROUP = RuleGroup(SUMMARIES, run)
