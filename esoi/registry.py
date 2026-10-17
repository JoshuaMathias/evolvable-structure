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


def join_metrics(solutions: List[Dict[str, str]], metrics: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Give each solution row the ``metric`` (names) and ``metric_command`` (commands) of its metric records."""
    if not metrics:
        return solutions
    by_id = {m["metric_id"]: m for m in metrics}
    for row in solutions:
        linked = [by_id[i] for i in ids(row.get("metric_ids", "")) if i in by_id]
        row["metric"] = SEP.join(m.get("name", "") for m in linked if m.get("name"))
        row["metric_command"] = SEP.join(m.get("command", "") for m in linked if m.get("command"))
    return solutions


def load(config: Config) -> Registry:
    struct = config.structure
    metrics = read_csv(struct / "metrics.csv")
    return Registry(
        components=read_csv(struct / "components.csv"),
        solutions=join_metrics(read_csv(struct / "solutions.csv"), metrics),
        metrics=metrics,
        problems=read_csv(struct / "problems.csv"),
        ideals=read_csv(struct / "ideals.csv"),
        implementations=read_csv(struct / "implementations.csv"),
        waivers=read_csv(struct / "waivers.csv"),
        principles=read_csv(struct / "principles.csv"))


def harness_arms(config: Config, command: str) -> List[Tuple[str, str]]:
    """Every ``(component, implementation)`` a metric command runs, in order; the first is the primary metric."""
    return [(m.group(1), m.group(2)) for m in re.finditer(config.metric_command, command or "")]


def first_arm(config: Config, command: str) -> Tuple[str, str]:
    arms = harness_arms(config, command)
    return arms[0] if arms else ("", "")
