"""``esoi intent migrate``: move a legacy two-level repository (an ``overall`` network plus detailed records) to the
intent layout, as far as that can be done without inventing anything.

What it does, when applied:

* writes ``intent.csv`` for the top intent with its name and vision statement left empty. The top intent is why the
  project exists, in the project's own words (a product's is about the product, not about ESOI); no tool can say that, so the check
  reports both until a person fills them, and the overall network's ideals are the place to draw them from;
* moves the overall network's records into the structure folder beside the detailed ones, so the structure folder is
  the top intent. An overall solution becomes a solution of ``metric_kind`` ``specification`` whose ``selected`` is its
  selected implementation;
* turns each detailed solution's ``overall_solution_ids`` into ``uses_solution_ids`` on the selected implementation of
  the overall solution it served (the overall solution's chosen way builds on the detailed one), and drops the retired
  ``overall_solution_ids`` columns.

What it never does: create a sub-intent (that needs an opportunity a person names, see the migration guide), delete the
overall folder, or edit ``esoi.toml``. It prints those steps. Without ``apply`` it only reports what it would do.
Standard library only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from .config import Config
from .records import FILES
from .tables import SEP, ids, read_csv, read_header, write_csv

Row = Dict[str, str]
YES = {"yes", "y", "true", "1", "selected"}
RETIRED = "overall_solution_ids"


def union_header(*headers: List[str], drop: Tuple[str, ...] = ()) -> List[str]:
    seen: Dict[str, None] = {}
    for header in headers:
        for column in header:
            if column not in drop:
                seen.setdefault(column, None)
    return list(seen)


def plan(config: Config, apply: bool = False) -> Tuple[List[str], List[str]]:
    """(what was done or would be done, steps left to a person). Raises ValueError when the repository is not legacy."""
    structure = config.structure
    overall = config.root / config.overall if config.overall else None
    if config.intent_mode:
        raise ValueError(f"{config.structure_dir}/intent.csv already exists; this repository uses the intent layout")
    if overall is None or not overall.is_dir():
        raise ValueError("no legacy `overall` network is configured, so there is nothing to migrate; "
                         "`esoi init` writes the intent layout for a new repository")
    done: List[str] = []
    solutions_o = read_csv(overall / "solutions.csv")
    intent_id = re.sub(r"[^a-z0-9]+", "-", (config.package or config.root.name).lower()).strip("-") or "top-intent"
    intent_row = {"intent_id": intent_id, "name": "", "vision_statement": "", "opportunities": "", "implements": ""}
    done.append(f"write {config.structure_dir}/intent.csv ({intent_id}: name and vision statement left empty for you)")

    selected_of: Dict[str, str] = {}
    for row in read_csv(overall / "implementations.csv"):
        if row.get("selected", "").strip().lower() in YES and row.get("solution_id") not in selected_of:
            selected_of[row["solution_id"]] = row.get("implementation_id", "")
    first_of: Dict[str, str] = {}
    for row in read_csv(overall / "implementations.csv"):
        first_of.setdefault(row.get("solution_id", ""), row.get("implementation_id", ""))

    uses: Dict[str, List[str]] = {}
    unplaced: Dict[str, List[str]] = {}   # overall solution without any implementation -> detailed solutions that served it
    for row in read_csv(structure / "solutions.csv"):
        for target in ids(row.get(RETIRED, "")):
            chosen = selected_of.get(target) or first_of.get(target, "")
            if chosen:
                uses.setdefault(chosen, []).append(row["solution_id"])
            else:
                unplaced.setdefault(target, []).append(row["solution_id"])

    merged: Dict[str, Tuple[List[str], List[Row]]] = {}
    for entity, (filename, _) in FILES.items():
        header_o = read_header(overall / filename) if (overall / filename).is_file() else []
        header_d = read_header(structure / filename) if (structure / filename).is_file() else []
        rows = read_csv(overall / filename) + read_csv(structure / filename)
        header = union_header(header_d[:1] or header_o[:1], header_o, header_d, drop=(RETIRED,))
        if entity == "solution":
            for row in rows[: len(solutions_o)]:
                row["metric_kind"] = "specification"
                row["selected"] = selected_of.get(row["solution_id"], "").partition(":")[2]
            header = union_header(header, ["selected", "metric_kind"])
        if entity == "implementation":
            for row in rows:
                if row.get("implementation_id") in uses:
                    row["uses_solution_ids"] = SEP.join(dict.fromkeys(ids(row.get("uses_solution_ids", "")) + uses[row["implementation_id"]]))
            header = union_header(header, ["uses_solution_ids"])
            header = [c for c in header if c != "selected"]
        merged[filename] = (header, rows)
        done.append(f"merge {len(rows)} {entity} record(s) of the overall network and the detailed records into "
                    f"{config.structure_dir}/{filename}")
    if uses:
        done.append("turn overall_solution_ids into uses_solution_ids on: " + ", ".join(sorted(uses)))
    if apply:
        write_csv(structure / "intent.csv", list(intent_row), [intent_row])
        for filename, (header, rows) in merged.items():
            write_csv(structure / filename, header, rows)
    manual = [
        f"The overall solution {target} has no implementation, so {', '.join(sorted(users))} could not be recorded as "
        "solutions its implementation builds on and the dropped overall_solution_ids link is lost: add an implementation "
        f"of {target} and list them in its uses_solution_ids." for target, users in sorted(unplaced.items())] + [
        f"Fill {config.structure_dir}/intent.csv: the name and the vision statement (present tense) say why this project "
        "exists, in its own words, and are not about ESOI. The check reports both until you do.",
        "The evolvable structure this project applies is a solution inside the top intent; its implementation may use the "
        "esoi solutions (uses_solution_ids, @project_id/solution_id for another project).",
        f"Delete {config.overall}/ and remove `overall` from the configuration once the merged records check.",
        "Decide which, if any, implementations become sub-intents: only one that brings insights on opportunities that "
        "do not emerge from its parent intent or the solution it implements. Move its solutions into a subfolder with "
        "its own intent.csv (implements, opportunities) and name it in the implementation's sub_intent.",
        "Run `esoi check --write-docs` and `esoi tracker build`; fix what they name.",
        "See docs/guides/migrate-to-intents.md in the esoi repository."]
    return done, manual


def run_cli(config: Config, apply: bool, say=print) -> int:
    try:
        done, manual = plan(config, apply)
    except ValueError as exc:
        say(f"esoi: {exc}")
        return 2
    say("done:" if apply else "would do (add --apply to write):")
    for line in done:
        say(f"  {line}")
    say("left to you:")
    for line in manual:
        say(f"  {line}")
    return 0
