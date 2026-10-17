"""Load a repository's registry: the CSV records in its structure folder, with each solution joined to its metrics.

A solution links its metrics through ``metric_ids``; a metric's name and command live on the metric record
(``metrics.csv``), so every rule and report that reads a solution's ``metric_command`` sees that one source.
A registry with no ``metrics.csv`` keeps the columns it has.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .config import Config
from .tables import SEP, ids, read_csv


@dataclass
class Registry:
    """The CSV records of one repository, as lists of row dicts."""
    components: List[Dict[str, str]] = field(default_factory=list)
    solutions: List[Dict[str, str]] = field(default_factory=list)
    metrics: List[Dict[str, str]] = field(default_factory=list)
    problems: List[Dict[str, str]] = field(default_factory=list)
    ideals: List[Dict[str, str]] = field(default_factory=list)
    implementations: List[Dict[str, str]] = field(default_factory=list)
    waivers: List[Dict[str, str]] = field(default_factory=list)
    principles: List[Dict[str, str]] = field(default_factory=list)
    missing: List[Tuple[str, str]] = field(default_factory=list)   # (file, column) the rules read that a file lacks


def join_metrics(solutions: List[Dict[str, str]], metrics: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Give each solution row the ``metric`` (names) and ``metric_command`` (commands) of its metric records."""
    if not metrics:
        return solutions
    by_id = {m.get("metric_id", ""): m for m in metrics}
    for row in solutions:
        linked = [by_id[i] for i in ids(row.get("metric_ids", "")) if i in by_id]
        row["metric"] = SEP.join(m.get("name", "") for m in linked if m.get("name"))
        row["metric_command"] = SEP.join(m.get("command", "") for m in linked if m.get("command"))
    return solutions


# Columns the rules read. A file that lacks one is reported (rules S2, S7, S9) and the rules see it as empty, so a
# header that was edited or never had the column cannot crash a check. An optional column (``port``) is only a finding
# when something needs it (see rules.registry_rules).
RULE_COLUMNS = {
    "components.csv": ["component_id", "layer", "path", "role", "solutions"],
    "solutions.csv": ["solution_id", "implementations", "selected", "gap", "action"],
    "waivers.csv": ["rule", "path", "reason"],
}
OPTIONAL_COLUMNS = {"solutions.csv": ["port"]}


def fill_columns(name: str, rows: List[Dict[str, str]], missing: List[Tuple[str, str]]) -> List[Dict[str, str]]:
    """Give every row an empty value for each column the rules read and the file lacks; record the lacking ones
    (the optional ones too, so a rule that needs one can say so)."""
    if rows:
        for column in RULE_COLUMNS.get(name, []) + OPTIONAL_COLUMNS.get(name, []):
            if column not in rows[0]:
                missing.append((name, column))
                for row in rows:
                    row[column] = ""
    return rows


def load(config: Config) -> Registry:
    struct = config.structure
    metrics = read_csv(struct / "metrics.csv")
    missing: List[Tuple[str, str]] = []
    return Registry(
        components=fill_columns("components.csv", read_csv(struct / "components.csv"), missing),
        solutions=join_metrics(fill_columns("solutions.csv", read_csv(struct / "solutions.csv"), missing), metrics),
        metrics=metrics,
        problems=read_csv(struct / "problems.csv"),
        ideals=read_csv(struct / "ideals.csv"),
        implementations=read_csv(struct / "implementations.csv"),
        waivers=fill_columns("waivers.csv", read_csv(struct / "waivers.csv"), missing),
        principles=read_csv(struct / "principles.csv"),
        missing=missing)


def harness_arms(config: Config, command: str) -> List[Tuple[str, str]]:
    """Every ``(component, implementation)`` a metric command runs, in order; the first is the primary metric."""
    return [(m.group(1), m.group(2)) for m in re.finditer(config.metric_command, command or "")]


def first_arm(config: Config, command: str) -> Tuple[str, str]:
    arms = harness_arms(config, command)
    return arms[0] if arms else ("", "")
