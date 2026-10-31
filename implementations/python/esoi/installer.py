"""Install only what the solutions in use need, safely, and keep the whole assembly coherent.

``make_plan`` turns the requirements of a closure (see ``esoi.requirements``) into a ``Plan``: one pip requirement set with every
declaration's own range, the per-implementation files to run, and what only a person can do. When declarations cannot coexist it
walks a resolution ladder, each step reported, until one works:

1. let the resolver work: the merged set, plus a constraints file of what is installed and satisfies the ranges (a dry run first);
2. widen to declared alternatives (another distribution, or a wider tested range, listed with ``python(..., alternatives=...)``);
3. choose another arm by the metric ranking, labelled as a circumstance of this environment, never silently;
4. isolate an arm that declares ``isolatable(...)`` in a virtual environment of its own under a project-local folder;
5. stop, naming the exact conflicting requirements, the arms that pull each and the options for a person.

``execute`` runs a plan only when told to: it uses ``sys.executable -m pip`` in the current environment, refuses an externally
managed one (PEP 668), takes a process lock, makes one pip call for the whole set, runs ``pip check`` after, and runs a script
only from inside the package directory. Every runner is injectable so tests touch no environment and no network. Output shown
or returned never contains a variable's value.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import sysconfig
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import requirements as req

PIP_TIMEOUT = 900.0
SCRIPT_TIMEOUT = 600.0
TAIL_LINES = 20


# running things (injectable)

@dataclass(frozen=True)
class Outcome:
    """What a command did: its exit code, the tail of its output, and whether it timed out."""
    code: int
    output: str = ""
    timed_out: bool = False


Runner = Callable[[Sequence[str], Optional[str], float], Outcome]


def run_command(command: Sequence[str], cwd: Optional[str] = None, timeout: float = PIP_TIMEOUT) -> Outcome:
    """Run a command, capturing output; a missing program or a timeout is an ``Outcome``, never an exception."""
    try:
        done = subprocess.run(list(command), cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        return Outcome(124, str(error.stdout or "") + str(error.stderr or ""), True)
    except OSError as error:
        return Outcome(127, f"{command[0]}: {error}")
    return Outcome(done.returncode, (done.stdout or "") + (done.stderr or ""))


def scrub(text: str, environ: Mapping[str, str]) -> str:
    """The text with every secret-looking value of the environment replaced by ``***`` (values of four characters or more)."""
    for value in sorted({str(v).strip() for v in environ.values() if len(str(v).strip()) >= 4}, key=len, reverse=True):
        text = text.replace(value, "***")
    return text


def tail(text: str, environ: Mapping[str, str], lines: int = TAIL_LINES) -> str:
    """The last lines of captured output, scrubbed."""
    return "\n".join(scrub(text, environ).strip().splitlines()[-lines:])


# conflicts

@dataclass(frozen=True)
class Conflict:
    """Requirements on one distribution that cannot all hold: each ``(specifier, arms)`` and why."""
    distribution: str
    pulls: Tuple[Tuple[str, Tuple[str, ...]], ...]
    reason: str

    def text(self) -> str:
        return f"{self.distribution}: " + "; ".join(f"{spec or 'any version'} (pulled by {', '.join(arms)})" for spec, arms in self.pulls) \
            + f" -> {self.reason}"


def arm_of(label: str) -> str:
    return label.split(" via ")[0]


def python_entries(entries: Sequence[req.Entry]) -> List[Tuple[req.Python, req.Parsed, Tuple[str, ...]]]:
    """The python requirements that apply here (their marker holds), parsed, with the arms that pull each."""
    out = []
    for entry in entries:
        item = entry.requirement
        if isinstance(item, req.Python):
            parsed = item.parsed
            if not parsed.marker or req.marker_applies(parsed.marker):
                out.append((item, parsed, tuple(dict.fromkeys(arm_of(label) for label in entry.used_by))))
    return out


def candidate_versions(specs: Iterable[str]) -> List[Any]:
    """Versions around every version the specifiers mention, to test whether their intersection is empty."""
    from packaging.version import InvalidVersion, Version
    found = {Version("0"), Version("0.0.1"), Version("9999")}
    for spec in specs:
        for number in re.findall(r"\d+(?:\.\d+)*(?:[a-z]+\d*)?", spec):
            try:
                base = Version(number)
            except InvalidVersion:
                continue
            release = list(base.release)
            found.add(base)
            for position in range(len(release)):
                for delta in (-1, 1):
                    bumped = release[:]
                    bumped[position] = max(bumped[position] + delta, 0)
                    found.add(Version(".".join(map(str, bumped))))
            found.add(Version(".".join(map(str, release + [1]))))
    return sorted(found)


def satisfiable(specs: Sequence[str]) -> Tuple[bool, str]:
    """``(ok, reason)``: whether one version can satisfy every specifier. With ``packaging``, the intersection is tested over
    versions around every bound; without it, only two different exact pins are found."""
    given = [spec for spec in specs if spec]
    pins = {spec[2:] for spec in given if spec.startswith("==") and not spec.startswith("===") and "," not in spec}
    if len(pins) > 1:
        return False, "two different exact pins: " + ", ".join(sorted(pins))
    parts = req.packaging_parts()
    if parts is None or not given:
        return True, ""
    try:
        combined = parts[0](",".join(given))
        ok = any(combined.contains(version, prereleases=True) for version in candidate_versions(given))
    except Exception as error:
        return True, f"specifiers not compared ({type(error).__name__})"
    return (True, "") if ok else (False, f"no version satisfies {','.join(given)}")


def find_conflicts(entries: Sequence[req.Entry]) -> List[Conflict]:
    """The offline conflicts: distributions whose declared specifiers have an empty intersection, in a stable order."""
    grouped: Dict[str, List[Tuple[str, Tuple[str, ...]]]] = {}
    names: Dict[str, str] = {}
    for item, parsed, arms in python_entries(entries):
        grouped.setdefault(parsed.key, []).append((parsed.specifier, arms))
        names[parsed.key] = parsed.name
    out = []
    for key in sorted(grouped):
        ok, reason = satisfiable([spec for spec, arms in grouped[key]])
        if not ok:
            out.append(Conflict(names[key], tuple(sorted(set(grouped[key]))), reason))
    return out


def merged_specs(entries: Sequence[req.Entry]) -> List[str]:
    """One pip requirement per distribution: extras united, every declaration's own range kept (never tighter)."""
    extras: Dict[str, set] = {}
    specs: Dict[str, List[str]] = {}
    names: Dict[str, str] = {}
    for item, parsed, arms in python_entries(entries):
        extras.setdefault(parsed.key, set()).update(parsed.extras)
        names[parsed.key] = parsed.name
        specs.setdefault(parsed.key, [])
        if parsed.specifier and parsed.specifier not in specs[parsed.key]:
            specs[parsed.key].append(parsed.specifier)
    return [req.Parsed(names[key], tuple(sorted(extras[key])), ",".join(specs[key])).spec() for key in sorted(names)]


