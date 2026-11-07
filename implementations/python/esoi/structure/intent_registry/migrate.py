"""``esoi intent migrate``: move a legacy two-level repository (an ``overall`` network plus detailed records) to the
intent layout, as far as that can be done without inventing anything.

What it does, when applied:

* writes ``intent.csv`` for the top intent with its name and vision statement left empty. The top intent is why the
  project exists, in the project's own words (a product's is about the product, not about ESOI); no tool can say that, so the check
  reports both until a person fills them, and the overall network's ideals are the place to draw them from;
* moves the overall network's records into the structure folder beside the detailed ones, so the structure folder is
  the top intent. An overall solution becomes a solution with no metric command (so a specification) whose ``selected`` is its
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

from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.records import FILES
from esoi.structure.intent_registry.tables import SEP, ids, read_csv, read_header, write_csv

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


def selected_and_first(overall: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """The selected implementation of each overall solution, and its first implementation (the fallback)."""
    selected_of: Dict[str, str] = {}
    first_of: Dict[str, str] = {}
    for row in read_csv(overall / "implementations.csv"):
        if row.get("selected", "").strip().lower() in YES and row.get("solution_id") not in selected_of:
            selected_of[row["solution_id"]] = row.get("implementation_id", "")
        first_of.setdefault(row.get("solution_id", ""), row.get("implementation_id", ""))
    return selected_of, first_of


def placed_uses(structure: Path, selected_of: Dict[str, str], first_of: Dict[str, str]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """The detailed solutions each overall implementation builds on, and the overall solutions with no implementation to place them on."""
    uses: Dict[str, List[str]] = {}
    unplaced: Dict[str, List[str]] = {}   # overall solution without any implementation -> detailed solutions that served it
    for row in read_csv(structure / "solutions.csv"):
        for target in ids(row.get(RETIRED, "")):
            chosen = selected_of.get(target) or first_of.get(target, "")
            if chosen:
                uses.setdefault(chosen, []).append(row["solution_id"])
            else:
                unplaced.setdefault(target, []).append(row["solution_id"])
    return uses, unplaced


def merge_records(entity: str, filename: str, overall: Path, structure: Path, selected_of: Dict[str, str],
                  uses: Dict[str, List[str]], overall_solutions: int) -> Tuple[List[str], List[Row]]:
    """The header and rows of one record file with the overall network's records first, then the detailed ones."""
    header_o = read_header(overall / filename) if (overall / filename).is_file() else []
    header_d = read_header(structure / filename) if (structure / filename).is_file() else []
    rows = read_csv(overall / filename) + read_csv(structure / filename)
    header = union_header(header_d[:1] or header_o[:1], header_o, header_d, drop=(RETIRED,))
    if entity == "solution":
        for row in rows[:overall_solutions]:
            row["selected"] = selected_of.get(row["solution_id"], "").partition(":")[2]
        header = union_header(header, ["selected"])
    if entity == "implementation":
        for row in rows:
            if row.get("implementation_id") in uses:
                row["uses_solution_ids"] = SEP.join(dict.fromkeys(ids(row.get("uses_solution_ids", "")) + uses[row["implementation_id"]]))
        header = [c for c in union_header(header, ["uses_solution_ids"]) if c != "selected"]
    return header, rows


def manual_steps(config: Config, unplaced: Dict[str, List[str]]) -> List[str]:
    """The steps the migration leaves to a person."""
    return [
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
        "See docs/how-to/migrate-to-intents.md in the esoi repository."]


def legacy_overall(config: Config) -> Path:
    """The folder of the legacy ``overall`` network; ValueError when the repository is not legacy."""
    overall = config.root / config.overall if config.overall else None
    if config.intent_mode:
        raise ValueError(f"{config.structure_dir}/intent.csv already exists; this repository uses the intent layout")
    if overall is None or not overall.is_dir():
        raise ValueError("no legacy `overall` network is configured, so there is nothing to migrate; "
                         "`esoi init` writes the intent layout for a new repository")
    return overall


def plan(config: Config, apply: bool = False) -> Tuple[List[str], List[str]]:
    """(what was done or would be done, steps left to a person). Raises ValueError when the repository is not legacy."""
    structure = config.structure
    overall = legacy_overall(config)
    solutions_o = read_csv(overall / "solutions.csv")
    intent_id = re.sub(r"[^a-z0-9]+", "-", (config.package or config.root.name).lower()).strip("-") or "top-intent"
    intent_row = {"intent_id": intent_id, "name": "", "vision_statement": "", "opportunities": "", "implements": ""}
    done = [f"write {config.structure_dir}/intent.csv ({intent_id}: name and vision statement left empty for you)"]
    selected_of, first_of = selected_and_first(overall)
    uses, unplaced = placed_uses(structure, selected_of, first_of)
    merged: Dict[str, Tuple[List[str], List[Row]]] = {}
    for entity, (filename, _) in FILES.items():
        merged[filename] = merge_records(entity, filename, overall, structure, selected_of, uses, len(solutions_o))
        done.append(f"merge {len(merged[filename][1])} {entity} record(s) of the overall network and the detailed records into "
                    f"{config.structure_dir}/{filename}")
    if uses:
        done.append("turn overall_solution_ids into uses_solution_ids on: " + ", ".join(sorted(uses)))
    if apply:
        write_csv(structure / "intent.csv", list(intent_row), [intent_row])
        for filename, (header, rows) in merged.items():
            write_csv(structure / filename, header, rows)
    return done, manual_steps(config, unplaced)


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
