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


def describe(item: Requirement) -> str:
    """One short factual line about what the requirement is."""
    if isinstance(item, Env):
        return item.label + (" (secret)" if item.secret else "") + (f", fills {item.option}" if item.option else "")
    if isinstance(item, Api):
        return describe_api(item)
    if isinstance(item, Python):
        return f"python module {item.module} from {item.pip_spec}"
    if isinstance(item, Binary):
        return f"binary {item.name} on PATH"
    if isinstance(item, Service):
        return f"service {item.name} at {item.url_env}" + (f" (default {item.default_url})" if item.default_url else "")
    if isinstance(item, Network):
        return "network access" + (f" to {item.host}" if item.host else "")
    if isinstance(item, Download):
        return f"download {item.name}" + (f", about {item.size_mb:g} MB" if item.size_mb else "")
    if isinstance(item, ScriptFile):
        return f"{item.role} file {item.path}"
    if isinstance(item, Isolate):
        return item.label
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


def as_json(entries: Sequence[Entry], checks: Optional[Sequence[Check]] = None, notes: Sequence[str] = ()) -> Dict[str, Any]:
    """The requirements as plain data under a versioned schema: ``{"schema", "requirements": [...], "notes": [...]}``. Names
    only: no variable's value is ever included."""
    out = []
    for i, entry in enumerate(entries):
        fields = {k: v for k, v in vars(entry.requirement).items() if v not in (None, "", ()) or k == "required"}
        item = entry.requirement
        if isinstance(item, Api) and item.key is not None:
            fields["key"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(item.key).items() if v not in (None, "", ())}
        for k, v in list(fields.items()):
            if isinstance(v, tuple):
                fields[k] = list(v)
        row: Dict[str, Any] = {**fields, "used_by": list(entry.used_by)}
        if checks:
            row["status"], row["remedy"] = checks[i].status, checks[i].remedy
        out.append(row)
    return {"schema": SCHEMA, "requirements": out, "notes": list(notes)}