def needs_install(entries: Sequence[req.Entry]) -> List[req.Entry]:
    """The python entries not already satisfied (unmet, or a version that cannot be verified: pip will decide)."""
    return [entry for entry, one in zip(entries, req.check(entries, {})) if isinstance(entry.requirement, req.Python) and one.status != req.MET]


def installed_constraints(entries: Sequence[req.Entry]) -> List[str]:
    """``name==version`` for each requested distribution already installed at a version its ranges allow: what the resolver
    should keep when it can."""
    import importlib.metadata as metadata
    lines = []
    parts = req.packaging_parts()
    ranges: Dict[str, List[str]] = {}
    names: Dict[str, str] = {}
    for item, parsed, arms in python_entries(entries):
        ranges.setdefault(parsed.key, []).append(parsed.specifier)
        names[parsed.key] = parsed.name
    for key in sorted(names):
        try:
            version = metadata.version(names[key])
        except metadata.PackageNotFoundError:
            continue
        combined = ",".join(spec for spec in ranges[key] if spec)
        if combined and parts is not None:
            try:
                if not parts[0](combined).contains(version, prereleases=True):
                    continue
            except Exception:
                continue
        lines.append(f"{names[key]}=={version}")
    return lines


Resolver = Callable[[Sequence[str], Sequence[str]], Outcome]


