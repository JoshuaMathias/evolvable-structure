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

A table need not hold its own ``default``. Leave it out and the default is the solution's ``selected`` in the records
(``Selector.from_config`` reads them), so the choice is made once, where the metric decides it, and there is no second
copy to keep in step. A table that still holds a ``default`` keeps working, and rule S23 compares it with the records.
The graceful layer on top of this table (decorators, a per-call ``using=``, a cascade of context) is ``esoi.runtime``.
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


def default_name(solution: Mapping[str, str], implementations: List[Mapping[str, str]]) -> str:
    """The implementation name a solution row's ``selected`` cell stands for. ``selected`` is a name, an
    ``implementation_id`` (``solution:name``), or the filepath of an implementation (``filepath`` or ``filepath::name``); the
    implementation records say which, so a project may write it in the style it already uses."""
    selected = (solution.get("selected") or "").strip()
    sid = solution.get("solution_id", "")
    if not selected:
        return ""
    module, _, named = selected.partition("::")
    for record in (r for r in implementations if r.get("solution_id") == sid):
        iid, path = record.get("implementation_id", ""), (record.get("filepath") or "").strip()
        suffix = iid.partition(":")[2].strip().lower()
        if selected in (iid, f"{sid}:{selected}") or (path == module and (not named or suffix == named.strip().lower())):
            return suffix or selected.lower()
    if named:
        return named.strip().lower()
    stem = module.rsplit("/", 1)[-1]
    return (stem[:-3] if stem.endswith(".py") else stem).strip().lower()


def records_defaults(config: Any) -> Dict[str, str]:
    """``{solution_id: implementation name}`` for every solution of the records that selects one: the project default,
    read where the metric decides it. ``config`` is an ``esoi.config.Config``."""
    from .registry import load
    loaded = load(config)
    return {r["solution_id"]: name for r in loaded.every_solution()
            if r.get("solution_id") and (name := default_name(r, loaded.implementations))}


def snapshot_defaults(path: Any) -> Dict[str, str]:
    """``{solution_id: name}`` from an ``esoi_selection.json`` written by ``esoi select --snapshot``: the project defaults
    for a package installed without its records."""
    import json
    found = json.loads(Path(path).read_text(encoding="utf-8"))
    return {sid: entry["default"] for sid, entry in found.items() if entry.get("default")}


class Selector:
    """Resolve implementations of solutions from a selection table."""

    def __init__(self, table: Table, defaults: Optional[Mapping[str, str]] = None):
        self.table = table
        self.defaults = dict(defaults or {})   # solution_id -> name, from the records, for entries without a default
        self.extra: Dict[str, Dict[str, Any]] = {}
        self.extra_default: Dict[str, str] = {}

    @classmethod
    def from_config(cls, config: Any) -> "Selector":
        """The table the configuration names, with defaults from the records for the entries that hold none."""
        if not config.selection_table:
            raise ValueError("no selection table configured (set `selection` in the config)")
        return cls(load_table(config.selection_table, config.root), records_defaults(config))

    def implementations(self, solution_id: str) -> Dict[str, Any]:
        if solution_id not in self.table:
            raise ValueError(f"no selection table entry for solution {solution_id!r}; known: {sorted(self.table)}")
        return {**self.table[solution_id]["implementations"], **self.extra.get(solution_id, {})}

    def default_name(self, solution_id: str) -> str:
        """The implementation used when nothing asks for another."""
        self.implementations(solution_id)
        found = self.extra_default.get(solution_id) or self.table[solution_id].get("default") or self.defaults.get(solution_id)
        if not found:
            raise ValueError(f"solution {solution_id!r} has no default: its table entry holds none and the records "
                             "name no `selected` implementation for it")
        return found

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
