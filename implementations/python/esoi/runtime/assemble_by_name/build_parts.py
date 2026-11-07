"""Build the parts of a program in dependency order from the chosen arms, injecting each need by name, failing on a cycle or an unmet need."""
from __future__ import annotations

import inspect
import logging
from dataclasses import replace
from typing import Any, Dict, List, Mapping, Optional, Tuple

from esoi.runtime.assemble_by_name.arm_inspection import builder_of, config_hash, package_version
from esoi.runtime.assemble_by_name.assembly import Assembly
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.runtime.assemble_by_name.assembly_errors import AssemblyError
from esoi.runtime.assemble_by_name.environ_options import environ_fill
from esoi.runtime.assemble_by_name.lazy_need import LazyNeed
from esoi.runtime.implementation_selection import variants

log = logging.getLogger("esoi.runtime.assemble_by_name.assemble")


def check_arguments(sid: str, arm: str, target: Any, kwargs: Mapping[str, Any], options: Mapping[str, Any], chain: List[Tuple[str, str]]) -> None:
    """Raise ``AssemblyError`` when the options name a parameter the arm lacks, or a required parameter has neither a need nor an option."""
    builder = builder_of(target)
    params = inspect.signature(builder).parameters if builder is not None else {}
    extra = [k for k in options if k not in params or k in kwargs]
    if extra:
        raise AssemblyError(f"{sid} ({arm}) has no option(s) {', '.join(extra)}; its parameters: "
                            f"{', '.join(p for p in params if p != 'self' and p not in kwargs) or 'none'}")
    missing = [name for name, par in params.items()
               if name != "self" and name not in kwargs and name not in options and par.default is par.empty
               and par.kind not in (par.VAR_POSITIONAL, par.VAR_KEYWORD)]
    if missing:
        chain_text = " -> ".join([p for p, a in chain] + [sid])
        raise AssemblyError(f"{sid} ({arm}) needs option(s) {', '.join(missing)} (chain: {chain_text}); remedy: "
                            f"pass options={{{sid!r}: {{{', '.join(repr(m) + ': ...' for m in missing)}}}}} or "
                            f"provided={{{sid!r}: ...}}")


def assemble_defaults(assembler: Any, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
    """Build every solution of the scope that its chosen arm (explicit name, selections, then the package default) can build
    with what was passed, and report the rest in ``Assembly.pending`` instead of raising. With no arguments this is the
    zero-configuration call; a consumer passes only what differs: ``names``/``selections`` for an arm, ``options`` for its
    arguments, ``provided`` for objects it owns."""
    cfg = config or AssemblyConfig()
    given = dict(provided or {})
    assembler.prepare()
    pending = assembler.pending_needs(cfg, given)
    wanted = tuple(sid for sid in assembler.visible() if sid not in pending)
    built = assembler.assemble(replace(cfg, solutions=wanted), given)
    return Assembly(built.assembler, built.config, {sid: (built.objects[sid], built.reason_by_solution[sid], built.choices.get(sid),
                                                       built.implementations.get(sid)) for sid in built.objects}, pending)


def assemble(assembler: Any, config: Optional[AssemblyConfig] = None, provided: Optional[Mapping[str, Any]] = None) -> Assembly:
    """Build the solutions a consumer uses, in dependency order, once. A provided object wins for its solution; otherwise
    the cascade's arm is built with its needs injected and its ``options`` passed. A cycle or an unmet need fails here,
    naming the chain. The result is frozen: its choices and implementations are fixed."""
    cfg = config or AssemblyConfig()
    given = dict(provided or {})
    assembler.prepare()
    assembler.selection_environ(cfg)
    for sid in cfg.reasons:
        assembler.reasons_for(sid, cfg)
    for sid, obj in given.items():
        assembler.check_provided(sid, obj)
    built: Dict[str, Tuple[Any, str, Any, Any]] = {}

    def need_error(chain: List[Tuple[str, str]], sid: str) -> AssemblyError:
        remedy = f"remedy: pass provided={{{sid!r}: ...}} or register an arm for it"
        if not chain:
            return AssemblyError(f"{sid}: no arm, not provided; {remedy}")
        parent, arm = chain[-1]
        return AssemblyError(f"{parent} ({arm}) needs {sid}: no arm, not provided (chain: "
                             f"{' -> '.join([p for p, a in chain] + [sid])}); {remedy}")

    def build(sid: str, chain: List[Tuple[str, str]]) -> Any:
        if sid in built:
            return built[sid][0]
        ring = [p for p, a in chain]
        if sid in ring:
            raise AssemblyError("dependency cycle: " + " -> ".join(ring[ring.index(sid):] + [sid]))
        if sid in given:
            reason = (f"{sid} -> {type(given[sid]).__name__} (layer: consumer provided, package version "
                      f"{package_version(given[sid])}, config hash {config_hash({})})")
            built[sid] = (given[sid], reason, None, None)
            return given[sid]
        picked = assembler.pick(sid, None, cfg)
        if picked is None:
            raise need_error(chain, sid)
        base, variant_options = variants.split(picked.name)    # a selected variant (arm@option=value) is its base arm with options
        target = assembler.load(sid, base)
        options = {**variant_options, **dict(cfg.options.get(sid, {}))}
        filled = environ_fill(target, options, cfg.consumer_environ)
        options.update({option: str(cfg.consumer_environ[variable]).strip() for option, variable in filled.items()})
        lazy = assembler.lazy_needs_of(target)
        below = chain + [(sid, picked.name)]
        kwargs = {param: (LazyNeed(need, lambda need=need, below=below: build(need, below)) if param in lazy else build(need, below))
                  for param, need in assembler.needs_of(target).items()}
        if inspect.isclass(target) or inspect.isfunction(target):   # a class or factory is built; anything else is an instance
            check_arguments(sid, picked.name, target, kwargs, options, chain)
            obj = target(**kwargs, **options)
        else:
            obj = target
        reason = (f"{sid} -> {picked.name} (layer: {picked.layer}, package version {package_version(target)}, "
                  f"config hash {config_hash(options)}{', options from consumer environ: ' + ', '.join(f'{o} <- {v}' for o, v in filled.items()) if filled else ''}{', reasons: ' + '; '.join(picked.reasons) if picked.reasons else ''})")
        built[sid] = (obj, reason, picked, target)
        return obj

    for sid in (list(cfg.solutions) or sorted(set(given) | set(assembler.with_a_default(cfg)))):
        assembler.check_solution(sid)
        build(sid, [])
    for item in built.values():
        log.info(item[1])
    return Assembly(assembler, cfg, built)
