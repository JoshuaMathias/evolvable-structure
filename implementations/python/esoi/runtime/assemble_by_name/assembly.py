"""The frozen result of one assembly: the built objects by solution id, with the reason, choice and implementation of each."""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, List, Mapping, Optional, Tuple

from esoi.runtime.assemble_by_name import hierarchy
from esoi.runtime.assemble_by_name.environment_needs import declarations
from esoi.runtime.assemble_by_name.environment_needs.closure import Member, members_pairs
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.runtime.assemble_by_name.assembly_errors import AssemblyError
from esoi.runtime.implementation_selection import selection_registry


class Assembly:
    """The built objects of one consumer, frozen. ``assembly[solution_id]`` is the object; ``reasons`` has one line per
    solution; ``choice`` and ``implementation`` return what was chosen and loaded when ``assemble`` ran."""

    def __init__(self, assembler: Any, config: AssemblyConfig, built: Mapping[str, Tuple[Any, str, Any, Any]],
                 pending: Optional[Mapping[str, str]] = None):
        """``built`` is ``{solution_id: (object, reason line, Choice or None, implementation or None)}`` in build order.
        ``pending`` is ``{solution_id: one line saying what the consumer must pass}`` for a solution ``assemble_defaults`` skipped."""
        self.pending = MappingProxyType(dict(pending or {}))
        self.assembler = assembler
        self.config = config
        self.objects = MappingProxyType({sid: item[0] for sid, item in built.items()})
        self.reason_by_solution = MappingProxyType({sid: item[1] for sid, item in built.items()})
        self.choices = MappingProxyType({sid: item[2] for sid, item in built.items() if item[2] is not None})
        self.implementations = MappingProxyType({sid: item[3] for sid, item in built.items() if item[3] is not None})

    @property
    def reasons(self) -> Tuple[str, ...]:
        return tuple(self.reason_by_solution.values())

    @property
    def requirements(self) -> Tuple[declarations.Entry, ...]:
        """What the built arms declare they need from their environment, once each (see ``esoi.runtime.assemble_by_name.environment_needs.declarations``)."""
        return tuple(declarations.gather(members_pairs(
            Member(f"{sid}:{self.choices[sid].name}", arm) for sid, arm in self.implementations.items())))

    def solutions(self) -> List[str]:
        """The assembled solution ids, in build order."""
        return list(self.objects)

    def __getitem__(self, solution_id: str) -> Any:
        try:
            return self.objects[solution_id]
        except KeyError:
            raise AssemblyError(f"{solution_id!r} was not assembled; assembled: {', '.join(self.objects) or 'none'}; "
                                "remedy: list it in AssemblyConfig.solutions or provide it") from None

    def __contains__(self, solution_id: str) -> bool:
        return solution_id in self.objects

    def get(self, solution_id: str, default: Any = None) -> Any:
        return self.objects.get(solution_id, default)

    def choice(self, solution_id: str) -> selection_registry.Choice:
        """The arm chosen for an assembled solution and the layer that chose it (a provided object has none)."""
        try:
            return self.choices[solution_id]
        except KeyError:
            raise AssemblyError(f"{solution_id!r} has no recorded choice: it was not assembled, or it was provided") from None

    def explain(self, solution_id: str) -> hierarchy.Explanation:
        """Every layer that names an arm for the solution, under the configuration this assembly was built with."""
        return self.assembler.explain(solution_id, config=self.config)

    def implementation(self, solution_id: str) -> Any:
        """The implementation class or function the solution's object was built from (not instantiated again)."""
        try:
            return self.implementations[solution_id]
        except KeyError:
            raise AssemblyError(f"{solution_id!r} has no recorded implementation: it was not assembled, or it was provided") \
                from None
