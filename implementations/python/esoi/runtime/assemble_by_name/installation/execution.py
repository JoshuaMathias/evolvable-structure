"""Run an install plan only when told to, guarded: refuse an externally managed environment, one pip call, pip check after, scripts only from inside the package."""

from __future__ import annotations

import os
import sys
import sysconfig
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence

from esoi.runtime.assemble_by_name.environment_needs.closure import Member
from esoi.runtime.assemble_by_name.installation.command_running import Outcome, PIP_TIMEOUT, Runner, SCRIPT_TIMEOUT, run_command, tail
from esoi.runtime.assemble_by_name.installation.install_lock import InstallLock, InstallLocked
from esoi.runtime.assemble_by_name.installation.plan import Plan


def externally_managed() -> bool:
    """True when this interpreter is a system Python marked externally managed (PEP 668) and not inside a virtualenv."""
    if sys.prefix != sys.base_prefix:
        return False
    return (Path(sysconfig.get_path("stdlib")) / "EXTERNALLY-MANAGED").exists()


def in_virtualenv() -> bool:
    return sys.prefix != sys.base_prefix or bool(os.environ.get("VIRTUAL_ENV"))


def script_refusal(path: str, roots: Sequence[Path]) -> str:
    """Why a script must not run ('' when it may): it must exist, and once symlinks and ``..`` are resolved lie inside one of the
    package directories in ``roots``."""
    try:
        real = Path(path).resolve(strict=True)
    except (OSError, RuntimeError):
        return f"{path}: the file is missing or its links do not resolve"
    for root in roots:
        try:
            real.relative_to(root.resolve())
            return ""
        except (ValueError, OSError):
            continue
    return f"{path}: resolves to {real}, outside the package directory; refusing to run it"


def package_roots(members: Iterable[Member]) -> List[Path]:
    """The package directories of the closure's members: where their per-implementation files may live."""
    roots: List[Path] = []
    for member in members:
        module = sys.modules.get((getattr(member.target, "__module__", "") or "").split(".")[0])
        for folder in getattr(module, "__path__", ()) or ():
            if Path(folder) not in roots:
                roots.append(Path(folder))
    return roots


@dataclass
class Result:
    """What ``execute`` did: the exit code (0 all done, 1 a step failed or refused), the step reports, and warnings."""
    code: int = 0
    reports: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def fail(result: Result, step: str, outcome: Outcome, environ: Mapping[str, str], remedy: str) -> Result:
    why = "timed out" if outcome.timed_out else f"exit code {outcome.code}"
    result.code = 1
    result.reports.append(f"FAILED {step} ({why}); remedy: {remedy}\n{tail(outcome.output, environ)}".rstrip())
    result.reports.append("the plan is resumable: run the same command again; what is now satisfied is skipped")
    return result


def execute(selected: Plan, roots: Sequence[Path], environ: Mapping[str, str], run: Runner = run_command,
            lock_folder: Optional[Path] = None, pip_timeout: float = PIP_TIMEOUT, script_timeout: float = SCRIPT_TIMEOUT) -> Result:
    """Run the plan, in the current environment only, stopping at the first failure. Called only on ``--yes``."""
    result = Result()
    if selected.conflicts:
        result.code = 1
        result.reports.append("refusing to install: unresolved conflict; " + "; ".join(selected.options or ("see the conflicts above",)))
        return result
    if selected.empty:
        result.reports.append("nothing to install")
        return result
    for role, path in selected.scripts:   # check every script before anything runs
        refusal = script_refusal(path, roots)
        if refusal:
            result.code = 1
            result.reports.append(f"refused {role} file: {refusal}; keep install files inside the package directory")
            return result
    if (selected.pip or selected.isolated or any(role == "requirements" for role, p in selected.scripts)) and externally_managed():
        result.code = 1
        result.reports.append("this Python is externally managed (PEP 668), so pip would refuse; create or activate a virtualenv "
                              "(python -m venv .venv && . .venv/bin/activate) and run again. --break-system-packages is never used")
        return result
    if not in_virtualenv():
        result.warnings.append("not inside a virtualenv: packages will go into this interpreter's own environment")
    try:
        with InstallLock(lock_folder):
            return run_locked(selected, roots, environ, run, result, pip_timeout, script_timeout)
    except InstallLocked as error:
        result.code = 1
        result.reports.append(str(error))
        return result


def run_locked(selected: Plan, roots: Sequence[Path], environ: Mapping[str, str], run: Runner, result: Result,
               pip_timeout: float, script_timeout: float) -> Result:
    if selected.pip:
        step = "python -m pip install " + " ".join(selected.pip)
        command = [sys.executable, "-m", "pip", "install", *selected.pip]
        outcome = run(command, None, pip_timeout)   # one call for the whole set, so resolution is atomic
        if outcome.code:
            return fail(result, step, outcome, environ, "read the pip message above; widen the range it rejects or deselect that arm")
        result.reports.append(f"ok {step}")
        checked = run([sys.executable, "-m", "pip", "check"], None, pip_timeout)
        if checked.code:
            result.code = 1
            result.reports.append("pip check found conflicts after installing:\n" + tail(checked.output, environ)
                                  + "\nremedy: widen one of the ranges above or deselect an arm; the installed set is unchanged by this check")
            return result
        result.reports.append("ok pip check")
    for one in selected.isolated:
        made = run([sys.executable, "-m", "venv", one.folder], None, pip_timeout)
        if made.code:
            return fail(result, f"python -m venv {one.folder}", made, environ, "check that the venv module is installed and the folder is writable")
        inner = Path(one.folder) / ("Scripts" if os.name == "nt" else "bin") / "python"
        outcome = run([str(inner), "-m", "pip", "install", *one.specs], None, pip_timeout)
        if outcome.code:
            return fail(result, f"isolated install for {one.arm}", outcome, environ, "see the pip message; the isolated environment is separate from yours")
        result.reports.append(f"ok isolated {one.arm} ({one.boundary}) in {one.folder}")
    for role, path in selected.scripts:
        folder = str(Path(path).resolve().parent)
        if role == "shell":
            if not shutil_which("sh"):
                return fail(result, f"sh {path}", Outcome(127, "sh not found"), environ,
                            "no sh on this system (Windows?): use WSL or Git Bash, or run the steps in the file yourself")
            command = ["sh", path]
        elif role == "requirements":
            command = [sys.executable, "-m", "pip", "install", "-r", path]
        else:
            command = [sys.executable, path]
        outcome = run(command, folder, script_timeout)
        if outcome.code:
            return fail(result, " ".join(command), outcome, environ, f"fix {path}, or remove it and declare the need with REQUIRES")
        result.reports.append(f"ok {' '.join(command)}" + (("\n" + tail(outcome.output, environ, 3)) if outcome.output.strip() else ""))
    return result


def shutil_which(name: str) -> Optional[str]:
    import shutil
    return shutil.which(name)
