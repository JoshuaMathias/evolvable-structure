"""Hierarchical defaults: a package built on another inherits its defaults, overrides only what differs, and says why.

An end user of a hub uses it with one line; the hub's ESOI-informed defaults apply to every solution. A package that builds on
the hub (a *child*) gives ``Assembler(..., parent=hub)`` and then carries only the choices that differ. This module holds the
parts of that which are plain data and have no Assembler in them:

* ``Layer`` and ``Explanation``: one line per layer of the cascade of one solution (value, source, scope, reasons), the winner
  named. ``Assembler.explain`` returns one across the child and its parents.
* ``entries``: a layer value is ``name`` or ``name@key=value,...``. In an Assembler the parameters are *conditions* on the
  caller's circumstance mapping (the parser is ``esoi.variants``, the comparison is ``esoi.circumstances.holds``): the entry
  applies only when every ``key=value`` holds, and a layer value may be a list, the first entry that applies winning.
* ``check_reasons``: why a child differs from its parent is a list of ids of the child's own problem, ideal or metric records,
  or ``unconfirmed: <text>`` (recorded and shown, never enough for rule S35).
* ``parent_defaults`` and ``read_overrides``: what rule S35 compares. ``[parent]`` in ``esoi.toml`` names the parent's records
  folder (``records``) or its ``esoi_selection.json`` (``snapshot``); ``overrides.csv`` (columns ``solution_id``,
  ``reason_ids``) holds a child's recorded reasons. A repository without ``[parent]`` has none of this and rule S35 is silent.

Standard library and ``esoi`` only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from . import variants
from .config import Config
from .intents import read_rows
from .tables import ids

OVERRIDES_FILE = "overrides.csv"
UNCONFIRMED = "unconfirmed:"
REASON_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
KINDS = ("explicit", "selections", "environ", "default")


@dataclass(frozen=True)
class Layer:
    """One layer of the cascade for one solution. ``kind`` is explicit, selections, environ or default; ``scope`` is the package
    whose default it is ('' for the caller's layers); ``when`` is the circumstance condition of a conditional entry; ``skipped``
    says why a conditional entry did not apply ('' when it did); ``inherited`` marks a parent's default."""
    layer: str
    name: str
    source: str = ""
    kind: str = "selections"
    scope: str = ""
    when: str = ""
    reasons: Tuple[str, ...] = ()
    skipped: str = ""
    inherited: bool = False


@dataclass(frozen=True)
class Explanation:
    """Every layer that names an arm for a solution, highest priority first, and the one that wins (the first not skipped)."""
    solution_id: str
    layers: Tuple[Layer, ...]
    parent_default: str = ""

    @property
    def winner(self) -> Optional[Layer]:
        return next((layer for layer in self.layers if not layer.skipped), None)

    @property
    def overrides_parent(self) -> bool:
        """Whether the winner is a caller's or child's choice of an arm other than the parent's default."""
        won = self.winner
        return bool(won and self.parent_default and not won.inherited and variants.base_of(won.name) != self.parent_default)

    def lines(self) -> List[str]:
        """A readable report: the winner first, then every layer with its value, source, condition and reasons."""
        won = self.winner
        head = f"{self.solution_id}: " + (f"{won.name} (layer: {won.layer})" if won else "no layer names an arm")
        out = [head]
        for layer in self.layers:
            mark = "->" if layer is won else ("skip" if layer.skipped else "  ")
            text = f"  {mark} {layer.layer}: {layer.name}"
            text += f" [{layer.source}]" if layer.source else ""
            text += f" when {layer.when}" if layer.when else ""
            text += f" ({layer.skipped})" if layer.skipped else ""
            text += f"; reasons: {', '.join(layer.reasons)}" if layer.reasons else ""
            out.append(text)
        if self.overrides_parent:
            out.append(f"  overrides the parent default {self.parent_default}" +
                       ("" if won and won.reasons else "; no reason recorded"))
        return out

    def __str__(self) -> str:
        return "\n".join(self.lines())


@dataclass(frozen=True)
class Override:
    """A choice that differs from the parent's default, with the reasons recorded for it."""
    solution_id: str
    chosen: str
    parent_default: str
    layer: str
    reasons: Tuple[str, ...]

    @property
    def justified(self) -> bool:
        """Whether at least one reason is an id of a record (an ``unconfirmed:`` marker does not count)."""
        return any(not r.startswith(UNCONFIRMED) for r in self.reasons)


def entries(value: Any) -> List[Tuple[str, str, Dict[str, str]]]:
    """``(text, base, conditions)`` for a layer value: a name, a ``name@key=value,...``, or a list of them. Raises
    ``ValueError`` for anything that is not text or is malformed, so a typo fails loudly."""
    items = [value] if isinstance(value, str) else (list(value) if isinstance(value, (list, tuple)) else [value])
    found = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError(f"{item!r} is not a name")
        base, conditions = variants.words(item)
        found.append((item.strip(), base, conditions))
    return found


def met(conditions: Mapping[str, str], facts: Mapping[str, Any]) -> str:
    """'' when every ``key=value`` holds in the caller's circumstance mapping, else which one does not."""
    from .circumstances import holds   # imported here: circumstances itself imports assemble
    for key, value in conditions.items():
        if not holds((key, "=", [value]), facts):
            return f"circumstance {key}={value} not met" + ("" if key in facts else f" ({key} not given)")
    return ""


def check_reasons(reasons: Sequence[str], what: str) -> Tuple[str, ...]:
    """The reasons as a tuple, or ``ValueError``: each is an id (``problem-x``) or ``unconfirmed: <text>``."""
    if isinstance(reasons, str):
        reasons = [reasons]
    out = []
    for reason in reasons:
        text = str(reason).strip()
        if text.lower().startswith(UNCONFIRMED):
            if not text[len(UNCONFIRMED):].strip():
                raise ValueError(f"{what}: {text!r} says unconfirmed but gives no text")
        elif not REASON_ID.fullmatch(text):
            raise ValueError(f"{what}: {text!r} is neither a record id nor '{UNCONFIRMED} <text>'")
        out.append(text)
    return tuple(out)


def read_overrides(config: Config) -> Dict[str, Tuple[str, ...]]:
    """``{solution_id: reason ids}`` from ``overrides.csv`` in the records (empty when the file is absent)."""
    found: Dict[str, Tuple[str, ...]] = {}
    for row in read_rows(config, OVERRIDES_FILE):
        sid = row.get("solution_id", "").strip()
        if sid:
            found[sid] = found.get(sid, ()) + tuple(ids(row.get("reason_ids", "")))
    return found


def parent_defaults(config: Config) -> Dict[str, str]:
    """``{solution_id: default name}`` of the parent that ``[parent]`` in the configuration names: ``records`` (a folder with its
    own ``esoi.toml``, relative to this repository) or ``snapshot`` (an ``esoi_selection.json``). Raises ``ValueError`` when it
    cannot be read, and ``{}`` when no parent is configured."""
    from . import config as config_module
    from .select import records_defaults, snapshot_defaults
    table = config.parent
    if not table:
        return {}
    try:
        if table.get("records"):
            return {sid: variants.base_of(name).lower() for sid, name in
                    records_defaults(config_module.load(config.root / str(table["records"]))).items()}
        if table.get("snapshot"):
            return {sid: variants.base_of(name).lower() for sid, name in snapshot_defaults(config.root / str(table["snapshot"])).items()}
    except Exception as error:
        raise ValueError(f"[parent] in the configuration cannot be read ({type(error).__name__}: {error})") from error
    raise ValueError("[parent] in the configuration names neither `records` (the parent's records folder) nor `snapshot` "
                     "(its esoi_selection.json)")

