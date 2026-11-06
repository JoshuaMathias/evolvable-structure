"""Read a project's intents, solutions and implementations from its records, and the intent map an installed package ships beside its snapshot."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi.runtime.assemble_by_name.entry_types import EntryError, Target
from esoi.runtime.implementation_selection import selection_cascade
from esoi.runtime.implementation_selection.interface import attach_evidence
from esoi.runtime.implementation_selection import selection_registry


INTENT_KEY = "@intents"   # where esoi_selection.json keeps the intent map (see ``intent_map``)


def records_root(assembler: Any) -> Optional[Path]:
    """The folder holding the package's ``esoi.toml``: the Assembler's ``records``, else a checkout beside the package."""
    if getattr(assembler, "records", None) is not None:
        return Path(assembler.records)
    for base in (Path(assembler.package_dir).parent, Path(assembler.package_dir).parent.parent):
        if (base / "esoi.toml").is_file():
            return base
    return None


def tree(root: Path) -> Tuple[Dict[str, Any], Dict[str, Dict[str, str]], List[Dict[str, str]]]:
    """``(intents by id, solutions by id, implementations)`` of the project at ``root``."""
    from esoi.structure.intent_registry import config as config_module
    from esoi.structure.intent_registry import intents as intents_module
    from esoi.structure.intent_registry.tables import read_csv
    cfg = config_module.load(root / "esoi.toml")
    found = {i.intent_id: i for i in intents_module.discover(cfg)}
    solutions: Dict[str, Dict[str, str]] = {}
    implementations: List[Dict[str, str]] = []
    for intent_id, folder in intents_module.folders(cfg):
        for row in read_csv(folder / "solutions.csv"):
            solutions[row["solution_id"]] = dict(row, intent_id=intent_id)
        implementations += read_csv(folder / "implementations.csv")
    return found, solutions, implementations


def selected_uses(solutions: Mapping[str, Mapping[str, str]], implementations: Sequence[Mapping[str, str]]) -> Dict[str, List[str]]:
    from esoi.runtime.implementation_selection.select import default_name
    from esoi.structure.intent_registry.tables import ids
    out: Dict[str, List[str]] = {}
    for sid, row in solutions.items():
        chosen = selection_registry.key(default_name(row, list(implementations)) or "")
        record = next((r for r in implementations if r.get("solution_id") == sid
                       and selection_registry.key(r["implementation_id"].split(":", 1)[-1]) == chosen), {})
        out[sid] = [t for t in ids(record.get("uses_solution_ids", "")) if t != sid]
    return out


def intent_target(intent_id: str, root: Path) -> Target:
    """The solution an intent's one line runs: its single root, else the parent solution with the arm the intent is."""
    found, solutions, implementations = tree(root)
    intent = found[intent_id]
    mine = sorted(s for s, r in solutions.items() if r["intent_id"] == intent_id)
    uses = selected_uses(solutions, implementations)
    used = {t for s in mine for t in uses[s] if t in mine}
    roots = [s for s in mine if s not in used]
    if len(roots) == 1:
        return Target(intent_id, roots[0], "intent")
    implements = (intent.row.get("implements") or "").strip()
    if implements and ":" in implements and not implements.startswith("@"):
        sid, arm = implements.split(":", 1)
        return Target(intent_id, sid, "intent", arm)
    raise EntryError(f"intent {intent_id} has {len(roots)} root solutions ({', '.join(roots) or 'none'}) and implements no local "
                     "solution, so no one solution is its entry; give it one root (metric-solution-coherence reports it)")


def intent_map(root: Path, scope: str) -> Dict[str, Any]:
    """What an installed package needs to answer ``run(<intent id>)`` without its records: for each intent its root solution (or
    the parent solution and arm it is), and the scope of each solution id. ``esoi select --snapshot`` writes it."""
    found, solutions, _ = tree(root)
    intents: Dict[str, Dict[str, str]] = {}
    for iid in sorted(found):
        try:
            where = intent_target(iid, root)
        except EntryError:
            continue
        intents[iid] = {"root": where.solution_id, "arm": where.arm}
    return {"intents": intents, "scopes": {sid: scope for sid in sorted(solutions)}}


def snapshot(config: Any) -> Dict[str, Any]:
    """``runtime.snapshot`` plus each solution's results-log evidence and, under ``"@intents"``, the intent map: what an installed package needs to answer
    ``run("<intent id>")`` without its records. ``esoi select --snapshot`` writes this."""
    out = selection_cascade.snapshot(config)
    try:
        attach_evidence(config, out)
    except Exception:
        pass   # a snapshot without evidence is still a snapshot
    try:
        if config.intent_mode:
            out[INTENT_KEY] = intent_map(config.root, config.package or "")
    except Exception:
        pass   # a snapshot without the intent map still serves every solution id
    return out


def packaged_map(assembler: Any) -> Optional[Dict[str, Any]]:
    """The intent map in the ``esoi_selection.json`` beside an installed package, or None."""
    try:
        data = json.loads((Path(assembler.package_dir) / selection_registry.SNAPSHOT_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    found = data.get(INTENT_KEY) if isinstance(data, dict) else None
    return found if isinstance(found, dict) else None
