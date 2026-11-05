"""Find where the Python requirements of the arms in use cannot coexist, naming the conflicting ranges and the arms that pull each."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from esoi.runtime.assemble_by_name.environment_needs.checking import MET, check
from esoi.runtime.assemble_by_name.environment_needs.declarations import Entry, Python
from esoi.runtime.assemble_by_name.environment_needs.python_specs import Parsed, marker_applies, packaging_parts


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


def python_entries(entries: Sequence[Entry]) -> List[Tuple[Python, Parsed, Tuple[str, ...]]]:
    """The python requirements that apply here (their marker holds), parsed, with the arms that pull each."""
    out = []
    for entry in entries:
        item = entry.requirement
        if isinstance(item, Python):
            parsed = item.parsed
            if not parsed.marker or marker_applies(parsed.marker):
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
    parts = packaging_parts()
    if parts is None or not given:
        return True, ""
    try:
        combined = parts[0](",".join(given))
        ok = any(combined.contains(version, prereleases=True) for version in candidate_versions(given))
    except Exception as error:
        return True, f"specifiers not compared ({type(error).__name__})"
    return (True, "") if ok else (False, f"no version satisfies {','.join(given)}")


def find_conflicts(entries: Sequence[Entry]) -> List[Conflict]:
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


def merged_specs(entries: Sequence[Entry]) -> List[str]:
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
    return [Parsed(names[key], tuple(sorted(extras[key])), ",".join(specs[key])).spec() for key in sorted(names)]


def needs_install(entries: Sequence[Entry]) -> List[Entry]:
    """The python entries not already satisfied (unmet, or a version that cannot be verified: pip will decide)."""
    return [entry for entry, one in zip(entries, check(entries, {})) if isinstance(entry.requirement, Python) and one.status != MET]


def installed_constraints(entries: Sequence[Entry]) -> List[str]:
    """``name==version`` for each requested distribution already installed at a version its ranges allow: what the resolver
    should keep when it can."""
    import importlib.metadata as metadata
    lines = []
    parts = packaging_parts()
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
