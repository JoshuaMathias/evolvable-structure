"""List every layer of the selection cascade that names an arm for a solution, highest priority first, with the conditions that skip one."""
from __future__ import annotations

from typing import Any, List, Optional

from esoi.runtime.assemble_by_name import hierarchy
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.runtime.assemble_by_name.assembly_errors import AssemblyError, LockError
from esoi.runtime.assemble_by_name.name_check import check_name
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
        if not given:
            continue
        if not isinstance(given, (str, list, tuple)):
            check_name(given, f"{layer} for {solution_id!r}")
        try:
            parsed = hierarchy.entries(given)
        except ValueError as error:
            raise AssemblyError(f"{layer} for {solution_id!r}: {error}") from error
        for _, base, conditions in parsed:
            check_name(base, f"{layer} for {solution_id!r}")
            if base not in available:
                raise AssemblyError(f"unknown implementation {base!r} for {solution_id!r} in scope {assembler.scope!r} (layer: {layer}); "
                                    f"available: {', '.join(available) or 'none'}; remedy: use one of them, or register your own "
                                    f"under a name you own with register()")
            found.append(hierarchy.Layer(layer, base, source, kind, "", ",".join(f"{k}={v}" for k, v in sorted(conditions.items())),
                                         why, hierarchy.met(conditions, cfg.circumstances)))
    if cfg.lock is not None:
        from esoi.runtime.implementation_selection import lock as lock_module
        locked = lock_module.locked_arm(assembler, cfg.lock, solution_id)
        if locked:
            arm, where = locked
            if arm not in available:
                raise LockError(f"the lock {where} names {arm!r} for {solution_id!r}, which scope {assembler.scope!r} no longer lists; "
                                f"available: {', '.join(available) or 'none'}; remedy: esoi lock --update --solution {solution_id} "
                                f"(moves the lock to the latest selection), or install the release that still has {arm!r}")
            found.append(hierarchy.Layer("lock", arm, where, "lock"))
    for one in assembler.chain():
        packaged = one.packaged()
        default = packaged.defaults.get(solution_id, "")
        if default:
            broken = "" if variants.base_of(default) in available else (
                f"error: the default {default!r} of {solution_id!r} in scope {one.scope!r} (from {packaged.source}) is "
                f"not an implementation that can be chosen; available: {', '.join(available) or 'none'}")
            found.append(hierarchy.Layer(f"{one.scope} default", default, packaged.source, "default", one.scope, "",
                                         tuple(packaged.reasons.get(solution_id, ())), broken, one is not assembler))
    parent_default = next((layer.name for layer in found if layer.inherited), "")
    return hierarchy.Explanation(solution_id, tuple(found), parent_default)
