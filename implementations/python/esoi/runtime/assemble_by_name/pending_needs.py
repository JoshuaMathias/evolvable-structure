"""Find the solutions that cannot be built from defaults alone, each with one line saying what the consumer must pass."""
from __future__ import annotations

import inspect
from typing import Any, Dict, Mapping

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
        if picked is None:
            available = ", ".join(assembler.names(sid))
            found[sid] = (f"{sid}: no selected arm; pass arms={{{sid!r}: <one of {available}>}}" if available
                          else f"{sid}: no arm yet; pass provided={{{sid!r}: <your object>}}")
        else:
            try:
                target = assembler.load(sid, picked.name)
                needs = assembler.needs_of(target)
            except Exception as error:
                found[sid] = f"{sid} ({picked.name}): cannot be loaded ({error}); install what it needs or pass provided={{{sid!r}: ...}}"
            else:
                builder = builder_of(target)
                options = {**config.options.get(sid, {}), **environ_fill(target, config.options.get(sid, {}), config.consumer_environ)}
                missing = [name for name, par in (inspect.signature(builder).parameters.items() if builder is not None else [])
                           if name != "self" and name not in needs and name not in options and par.default is par.empty
                           and par.kind not in (par.VAR_POSITIONAL, par.VAR_KEYWORD)]
                lacking = environ_lacking(target, config.options.get(sid, {}), config.consumer_environ)
                given_options = config.options.get(sid, {})
                remedy = checking.remedy_line(
                    one for one in checking.check(declarations.declared(target), config.consumer_environ)
                    if not (isinstance(one.requirement, declarations.Env) and one.requirement.option in given_options)
                    and not (isinstance(one.requirement, declarations.Api) and one.requirement.key is not None
                             and one.requirement.key.option in given_options))
                lazy = assembler.lazy_needs_of(target)
                unmet = [need for param, need in needs.items() if param not in lazy and not check(need)]
                if lacking:
                    found[sid] = (f"{sid} ({picked.name}): set " + "; ".join(f"{' or '.join(names)} (option {' or '.join(repr(o) for o in group)})"
                                  for group, names in lacking.items()) + f" in the environ mapping you pass, or pass options={{{sid!r}: {{...}}}}")
                elif remedy:
                    found[sid] = f"{sid} ({picked.name}): {remedy}"
                elif missing:
                    found[sid] = f"{sid} ({picked.name}): pass options={{{sid!r}: {{{', '.join(repr(m) + ': ...' for m in missing)}}}}}"
                elif unmet:
                    found[sid] = f"{sid} ({picked.name}): needs {', '.join(unmet)}; see those lines"
        state[sid] = sid not in found
        return state[sid]

    for sid in assembler.visible():
        check(sid)
    return found
