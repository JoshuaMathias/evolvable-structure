"""The first-stage check of the one line (rule S37): call every id of a project with its example, offline, and report one outcome per id."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from esoi.runtime.assemble_by_name.entry import describe, targets
from esoi.runtime.assemble_by_name.entry_outcome import classify
from esoi.runtime.assemble_by_name.entry_types import EntryError
from esoi.runtime.assemble_by_name.offline_guard import offline_guard
from esoi.runtime.assemble_by_name.project_runner import project_runner


def check_entries(root: Path) -> List[Dict[str, Any]]:
    """Call every id of the project's one line with its example under ``environ={}`` and no network: one row per id with
    ``outcome``: ok (a value of the declared kind came back), pending-key, pending-install or pending-network (it named the key, install or network need that
    would let it run), needs-option (it asks the caller for an option or an object: no default fills the seat), load-error (an
    arm cannot be loaded), live-attempt (it reached for the network or a program nothing declared), no-entry (no interface,
    kind, entry or example) or fail (it raised anything else). Only the first three answer."""
    os.environ["ESOI_IN_ENTRY_CHECK"] = "1"   # an entry that runs `esoi check` does not start this check again (rule S37)
    offline_guard()
    run_one = project_runner(root)
    out: List[Dict[str, Any]] = []
    for target, level, kind, example in targets(run_one.assembler):
        row: Dict[str, Any] = {"id": target, "level": level, "kind": kind, "reasons": []}
        if not kind or example is None:
            row.update(outcome="no-entry", detail="declare kind=, entry= and example= on its @solution" if not kind else "no example input")
        else:
            try:
                value = run_one(target, example, environ={})
                if kind == "store" and value is None:
                    raise EntryError("a store's query returned None")
                row.update(outcome="ok", detail=describe(value))
            except Exception as error:
                outcome, detail, reasons = classify(error)
                row.update(outcome=outcome, detail=detail, reasons=[vars(r) for r in reasons])
        out.append(row)
    return out
