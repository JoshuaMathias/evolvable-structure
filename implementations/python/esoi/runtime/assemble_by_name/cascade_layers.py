"""List every layer of the selection cascade that names an arm for a solution, highest priority first, with the conditions that skip one."""
from __future__ import annotations

from typing import Any, List, Optional

from esoi.runtime.assemble_by_name import hierarchy, lock_file
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.structure.intent_registry.assembly_errors import AssemblyError, LockError
from esoi.structure.intent_registry.name_check import check_name
from esoi.runtime.implementation_selection import selection_cascade
from esoi.runtime.implementation_selection import variants


def layers(assembler: Any, solution_id: str, name: Optional[str], cfg: AssemblyConfig) -> hierarchy.Explanation:
    """Every layer that names an arm for the solution, highest priority first: explicit name, consumer selections,
    selection environ, the lock, this scope's default, then each parent's default. A name that is not listed raises; a conditional
    entry whose condition does not hold stays in the list, marked skipped."""
    available = assembler.names(solution_id)
    variable = selection_cascade.env_name(solution_id, assembler.scope)
    found: List[hierarchy.Layer] = []
    for layer, kind, given, why, source in (("explicit name", "explicit", name or cfg.names.get(solution_id), (), ""),
                                            ("consumer selections", "selections", cfg.selections.get(solution_id),
                                             assembler.reasons_for(solution_id, cfg), ""),
                                            ("selection environ", "environ", assembler.selection_environ(cfg).get(variable), (), variable)):
        if given:
            found += given_layers(assembler, solution_id, available, cfg, (layer, kind, given, why, source))
    if cfg.lock is not None:
        found += lock_layers(assembler, solution_id, available, cfg)
    found += default_layers(assembler, solution_id, available)
    parent_default = next((layer.name for layer in found if layer.inherited), "")
    return hierarchy.Explanation(solution_id, tuple(found), parent_default)


def given_layers(assembler: Any, solution_id: str, available: List[str], cfg: AssemblyConfig, source_of: tuple) -> List[hierarchy.Layer]:
    """The layers one given source (explicit name, consumer selections or selection environ) names; an unlisted name raises."""
    layer, kind, given, why, source = source_of
    if not isinstance(given, (str, list, tuple)):
        check_name(given, f"{layer} for {solution_id!r}")
    try:
        parsed = hierarchy.entries(given)
    except ValueError as error:
        raise AssemblyError(f"{layer} for {solution_id!r}: {error}") from error
    found: List[hierarchy.Layer] = []
    for _, base, conditions in parsed:
        check_name(base, f"{layer} for {solution_id!r}")
        if base not in available:
            raise AssemblyError(f"unknown implementation {base!r} for {solution_id!r} in scope {assembler.scope!r} (layer: {layer}); "
                                f"available: {', '.join(available) or 'none'}; remedy: use one of them, or register your own "
                                f"under a name you own with register()")
        found.append(hierarchy.Layer(layer, base, source, kind, "", ",".join(f"{k}={v}" for k, v in sorted(conditions.items())),
                                     why, hierarchy.met(conditions, cfg.circumstances)))
    return found


def lock_layers(assembler: Any, solution_id: str, available: List[str], cfg: AssemblyConfig) -> List[hierarchy.Layer]:
    """The lock's layer for the solution, or none; a locked arm the scope no longer lists raises."""
    locked = lock_file.locked_arm(assembler, cfg.lock, solution_id)
    if not locked:
        return []
    arm, where = locked
    if arm not in available:
        raise LockError(f"the lock {where} names {arm!r} for {solution_id!r}, which scope {assembler.scope!r} no longer lists; "
                        f"available: {', '.join(available) or 'none'}; remedy: esoi lock --update --solution {solution_id} "
                        f"(moves the lock to the latest selection), or install the release that still has {arm!r}")
    return [hierarchy.Layer("lock", arm, where, "lock")]


def default_layers(assembler: Any, solution_id: str, available: List[str]) -> List[hierarchy.Layer]:
    """The default of this scope and of each parent that names an arm, marked broken when it cannot be chosen."""
    found: List[hierarchy.Layer] = []
    for one in assembler.chain():
        packaged = one.packaged()
        default = packaged.defaults.get(solution_id, "")
        if default:
            broken = "" if variants.base_of(default) in available else (
                f"error: the default {default!r} of {solution_id!r} in scope {one.scope!r} (from {packaged.source}) is "
                f"not an implementation that can be chosen; available: {', '.join(available) or 'none'}")
            found.append(hierarchy.Layer(f"{one.scope} default", default, packaged.source, "default", one.scope, "",
                                         tuple(packaged.reasons.get(solution_id, ())), broken, one is not assembler))
    return found
