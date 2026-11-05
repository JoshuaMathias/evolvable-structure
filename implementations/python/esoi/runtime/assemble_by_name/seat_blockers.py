"""Say why a seat cannot be built yet, as lines and structured reasons read from the arm itself: unmet keys, installs, programs, options."""
from __future__ import annotations

import inspect
import shutil
from typing import Any, List, Mapping, Tuple

from esoi.runtime.assemble_by_name.environment_needs import checking, declarations
from esoi.runtime.assemble_by_name.arm_inspection import builder_of
from esoi.runtime.assemble_by_name.entry_types import Reason
from esoi.runtime.assemble_by_name.environ_options import environ_lacking


def unmet_checks(target: Any, environ: Mapping[str, str], options: Mapping[str, Any]) -> List[Any]:
    """The unmet required requirements of one arm that nothing the caller passed fills. A program is looked up on the PATH of
    ``environ`` (no PATH, no program), so ``environ={}`` never finds, and never starts, one."""
    out = []
    for one in checking.check(declarations.declared(target), environ):
        item = one.requirement
        if isinstance(item, declarations.Binary):
            found = shutil.which(item.name, path=environ.get("PATH", ""))
            one = checking.Check(item, checking.MET if found else checking.UNMET,
                            "" if found else (item.install_hint or f"install {item.name} and put it on PATH"))
        if isinstance(item, declarations.Env) and item.option in options:
            continue
        if isinstance(item, declarations.Api) and item.key is not None and item.key.option in options:
            continue
        if one.blocking:
            out.append(one)
    return out


def reason_of(seat: str, arm: str, one: Any) -> Reason:
    kind = ("key" if isinstance(one.requirement, (declarations.Env, declarations.Api)) else "network" if isinstance(one.requirement, declarations.Network)
            else "install")
    return Reason(seat, arm, kind, one.remedy)


def seat_reasons(assembler: Any, sid: str, cfg: Any, line: str) -> List[Reason]:
    """Why one pending seat cannot be built, by category, read from the arm itself (not from the pending line)."""
    picked = assembler.pick(sid, None, cfg)
    if picked is None:
        return [Reason(sid, "", "provided", line)]
    try:
        target = assembler.load(sid, picked.name)
        needs = assembler.needs_of(target)
    except Exception:
        return [Reason(sid, picked.name, "load", line)]
    given = cfg.options.get(sid, {})
    out: List[Reason] = []
    if environ_lacking(target, given, cfg.consumer_environ):
        out.append(Reason(sid, picked.name, "key", line))
    out += [reason_of(sid, picked.name, one) for one in unmet_checks(target, cfg.consumer_environ, given)]
    builder = builder_of(target)
    for name, par in (inspect.signature(builder).parameters.items() if builder is not None else []):
        if name != "self" and name not in needs and name not in given and par.default is par.empty \
                and par.kind not in (par.VAR_POSITIONAL, par.VAR_KEYWORD) and not out:
            out.append(Reason(sid, picked.name, "option", line))
            break
    lazy = assembler.lazy_needs_of(target)     # a Lazy need is built on first use, so the seat does not wait on it
    return out or [Reason(sid, picked.name, "needs", line, tuple(need for param, need in needs.items() if param not in lazy))]


def blockers(assembler: Any, cfg: Any, pending: Mapping[str, str], sid: str, given: Mapping[str, Any]) -> Tuple[List[str], List[Reason]]:
    """Every line and structured reason that keeps ``sid`` from running: the pending seats it reaches, and, for the arms that
    would be built, each unmet key, install or program."""
    lines: List[str] = []
    reasons: List[Reason] = []
    if sid in pending:
        seen: List[str] = []
        queue = [sid]
        while queue:
            seat = queue.pop(0)
            if seat in seen or seat not in pending:
                continue
            seen.append(seat)
            lines.append(pending[seat])
            reasons += seat_reasons(assembler, seat, cfg, pending[seat])
            queue += [other for other in pending if other in pending[seat]]
        return lines, reasons
    for member in assembler.closure(cfg, given, solutions=(sid,)):
        seat, _, arm = member.label.partition(":")
        found = unmet_checks(member.target, cfg.consumer_environ, cfg.options.get(seat, {}))
        if found:
            lines.append(f"{seat} ({arm}): " + "; ".join(dict.fromkeys(one.remedy for one in found if one.remedy)))
            reasons += [reason_of(seat, arm, one) for one in found]
    return lines, reasons
