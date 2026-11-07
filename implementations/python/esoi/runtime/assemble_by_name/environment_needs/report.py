"""Render requirement entries and check results as text and as JSON, and name the exit codes of the commands that use them."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from esoi.runtime.assemble_by_name.environment_needs.checking import Check
from esoi.runtime.assemble_by_name.environment_needs.declarations import Api, Binary, Download, Entry, Env, Isolate, Network, Python, Requirement, ScriptFile, Service


SCHEMA = "esoi.requirements/1"   # the "schema" field of the JSON output; a field is only ever added within a version
EXIT_MET, EXIT_UNMET, EXIT_ERROR = 0, 1, 2   # the exit codes of esoi requirements --check and esoi install


def describe_api(item: Api) -> str:
    """One line about an API: key situation, free tier and rate limit."""
    bits = [item.label, "keyless path available" if item.keyless else "key required" if item.key else "no key"]
    for text, value in (("free tier", item.free_tier), ("rate limit", item.rate_limit)):
        if value:
            bits.append(f"{text}: {value}" + (f" (as of {item.as_of})" if item.as_of else ""))
    return ", ".join(bits)


DESCRIBERS = (
    (Env, lambda item: item.label + (" (secret)" if item.secret else "") + (f", fills {item.option}" if item.option else "")),
    (Api, describe_api),
    (Python, lambda item: f"python module {item.module} from {item.pip_spec}"),
    (Binary, lambda item: f"binary {item.name} on PATH"),
    (Service, lambda item: f"service {item.name} at {item.url_env}" + (f" (default {item.default_url})" if item.default_url else "")),
    (Network, lambda item: "network access" + (f" to {item.host}" if item.host else "")),
    (Download, lambda item: f"download {item.name}" + (f", about {item.size_mb:g} MB" if item.size_mb else "")),
    (ScriptFile, lambda item: f"{item.role} file {item.path}"),
)


def describe(item: Requirement) -> str:
    """One short factual line about what the requirement is."""
    for kind, say in DESCRIBERS:
        if isinstance(item, kind):
            return say(item)
    return item.label


def report(entries: Sequence[Entry], checks: Optional[Sequence[Check]] = None) -> str:
    """A text report: one line per requirement with its status and remedy, and who uses it."""
    if not entries:
        return "no declared requirements\n"
    lines = []
    for i, entry in enumerate(entries):
        one = checks[i] if checks else None
        status = f"[{one.status}] " if one else ""
        need = "" if entry.requirement.required else " (optional)"
        line = f"{status}{describe(entry.requirement)}{need}"
        if entry.used_by:
            line += f"  <- {', '.join(entry.used_by)}"
        lines.append(line)
        if one and one.remedy:
            lines.append(f"    remedy: {one.remedy}")
    return "\n".join(lines) + "\n"


def requirement_fields(item: Requirement) -> Dict[str, Any]:
    """The set fields of a requirement as plain data (tuples as lists), with an api's key nested; never a value."""
    fields = {k: v for k, v in vars(item).items() if v not in (None, "", ()) or k == "required"}
    if isinstance(item, Api) and item.key is not None:
        fields["key"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(item.key).items() if v not in (None, "", ())}
    return {k: list(v) if isinstance(v, tuple) else v for k, v in fields.items()}


def as_json(entries: Sequence[Entry], checks: Optional[Sequence[Check]] = None, notes: Sequence[str] = ()) -> Dict[str, Any]:
    """The requirements as plain data under a versioned schema: ``{"schema", "requirements": [...], "notes": [...]}``. Names
    only: no variable's value is ever included."""
    out = []
    for i, entry in enumerate(entries):
        row: Dict[str, Any] = {**requirement_fields(entry.requirement), "used_by": list(entry.used_by)}
        if checks:
            row["status"], row["remedy"] = checks[i].status, checks[i].remedy
        out.append(row)
    return {"schema": SCHEMA, "requirements": out, "notes": list(notes)}