def pip_resolver(run: Runner = run_command, python: Optional[str] = None) -> Resolver:
    """A resolver that asks pip for a dry run (``--dry-run --report -``, pip 22.2 or later) of the requirement set, optionally
    with a constraints file. It changes nothing."""
    def resolve(specs: Sequence[str], constraints: Sequence[str]) -> Outcome:
        with tempfile.TemporaryDirectory() as work:
            command = [python or sys.executable, "-m", "pip", "install", "--dry-run", "--quiet", "--report", str(Path(work) / "report.json"), *specs]
            if constraints:
                path = Path(work) / "constraints.txt"
                path.write_text("\n".join(constraints) + "\n", encoding="utf-8")
                command += ["-c", str(path)]
            return run(command, None, PIP_TIMEOUT)
    return resolve


# the plan

@dataclass(frozen=True)
class Substitution:
    """A seat whose selected arm cannot coexist with the others here, and the arm used instead (a circumstance, not a default)."""
    solution_id: str
    selected: str
    using: str
    because: str

    def text(self) -> str:
        return f"{self.solution_id}: selected {self.selected}; using {self.using} here because {self.because}"


@dataclass(frozen=True)
class Isolated:
    """An arm installed in a virtual environment of its own, reached through its declared process boundary."""
    arm: str
    boundary: str
    folder: str
    specs: Tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    """What installing the closure would do, in order, and everything the ladder decided.

    ``pip`` is the one requirement set for the current environment; ``constraints`` the installed versions to keep;
    ``scripts`` are ``(role, path)`` in the order install.sh, requirements.txt, install.py per implementation; ``isolated`` arms
    get their own environments; ``substitutions`` name arms used instead of the selected ones; ``steps`` is the ladder log;
    ``conflicts`` is non-empty only when no step worked (then nothing is installed); ``binaries`` and ``missing`` are for a person."""
    pip: Tuple[str, ...] = ()
    constraints: Tuple[str, ...] = ()
    scripts: Tuple[Tuple[str, str], ...] = ()
    isolated: Tuple[Isolated, ...] = ()
    substitutions: Tuple[Substitution, ...] = ()
    steps: Tuple[str, ...] = ()
    conflicts: Tuple[str, ...] = ()
    options: Tuple[str, ...] = ()
    binaries: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.pip or self.scripts or self.isolated)

    @property
    def coherent(self) -> bool:
        return not self.conflicts

    @property
    def adjusted(self) -> bool:
        """True when the selected arms did not coexist as declared and the ladder had to act (or failed): what CI should flag."""
        return bool(self.conflicts or self.substitutions or self.isolated or any("instead of" in step for step in self.steps))


Fallback = Callable[[Sequence[Conflict], Sequence[req.Entry]], Optional[Tuple[Substitution, List[req.Entry]]]]


def trial(entries: Sequence[req.Entry], resolver: Optional[Resolver], with_constraints: bool = True) -> Tuple[List[Conflict], List[str]]:
    """Conflicts of the entries: the offline intersection, then (when a resolver is given) pip's dry run, first with the
    installed versions as constraints and, if that fails, without them. Returns the conflicts and the ladder log lines."""
    log: List[str] = []
    conflicts = find_conflicts(entries)
    if conflicts or resolver is None:
        return conflicts, log
    specs = merged_specs(needs_install(entries))
    if not specs:
        return [], log
    kept = installed_constraints(entries) if with_constraints else []
    outcome = resolver(specs, kept)
    if outcome.code and kept:
        log.append("resolver: failed with the installed versions as constraints; retrying without them")
        outcome = resolver(specs, [])
    if outcome.code:
        return [Conflict("(resolver)", ((" ".join(specs), ()),), tail(outcome.output, {}, 8) or "pip could not resolve the set")], log
    return [], log


def options_for(conflicts: Sequence[Conflict]) -> List[str]:
    """Concrete choices for a person: which range to widen and which arm to deselect, per conflict."""
    out = []
    for one in conflicts:
        for spec, arms in one.pulls:
            if arms:
                out.append(f"widen {one.distribution} {spec or '(any)'} declared by {', '.join(arms)}, or deselect one of those arms "
                           f"(AssemblyConfig names={{...}} / esoi select)")
        if not any(arms for spec, arms in one.pulls):
            out.append(f"run `python -m pip install --dry-run {one.distribution}` to see which requirement pip rejects")
    return list(dict.fromkeys(out))


