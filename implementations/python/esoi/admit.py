"""``esoi admit``: take a newly found technology into the structure, or record a justified change to the structure.

Two moves, both written to the records and never to the code:

* ``esoi admit <solution> <name> --why TEXT [--uses <solution>]... [--filepath FILE]`` registers the technology as an
  implementation of a solution that already exists. With no code yet it is a rival with no arm: the row has an empty ``filepath``,
  nothing runs, and the leaderboard lists it as not measured so the gap stays visible. When its code is declared
  (``@implementation``), ``esoi records sync`` fills the ``filepath`` and the row becomes an arm. ``--uses`` names the solutions a
  composite arm is built over (a reranker as a stage of a search arm).
* ``esoi admit <solution> --changed WHAT --why TEXT`` records a change to the specification itself (an interface widened, two
  solutions merged, one split, the hierarchy reorganized) as a dated line in the solution's ``knowledge``, so the reason outlives the
  commit that made the change.

The decision steps and three worked examples are in docs/how-to/admit-a-technology-that-does-not-fit.md.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import List, Optional, Sequence

from . import declarations
from .config import Config
from .records import TEMPLATE_DATA, load_template
from .registry import Registry
from .tables import ids, read_csv, write_csv


def slug(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "-", text.lower()).strip("-")


def solution_folder(config: Config, registry: Registry, solution_id: str) -> Path:
    if solution_id not in {r.get("solution_id", "") for r in registry.every_solution()}:
        raise ValueError(f"no solution {solution_id!r} in the records; a technology that fits no solution needs a new one "
                         f"(`esoi new solution <id>`), recorded with `esoi admit <id> --changed ... --why ...`")
    return declarations.holder(config, config.structure, "solutions.csv", "solution_id", solution_id)


def admit(config: Config, registry: Registry, solution_id: str, name: str, why: str, uses: Sequence[str] = (),
          filepath: str = "") -> List[str]:
    """Add the implementation row ``<solution_id>:<slug of name>`` and list it in the solution's ``implementations``. Returns the
    changes, one line each. Raises ``ValueError`` when the solution is unknown, the technology is already there, the reason is empty,
    or a used solution does not exist."""
    if not why.strip():
        raise ValueError("--why is required: the description of a new alternative says what it is and why it is worth measuring")
    key = slug(name)
    if not key:
        raise ValueError("name the technology")
    known = {r.get("solution_id", "") for r in registry.every_solution()}
    missing = [u for u in uses if u not in known]
    if missing:
        raise ValueError(f"the solutions it would use do not exist: {', '.join(missing)}")
    folder = solution_folder(config, registry, solution_id)
    impl_id = f"{solution_id}:{key}"
    if impl_id in {r.get("implementation_id", "") for r in registry.implementations}:
        raise ValueError(f"{impl_id} is already recorded")
    impl_folder = folder
    template = load_template(TEMPLATE_DATA)
    columns, rows = declarations.table_rows(impl_folder, "implementations.csv", "implementation_id", template, "implementation")
    rows.append(declarations.blank(columns, implementation_id=impl_id, solution_id=solution_id, filepath=filepath, name=name.strip(),
                                   description=why.strip(), uses_solution_ids=";".join(uses)))
    write_csv(impl_folder / "implementations.csv", columns, rows)
    done = [f"implementations.csv: add {impl_id}" + ("" if filepath else " (no arm yet: not measured until its code is declared)")]
    sol_columns, sol_rows = declarations.table_rows(folder, "solutions.csv", "solution_id", template, "solution")
    row = next(r for r in sol_rows if r.get("solution_id") == solution_id)
    if "implementations" in row and key not in ids(row["implementations"]):
        row["implementations"] = ";".join(ids(row["implementations"]) + [key])
        write_csv(folder / "solutions.csv", sol_columns, sol_rows)
        done.append(f"solutions.csv: list {key} in the implementations of {solution_id}")
    return done


def record_change(config: Config, registry: Registry, solution_id: str, what: str, why: str,
                  today: Optional[datetime.date] = None) -> List[str]:
    """Append ``<date>: <what>. Because <why>`` to the solution's ``knowledge``: the justification of a change to the specification."""
    if not what.strip() or not why.strip():
        raise ValueError("a change to the specification is recorded with what changed (--changed) and why (--why)")
    folder = solution_folder(config, registry, solution_id)
    columns, rows = declarations.table_rows(folder, "solutions.csv", "solution_id", load_template(TEMPLATE_DATA), "solution")
    row = next(r for r in rows if r.get("solution_id") == solution_id)
    if "knowledge" not in row:
        raise ValueError("this solutions.csv has no `knowledge` column")
    line = f"{(today or datetime.date.today()).isoformat()}: {what.strip().rstrip('.')}. Because {why.strip().rstrip('.')}."
    row["knowledge"] = (row["knowledge"].rstrip() + "\n" if row["knowledge"].strip() else "") + line
    write_csv(folder / "solutions.csv", columns, rows)
    return [f"solutions.csv: record the change in the knowledge of {solution_id}"]


def run_cli(config: Config, registry: Registry, solution_id: str, name: str, why: str, uses: Sequence[str], filepath: str,
            changed: str, say=print) -> int:
    try:
        if changed:
            done = record_change(config, registry, solution_id, changed, why)
        else:
            done = admit(config, registry, solution_id, name, why, uses, filepath)
    except ValueError as exc:
        say(f"esoi: {exc}")
        return 2
    for line in done:
        say(line)
    if not changed:
        say("next: fill the advantages and disadvantages, declare the code with `@implementation` when there is some, then "
            "`esoi records sync`, `esoi run`, `esoi leaderboard`")
    return 0
