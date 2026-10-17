"""Selection as data: turn ``(solution_id, name)`` into the implementation, from a selection table.

The table is plain data, keyed by ``solution_id``::

    SELECTION = {
        "greet": {
            "default": "plain",
            "implementations": {
                "plain": "mylib.greeters:PlainGreeter",                      # the class or factory
                "loud": {"target": "mylib.greeters:LoudGreeter", "config": "mylib.greeters:LoudConfig"},
            },
        },
    }

    selector = Selector(SELECTION)
    cls = selector.resolve("greet")                                   # the table default
    cls = selector.resolve("greet", "loud")                           # an explicit name
    cls = selector.resolve("greet", overrides={"greet": "loud"})      # a per-solution override dict

Precedence: explicit ``name``, then ``overrides[solution_id]``, then the table's ``default``. An unknown solution or
name raises ``ValueError`` listing the choices, so a typo in configuration fails loudly instead of falling
through an ``else``. Targets are imported lazily, so a module never imports an implementation until it is
chosen and an optional dependency is only needed when its implementation is picked.

A Selector reads no environment: the caller decides the name (from configuration, a test) and passes it in.
``register`` adds an implementation at run time (a consumer's own backend), so adding one is a data change, not
an edit to a call site. ``esoi check`` (rules S7, S14, S23) keeps the table and the registry in step.
"""
from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

Table = Mapping[str, Mapping[str, Any]]


def import_ref(ref: str) -> Any:
    """Import ``package.module:Attr`` and return the attribute."""
    module, _, attr = ref.partition(":")
    return getattr(importlib.import_module(module), attr)


def load_table(spec: str, root: Optional[Path] = None) -> Table:
    """Load a table named ``path/to/file.py:ATTR`` (loaded by path, so nothing else imports) or ``pkg.module:ATTR``."""
    where, _, attr = spec.partition(":")
    attr = attr or "SELECTION"
    if where.endswith(".py"):
        path = Path(where)
        path = path if path.is_absolute() or root is None else Path(root) / path
        loader = importlib.util.spec_from_file_location(f"esoi_table_{path.stem}", path)
        if loader is None or loader.loader is None:
            raise ValueError(f"cannot load selection table from {path}")
        module = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(module)
        return getattr(module, attr)
    return getattr(importlib.import_module(where), attr)


class Selector:
    """Resolve implementations of solutions from a selection table."""

    def __init__(self, table: Table):
        self.table = table
        self.extra: Dict[str, Dict[str, Any]] = {}
        self.extra_default: Dict[str, str] = {}

    def implementations(self, solution_id: str) -> Dict[str, Any]:
        if solution_id not in self.table:
            raise ValueError(f"no selection table entry for solution {solution_id!r}; known: {sorted(self.table)}")
        return {**self.table[solution_id]["implementations"], **self.extra.get(solution_id, {})}

    def default_name(self, solution_id: str) -> str:
        """The implementation used when nothing asks for another."""
        self.implementations(solution_id)
        return self.extra_default.get(solution_id) or self.table[solution_id]["default"]

    def names(self, solution_id: str) -> List[str]:
        """Every selectable implementation name for a solution, sorted."""
        return sorted(self.implementations(solution_id))

    def chosen_name(self, solution_id: str, name: Optional[str] = None,
                    overrides: Optional[Mapping[str, str]] = None) -> str:
        """The implementation name that ``resolve`` would use (explicit, then override, then default)."""
        picked = str(name or (overrides or {}).get(solution_id) or self.default_name(solution_id)).strip().lower()
        if picked not in self.implementations(solution_id):
            raise ValueError(f"unknown implementation {picked!r} for {solution_id}; choices: "
                             f"{', '.join(self.names(solution_id))}")
        return picked

    def resolve(self, solution_id: str, name: Optional[str] = None, *,
                overrides: Optional[Mapping[str, str]] = None) -> Any:
        """The class or factory for the chosen implementation of ``solution_id`` (not an instance)."""
        entry = self.implementations(solution_id)[self.chosen_name(solution_id, name, overrides)]
        return import_ref(entry["target"] if isinstance(entry, dict) else entry)

    def resolve_config(self, solution_id: str, name: Optional[str] = None, *,
                       overrides: Optional[Mapping[str, str]] = None) -> Any:
        """The config class the chosen implementation is built from, or ``None`` when it takes none."""
        entry = self.implementations(solution_id)[self.chosen_name(solution_id, name, overrides)]
        ref = entry.get("config") if isinstance(entry, dict) else None
        return import_ref(ref) if ref else None

    def register(self, solution_id: str, name: str, target: str, *, config: Optional[str] = None,
                 default: bool = False) -> None:
        """Add an implementation (``"pkg.module:Attr"``) to a known solution; ``default=True`` makes it the default."""
        self.implementations(solution_id)
        key = name.strip().lower()
        self.extra.setdefault(solution_id, {})[key] = {"target": target, "config": config} if config else target
        if default:
            self.extra_default[solution_id] = key