def alternatives_step(entries: Sequence[req.Entry], conflicts: Sequence[Conflict], resolver: Optional[Resolver],
                      steps: List[str]) -> Optional[List[req.Entry]]:
    """Ladder step 2: swap a conflicting declaration for one of its declared alternatives; the first swap that leaves no conflict wins."""
    keys = {re.sub(r"[-_.]+", "-", one.distribution).lower() for one in conflicts}
    for index, entry in enumerate(entries):
        item = entry.requirement
        if not isinstance(item, req.Python) or item.parsed.key not in keys:
            continue
        for alternative in item.alternatives:
            swapped = list(entries)
            swapped[index] = replace(entry, requirement=replace(item, distribution=alternative, alternatives=()))
            remaining, log = trial(swapped, resolver)
            if not remaining:
                steps.append(f"2. alternatives: {item.module} uses {alternative} instead of {item.distribution}; no conflict")
                return swapped
    steps.append("2. alternatives: none of the declared alternatives resolves the conflict" if any(
        isinstance(e.requirement, req.Python) and e.requirement.alternatives for e in entries) else "2. alternatives: none declared")
    return None


def isolate_step(entries: Sequence[req.Entry], conflicts: Sequence[Conflict], project: Path,
                 steps: List[str]) -> Optional[Tuple[List[req.Entry], List[Isolated]]]:
    """Ladder step 4: move the python requirements of an arm that declares ``isolatable`` into a virtual environment of its own."""
    boundaries: Dict[str, str] = {}
    for entry in entries:
        if isinstance(entry.requirement, req.Isolate):
            for label in entry.used_by:
                boundaries[arm_of(label)] = entry.requirement.boundary
    pulled = {arm for one in conflicts for spec, arms in one.pulls for arm in arms}
    for arm in sorted(pulled):
        if arm not in boundaries:
            continue
        own = [e for e in entries if isinstance(e.requirement, req.Python) and arm in {arm_of(label) for label in e.used_by}]
        rest = [e for e in entries if e not in own]
        if not own or find_conflicts(rest):
            continue
        folder = str(project / ".esoi" / "venvs" / re.sub(r"[^A-Za-z0-9_.-]+", "-", arm))
        steps.append(f"4. isolate: {arm} installs in its own environment at {folder} and is reached through its {boundaries[arm]} boundary")
        return rest, [Isolated(arm, boundaries[arm], folder, tuple(merged_specs(own)))]
    steps.append("4. isolate: no conflicting arm declares isolatable(...)")
    return None


def make_plan(entries: Sequence[req.Entry], environ: Mapping[str, str], resolver: Optional[Resolver] = None,
              fallback: Optional[Fallback] = None, project: Optional[Path] = None, notes: Sequence[str] = ()) -> Plan:
    """The install plan for the entries, with the resolution ladder applied when they conflict (see the module docstring).
    Nothing already satisfied is reinstalled; nothing is changed."""
    steps: List[str] = []
    substitutions: List[Substitution] = []
    isolated: List[Isolated] = []
    current = list(entries)
    conflicts, log = trial(current, resolver)
    steps += log
    steps.append("1. resolver: the merged ranges coexist" if not conflicts else
                 "1. resolver: " + "; ".join(one.text() for one in conflicts))
    if conflicts:
        swapped = alternatives_step(current, conflicts, resolver, steps)
        if swapped is not None:
            current, conflicts = swapped, []
    if conflicts and fallback is not None:
        found = fallback(conflicts, current)
        if found is not None:
            substitutions.append(found[0])
            current = found[1]
            conflicts, log = trial(current, resolver)
            steps.append("3. another arm: " + found[0].text())
        else:
            steps.append("3. another arm: no compatible arm among the seat's alternatives")
    elif conflicts:
        steps.append("3. another arm: not available here (no assembly to choose from)")
    if conflicts:
        moved = isolate_step(current, conflicts, project or Path.cwd(), steps)
        if moved is not None:
            current = moved[0]
            isolated += moved[1]
            conflicts = find_conflicts(current)
    if conflicts:
        steps.append("5. stop: no step resolved the conflict; nothing will be installed")
    scripts: List[Tuple[str, str]] = []
    binaries: List[str] = []
    missing: List[str] = []
    for entry, one in zip(current, req.check(current, environ)):
        item = entry.requirement
        if isinstance(item, req.ScriptFile):
            scripts.append((item.role, item.path))
        elif isinstance(item, req.Binary) and one.status != req.MET:
            binaries.append(f"{item.name}: {one.remedy}")
        elif one.blocking and not isinstance(item, req.Python):
            missing.append(f"{item.label}: {one.remedy}")
        elif isinstance(item, req.Download) and one.failing:
            missing.append(f"{item.label}: {one.remedy}")
    order = {role: position for position, (name, role) in enumerate(req.SCRIPT_ROLES)}
    scripts.sort(key=lambda pair: (str(Path(pair[1]).parent), order.get(pair[0], 9)))
    pip = () if conflicts else tuple(merged_specs(needs_install(current)))
    constraints = tuple(installed_constraints(current)) if pip else ()
    return Plan(pip, constraints, tuple(scripts), tuple(isolated), tuple(substitutions), tuple(steps),
                tuple(one.text() for one in conflicts), tuple(options_for(conflicts)), tuple(binaries), tuple(missing), tuple(notes))


