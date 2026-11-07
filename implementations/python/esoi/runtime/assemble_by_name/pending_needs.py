"""Find the solutions that cannot be built from defaults alone, each with one line saying what the consumer must pass."""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Mapping

from esoi.runtime.assemble_by_name.environment_needs import checking, declarations
from esoi.runtime.assemble_by_name.arm_inspection import builder_of
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.runtime.assemble_by_name.environ_options import environ_fill, environ_lacking


def pending_needs(assembler: Any, config: AssemblyConfig, provided: Mapping[str, Any]) -> Dict[str, str]:
    """``{solution_id: one line}`` for each solution of the scope that cannot be built from defaults alone: no layer names an
    arm, the arm cannot be loaded, it needs a constructor argument that is not a solution (pass it in ``options``), or it needs
    a solution that is itself pending. A name a layer supplies that is unknown still raises: that is the caller's mistake."""
    assembler.prepare()
    found: Dict[str, str] = {}
    state: Dict[str, bool] = {}

    def check(sid: str) -> bool:
        if sid in state:
            return state[sid]
        state[sid] = True   # a cycle is left for assemble to name
        if sid in provided:
            return True
        picked = assembler.pick(sid, None, config)
        line = no_arm_line(assembler, sid) if picked is None else pending_line(assembler, config, sid, picked.name, check)
        if line:
            found[sid] = line
        state[sid] = sid not in found
        return state[sid]

    for sid in assembler.visible():
        check(sid)
    return found


def no_arm_line(assembler: Any, sid: str) -> str:
    """The pending line of a solution no layer names an arm for."""
    available = ", ".join(assembler.names(sid))
    return (f"{sid}: no selected arm; pass arms={{{sid!r}: <one of {available}>}}" if available
            else f"{sid}: no arm yet; pass provided={{{sid!r}: <your object>}}")


def missing_arguments(target: Any, needs: Mapping[str, str], options: Mapping[str, Any]) -> List[str]:
    """Constructor parameters of the target that are no need, no option and have no default."""
    builder = builder_of(target)
    return [name for name, par in (inspect.signature(builder).parameters.items() if builder is not None else [])
            if name != "self" and name not in needs and name not in options and par.default is par.empty
            and par.kind not in (par.VAR_POSITIONAL, par.VAR_KEYWORD)]


def unmet_requirement_remedy(target: Any, config: AssemblyConfig, sid: str) -> str:
    """The remedy line for the target's declared requirements that fail and that no option given for the solution fills."""
    given_options = config.options.get(sid, {})
    return checking.remedy_line(
        one for one in checking.check(declarations.declared(target), config.consumer_environ)
        if not (isinstance(one.requirement, declarations.Env) and one.requirement.option in given_options)
        and not (isinstance(one.requirement, declarations.Api) and one.requirement.key is not None
                 and one.requirement.key.option in given_options))


def pending_line(assembler: Any, config: AssemblyConfig, sid: str, arm: str, check: Callable[[str], bool]) -> str:
    """Why the picked arm cannot be built from defaults alone (empty when it can)."""
    try:
        target = assembler.load(sid, arm)
        needs = assembler.needs_of(target)
    except Exception as error:
        return f"{sid} ({arm}): cannot be loaded ({error}); install what it needs or pass provided={{{sid!r}: ...}}"
    options = {**config.options.get(sid, {}), **environ_fill(target, config.options.get(sid, {}), config.consumer_environ)}
    lazy = assembler.lazy_needs_of(target)
    return blocked_line(sid, arm, (environ_lacking(target, config.options.get(sid, {}), config.consumer_environ),
                                   unmet_requirement_remedy(target, config, sid), missing_arguments(target, needs, options),
                                   [need for param, need in needs.items() if param not in lazy and not check(need)]))


def blocked_line(sid: str, arm: str, found: tuple) -> str:
    """The first reason that applies, in order: a variable to set, an unmet requirement, a missing option, a seat it waits on."""
    lacking, remedy, missing, unmet = found
    if lacking:
        return (f"{sid} ({arm}): set " + "; ".join(f"{' or '.join(names)} (option {' or '.join(repr(o) for o in group)})"
                for group, names in lacking.items()) + f" in the environ mapping you pass, or pass options={{{sid!r}: {{...}}}}")
    if remedy:
        return f"{sid} ({arm}): {remedy}"
    if missing:
        return f"{sid} ({arm}): pass options={{{sid!r}: {{{', '.join(repr(m) + ': ...' for m in missing)}}}}}"
    if unmet:
        return f"{sid} ({arm}): needs {', '.join(unmet)}; see those lines"
    return ""
