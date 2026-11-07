"""Read the needs the code declares for each recorded arm, compare them with the records, and write ``uses_solution_ids`` from them."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

from esoi.structure.intent_registry.assembly_errors import AssemblyError
from esoi.runtime.assemble_by_name.dependency_graph import problems
from esoi.structure.intent_registry import intents
from esoi.structure.intent_registry.tables import read_csv, read_header, write_csv


def declared_needs(assembler: Any, implementations: Sequence[Mapping[str, str]]) -> Tuple[Dict[str, Set[str]], List[str]]:
    """``({implementation_id: {solution ids it needs}}, findings)`` read from the constructor parameters of each recorded
    implementation. An arm that cannot be loaded (an optional dependency missing) is a finding, not an exception, and is
    left out of the first. A recorded alternative that names no code (an empty ``filepath``) and has no declaration is a described
    alternative ("no arm yet"): it has no needs, is left out of the first and is not a finding; its recorded
    ``uses_solution_ids`` is kept as written."""
    found: Dict[str, Set[str]] = {}
    findings: List[str] = []
    for row in implementations:
        iid = row["implementation_id"]
        sid, name = iid.split(":", 1) if ":" in iid else (iid, "")
        try:
            found[iid] = set(assembler.needs_of(assembler.load(sid, name)).values())
        except AssemblyError as error:
            if not (row.get("filepath") or "").strip():
                continue    # a described alternative names no code and no declaration: it has no needs and nothing to load
            findings.append(f"{iid}: cannot be loaded to read its needs ({error})")
    return found, findings


def uses_problems(assembler: Any, folder: Path) -> List[str]:
    """Every disagreement between the records in ``folder`` and the needs the code declares. Empty means sound."""
    rows = intents.read_tree(Path(folder), "implementations.csv")
    needs, findings = declared_needs(assembler, rows)
    return findings + problems(intents.read_tree(Path(folder), "solutions.csv"), rows, needs)


def sync_uses(assembler: Any, folder: Path) -> List[str]:
    """Write the ``uses_solution_ids`` column of ``implementations.csv`` in ``folder`` from the constructor parameters.
    Records beside the code are read and written where they live. A row whose arm cannot be loaded keeps its cell and is returned as a finding."""
    held = {each: read_csv(each / "implementations.csv") for each in intents.tree_folders(Path(folder))}
    needs, findings = declared_needs(assembler, [row for rows in held.values() for row in rows])
    for each, rows in held.items():
        for row in rows:
            if row["implementation_id"] in needs:
                row["uses_solution_ids"] = ";".join(sorted(needs[row["implementation_id"]]))
        if (each / "implementations.csv").is_file():
            write_csv(each / "implementations.csv", read_header(each / "implementations.csv"), rows)
    return findings