def plan_text(selected: Plan, members: Sequence[req.Member] = ()) -> str:
    """The plan as text: the closure with reasons, the ladder, what would run, what a person must still do."""
    lines: List[str] = []
    if members:
        lines += ["closure:"] + [f"  {line}" for line in req.explain_closure(members)]
    if selected.steps and (selected.conflicts or selected.substitutions or selected.isolated):
        lines += ["resolution:"] + [f"  {step}" for step in selected.steps]
    for one in selected.substitutions:
        lines.append(f"substitution: {one.text()}")
    for one in selected.conflicts:
        lines.append(f"CONFLICT {one}")
    for text in selected.options:
        lines.append(f"option: {text}")
    lines.append("nothing to install" if selected.empty and not selected.conflicts else "would run:")
    if selected.pip:
        lines.append("  python -m pip install " + " ".join(f"'{spec}'" for spec in selected.pip) + "  (then pip check)")
    for one in selected.isolated:
        lines.append(f"  python -m venv {one.folder}; {one.folder}/bin/python -m pip install " + " ".join(f"'{spec}'" for spec in one.specs))
    for role, path in selected.scripts:
        lines.append("  " + {"requirements": "python -m pip install -r ", "shell": "sh ", "python": "python "}.get(role, "") + path)
    for text in selected.binaries:
        lines.append(f"you must install: {text}")
    for text in selected.missing:
        lines.append(f"you must provide: {text}")
    for text in selected.notes:
        lines.append(f"note: {text}")
    return "\n".join(lines) + "\n"


def plan_json(selected: Plan, members: Sequence[req.Member] = ()) -> Dict[str, Any]:
    """The plan as plain data under a versioned schema (names only, never values)."""
    return {"schema": "esoi.install/1", "closure": req.explain_closure(members), "steps": list(selected.steps), "pip": list(selected.pip),
            "constraints": list(selected.constraints), "scripts": [{"role": r, "path": p} for r, p in selected.scripts],
            "isolated": [vars(one) | {"specs": list(one.specs)} for one in selected.isolated],
            "substitutions": [vars(one) for one in selected.substitutions], "conflicts": list(selected.conflicts),
            "options": list(selected.options), "binaries": list(selected.binaries), "missing": list(selected.missing),
            "notes": list(selected.notes), "coherent": selected.coherent}


# safety

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


def package_roots(members: Iterable[req.Member]) -> List[Path]:
    """The package directories of the closure's members: where their per-implementation files may live."""
    roots: List[Path] = []
    for member in members:
        module = sys.modules.get((getattr(member.target, "__module__", "") or "").split(".")[0])
        for folder in getattr(module, "__path__", ()) or ():
            if Path(folder) not in roots:
                roots.append(Path(folder))
    return roots


class InstallLocked(RuntimeError):
    """Another install is running in this environment."""


class InstallLock:
    """A process lock so two installs cannot run at once in one environment (a lock file per interpreter prefix)."""

    def __init__(self, folder: Optional[Path] = None):
        import hashlib
        name = "esoi-install-" + hashlib.sha1(sys.prefix.encode()).hexdigest()[:12] + ".lock"
        self.path = (folder or Path(tempfile.gettempdir())) / name
        self.handle: Any = None

    def __enter__(self) -> "InstallLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "a+")
        try:
            import fcntl
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:   # no fcntl (Windows): fall back to an exclusive marker file
            self.handle.close()
            try:
                self.handle = os.fdopen(os.open(str(self.path) + ".run", os.O_CREAT | os.O_EXCL | os.O_WRONLY), "w")
            except FileExistsError:
                raise InstallLocked(f"another install holds {self.path}.run; wait for it, or delete the file if it is stale") from None
        except OSError:
            self.handle.close()
            raise InstallLocked(f"another esoi install is running in this environment (lock {self.path}); wait for it to finish") from None
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            if self.handle is not None:
                self.handle.close()
            marker = Path(str(self.path) + ".run")
            if marker.exists():
                marker.unlink()
        except OSError:
            pass


# executing

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


# an assembly: closure, plan, coherence

def assembly_plan(assembler: Any, config: Any, environ: Mapping[str, str], solutions: Sequence[str] = (), every_arm: bool = False,
                  resolver: Optional[Resolver] = None, rank: Optional[Callable[[str, str], Sequence[str]]] = None,
                  lead: Optional[Callable[[str], Optional[float]]] = None, project: Optional[Path] = None
                  ) -> Tuple[Plan, List[req.Member]]:
    """The install plan for what the solutions use (their selected arms, the arms that fill their needs, and the modules each
    imports), with the ladder applied. ``rank(solution_id, selected)`` gives the arms to try instead, best first by the metric
    (default: the other names in order); ``lead(solution_id)`` says how large the selected arm's recorded lead over its runner-up
    is (None: none recorded), so the least important seat gives way first. Returns the plan and the closure it describes."""
    from .assemble import AssemblyConfig
    base = config or AssemblyConfig()
    state: Dict[str, Any] = {"members": assembler.closure(base, None, solutions, every_arm)}
    notes: List[str] = []
    entries = req.gather(req.members_pairs(state["members"], notes))
    names = dict(base.names)
    orders: Dict[Tuple[str, str], Tuple[List[str], Optional[float], str]] = {}

    def order_of(sid: str, name: str) -> Tuple[List[str], Optional[float], str]:
        if (sid, name) not in orders:
            orders[(sid, name)] = assembler.metric_order(sid, name)
            notes.append(orders[(sid, name)][2])
        return orders[(sid, name)]

    def metric_rank(sid: str, name: str) -> List[str]:
        return order_of(sid, name)[0]

    def metric_lead(sid: str, name: str) -> Optional[float]:
        return order_of(sid, name)[1]

    def fallback(conflicts: Sequence[Conflict], current: Sequence[req.Entry]) -> Optional[Tuple[Substitution, List[req.Entry]]]:
        pulled = {arm for one in conflicts for spec, arms in one.pulls for arm in arms}
        seats = [m.label for m in state["members"] if m.label in pulled]
        seats.sort(key=lambda label: (lead(label.split(":", 1)[0]) if lead else metric_lead(label.split(":", 1)[0], label.split(":", 1)[1])) or 0.0)
        for label in seats:
            sid, name = label.split(":", 1)
            for alternative in [a for a in (rank(sid, name) if rank else metric_rank(sid, name)) if a != name]:
                trial_config = replace(base, names={**names, sid: alternative})
                members = assembler.closure(trial_config, None, solutions, every_arm)
                found = req.gather(req.members_pairs(members, []))
                if not find_conflicts(found):
                    others = sorted(pulled - {label})
                    because = f"{name} conflicts with {', '.join(others) or 'the other requirements'} ({conflicts[0].reason} for {conflicts[0].distribution})"
                    names[sid] = alternative
                    state["members"] = members
                    return Substitution(sid, name, alternative, because), found
        return None

    chosen = make_plan(entries, environ, resolver, fallback, project, notes)
    return chosen, state["members"]


def venv_resolver(run: Runner = run_command) -> Tuple[Resolver, Callable[[], None]]:
    """A resolver that works in a throwaway virtualenv (so what is installed here cannot influence it), and its cleanup.
    Opt-in: it needs the network for pip's index."""
    work = tempfile.mkdtemp(prefix="esoi-coherence-")
    made = run([sys.executable, "-m", "venv", work], None, PIP_TIMEOUT)
    inner = str(Path(work) / ("Scripts" if os.name == "nt" else "bin") / "python")

    def cleanup() -> None:
        import shutil
        shutil.rmtree(work, ignore_errors=True)

    if made.code:
        cleanup()
        raise RuntimeError("could not create a temporary virtualenv: " + made.output.strip()[-200:])
    return pip_resolver(run, inner), cleanup
