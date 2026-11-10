"""Which version of the author's skill and of the intent template this library carries, and which one a repository follows.

``esoi skill sync`` and ``esoi template sync`` copy the author's skill and template into the library. Both write what they
copied from into one small generated file, the stamp (``data/skill_version.json``, named by ``version_stamp`` in the
configuration), so the library can say which skill it follows and an adopting repository can compare its records with it:

    skill      the skill the public copy was made from: the git commit that last touched its files in the source, whether
               the source still matches that commit (``committed``), the date, a content hash of the source SKILL.md
               (so it works without git) and a hash of the shipped copy
    template   the current template version: a whole number, one more than the released template's when a field was added,
               removed or renamed since the release, else the released number (rewording a question or making a field
               optional or required never bumps it); the first 12 hex digits of the hash of the content, the skill commit
               it came from, and ``changes``: the fields added, removed, made optional or required, or reworded since the
               released template. The released template is the stamp and template CSV on the upstream default branch
               (``git show origin/<default>:<path>``); without git or that ref, the previous stamp on disk
    history    the earlier released template versions, oldest first, in the same shape (no unreleased intermediates)

The stamp holds no path and no name: commits and hashes only. It is reproducible: syncing again from the same source
changes nothing (the date is the commit date, and an uncommitted source keeps the date it was first stamped).

An adopting repository records the template version its records follow in ``esoi.toml``:

    [records]
    template_version = 1

``esoi version --record`` writes the line. Rule S34 (see ``rules/version_rules.py``) compares it with the library's.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from esoi.structure.intent_registry.config import Config

STAMP_FILE = "skill_version.json"
BUNDLED_STAMP = Path(__file__).resolve().parents[3] / "data" / STAMP_FILE
FORMAT = 1
RECORD_KEY = "template_version"
BASELINE = "baseline: the first recorded template version; earlier changes are in CHANGELOG.md"
SECTION = re.compile(r"^\s*\[(?!\[)\s*([^\]]+?)\s*\]\s*(?:#.*)?$")
TABLE_ARRAY = re.compile(r"^\s*\[\[\s*([^\]]+?)\s*\]\]\s*(?:#.*)?$")
KEY_LINE = re.compile(rf"^\s*{RECORD_KEY}\s*=")
DOTTED_LINE = re.compile(rf"^\s*records\.{RECORD_KEY}\s*=")   # at the top of the file, before any table: how `esoi init` writes it

Stamp = Dict[str, Any]


class VersionError(ValueError):
    """The stamp or the configuration line cannot be read or written."""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def copy_digest(files: Dict[str, str]) -> str:
    """One hash for a whole copy: its file names and texts, in name order."""
    return digest("".join(f"{rel}\0{text}\0" for rel, text in sorted(files.items())))


def stamp_path(config: Config) -> Optional[Path]:
    return config.root / config.version_stamp if config.version_stamp else None


def read_stamp(path: Optional[Path]) -> Stamp:
    """The stamp on disk, or an empty one when there is none yet (or it cannot be read)."""
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def render_stamp(stamp: Stamp) -> str:
    return json.dumps({"format": FORMAT, **{k: v for k, v in stamp.items() if k != "format"}}, indent=1, sort_keys=True) + "\n"


def bundled_stamp() -> Stamp:
    """The stamp this installed library ships."""
    return read_stamp(BUNDLED_STAMP)


def template_version(stamp: Stamp) -> int:
    version = stamp.get("template", {}).get("version", 0)
    return version if isinstance(version, int) else 0


def git_output(folder: Path, args: List[str]) -> Optional[str]:
    try:
        done = subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def source_identity(folder: Path, files: List[str]) -> Dict[str, Any]:
    """Where the source files stand in git: the last commit that touched them, its date, and whether they still match it.
    Without git, or outside a repository, the commit is empty and ``committed`` is false."""
    found = git_output(folder, ["log", "-1", "--format=%H %cs", "--", *files])
    commit, day = (found.split() + ["", ""])[:2] if found and found.strip() else ("", "")
    status = git_output(folder, ["status", "--porcelain", "--", *files])
    return {"commit": commit, "commit_date": day, "committed": bool(commit) and status is not None and not status.strip()}


def stamped_date(identity: Dict[str, Any], previous: Dict[str, Any], unchanged: bool, today: datetime.date) -> str:
    """The commit date when the source is committed; otherwise the date it was first stamped, so a second sync is a no-op."""
    if identity["committed"] and identity["commit_date"]:
        return identity["commit_date"]
    return previous.get("date", "") if unchanged and previous.get("date") else today.isoformat()


def skill_section(stamp: Stamp, identity: Dict[str, Any], skill_text: str, shipped: Dict[str, str],
                  today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """The ``skill`` part of the stamp for a copy made from the source now."""
    previous = stamp.get("skill", {})
    md, copy = digest(skill_text), copy_digest(shipped)
    unchanged = previous.get("skill_md_sha256") == md and previous.get("copy_sha256") == copy
    return {"commit": identity["commit"], "committed": identity["committed"],
            "date": stamped_date(identity, previous, unchanged, today or datetime.date.today()),
            "skill_md_sha256": md, "copy_sha256": copy}


def template_rows(text: str) -> Dict[Tuple[str, str], Dict[str, str]]:
    return {(row["entity"], row["field_key"]): row for row in csv.DictReader(io.StringIO(text))}


def field_changes(old_csv: str, new_csv: str) -> List[str]:
    """What changed between two parsed templates, one line per field, in the new template's order, then the removed ones."""
    old, new = template_rows(old_csv), template_rows(new_csv)
    out: List[str] = []
    for key, row in new.items():
        name = f"{key[0]}.{key[1]}"
        if key not in old:
            out.append(f"{name}: added ({'required' if row['required'] == 'yes' else 'optional'})")
            continue
        before = old[key]
        if before["required"] != row["required"]:
            out.append(f"{name}: made {'required' if row['required'] == 'yes' else 'optional'}")
        if before["group"] != row["group"]:
            out.append(f"{name}: moved from the {before['group']} fields to the {row['group']} fields")
        if before["question"] != row["question"]:
            out.append(f"{name}: question reworded")
    out.extend(f"{key[0]}.{key[1]}: removed" for key in old if key not in new)
    return out


def released_state(folder: Path, stamp_file: Path, template_file: Path) -> Optional[Tuple[Stamp, str]]:
    """The stamp and the template CSV as the upstream default branch holds them (``git show <remote>/<default>:<path>``), or None
    when git, the remote ref, or either file there is unavailable. The default branch is the one ``refs/remotes/origin/HEAD``
    names, else ``origin/main``."""
    top = git_output(folder, ["rev-parse", "--show-toplevel"])
    if not top:
        return None
    head = git_output(folder, ["symbolic-ref", "refs/remotes/origin/HEAD"])
    ref = head.strip().removeprefix("refs/remotes/") if head and head.strip() else "origin/main"
    texts = []
    for path in (stamp_file, template_file):
        try:
            rel = path.resolve().relative_to(Path(top.strip()).resolve()).as_posix()
        except ValueError:
            return None
        found = git_output(folder, ["show", f"{ref}:{rel}"])
        if found is None:
            return None
        texts.append(found)
    try:
        stamp = json.loads(texts[0])
    except ValueError:
        return None
    return (stamp, texts[1]) if isinstance(stamp, dict) and stamp.get("template") else None


def template_stamp(stamp: Stamp, old_csv: str, new_csv: str, identity: Dict[str, Any], skill_text: str,
                   today: Optional[datetime.date] = None, released: Optional[Tuple[Stamp, str]] = None) -> Stamp:
    """The whole stamp after a template sync. The version is compared with the released template (``released``: its stamp and
    CSV; without it, the previous stamp and ``old_csv``): it is the released version plus one when a field was added, removed or
    renamed (the set of entity and field key differs), however many syncs came before, and the released version otherwise, so
    rewording a question or making a field optional never bumps. ``changes`` list the content now against the released template.
    The history holds released versions only."""
    today = today or datetime.date.today()
    sha, md = digest(new_csv)[:12], digest(skill_text)
    current = stamp.get("template") or {}
    if released is None:
        if current and current.get("sha256") == sha:   # nothing changed since the last sync: refresh the identity only
            entry = {**current, "skill_commit": identity["commit"], "skill_committed": identity["committed"], "skill_md_sha256": md,
                     "date": stamped_date(identity, current, current.get("skill_md_sha256") == md, today)}
            return {**stamp, "template": entry}
        released = ({**stamp, "history": list(stamp.get("history", []))}, old_csv)
    base_stamp, base_csv = released
    base = base_stamp.get("template") or {}
    history = list(base_stamp.get("history", []))
    if not base:
        version, changes = 1, [BASELINE]
    else:
        grew = set(template_rows(base_csv)) != set(template_rows(new_csv))
        version = base.get("version", 0) + 1 if grew else base.get("version", 0)
        if grew:
            history.append(base)
        changes = field_changes(base_csv, new_csv)
    previous = current if current.get("sha256") == sha else {}
    entry = {"version": version, "sha256": sha, "changes": changes,
             "skill_commit": identity["commit"], "skill_committed": identity["committed"], "skill_md_sha256": md,
             "date": stamped_date(identity, previous, bool(previous) and previous.get("skill_md_sha256") == md, today)}
    return {**stamp, "template": entry, "history": history}


def since(stamp: Stamp, recorded: int) -> List[Dict[str, Any]]:
    """The template versions after ``recorded``, oldest first, each with its date, skill commit and changes."""
    every = list(stamp.get("history", [])) + ([stamp["template"]] if stamp.get("template") else [])
    return [entry for entry in every if entry.get("version", 0) > recorded]


def describe(entry: Dict[str, Any]) -> str:
    """One version in a line: its number, date, skill commit and what changed."""
    commit = entry.get("skill_commit", "")[:7]
    head = f"template {entry.get('version')} ({entry.get('date', '')}" + (f", skill {commit})" if commit else ")")
    return head + ": " + ("; ".join(entry.get("changes", [])) or "no field change")


def recorded_version(config: Config) -> Tuple[Optional[int], str]:
    """(the template version the repository records, a problem). Both empty when nothing is recorded."""
    table = config.records if isinstance(config.records, dict) else {}
    if RECORD_KEY not in table:
        return None, ""
    value = table[RECORD_KEY]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None, f"[records] {RECORD_KEY} must be a whole number of 1 or more, not {value!r}"
    return value, ""


def record_key_line(lines: List[str]) -> Tuple[Optional[int], bool, int]:
    """Where the record key sits in the lines of ``esoi.toml``: (its line index or None, whether it is written dotted outside any section,
    the index of the ``[records]`` header or -1)."""
    section, header = "", -1
    for index, line in enumerate(lines):
        if TABLE_ARRAY.match(line):
            section = TABLE_ARRAY.match(line).group(1)
        elif SECTION.match(line):
            section = SECTION.match(line).group(1)
            header = index if section == "records" else header
        elif (section == "records" and KEY_LINE.match(line)) or (section == "" and DOTTED_LINE.match(line)):
            return index, section == "", header
    return None, False, header


def with_recorded_version(text: str, version: int) -> str:
    """The text of ``esoi.toml`` with ``[records] template_version`` set, changing nothing else."""
    lines = text.splitlines(keepends=True)
    found, dotted, header = record_key_line(lines)
    if found is not None:
        lines[found] = f"{'records.' if dotted else ''}{RECORD_KEY} = {version}\n"
        return check_toml("".join(lines), version)
    if header >= 0:
        lines.insert(header + 1, f"{RECORD_KEY} = {version}\n")
        return check_toml("".join(lines), version)
    tail = "" if not text or text.endswith("\n") else "\n"
    return check_toml(text + tail + ("\n" if text else "") + f"[records]\n{RECORD_KEY} = {version}\n", version)


def check_toml(text: str, version: int) -> str:
    try:
        written = tomllib.loads(text).get("records", {}).get(RECORD_KEY)
    except tomllib.TOMLDecodeError as exc:
        raise VersionError(f"the edit would make the configuration invalid TOML ({exc}); add `{RECORD_KEY} = {version}` "
                           "under [records] by hand") from exc
    if written != version:
        raise VersionError(f"`records` is defined in a way this edit cannot extend; add `{RECORD_KEY} = {version}` "
                           "under [records] by hand")
    return text


def record(config: Config, version: Optional[int] = None) -> str:
    """Write the library's template version (or ``version``) into the repository's ``esoi.toml``; return the line written."""
    if config.source is None or config.source.name != "esoi.toml":
        raise VersionError(f"add `{RECORD_KEY} = {version or template_version(bundled_stamp())}` under the [records] table "
                           "(for pyproject.toml: [tool.esoi.records]) by hand; only esoi.toml is edited here")
    wanted = version or template_version(bundled_stamp())
    if wanted < 1:
        raise VersionError("this library carries no template version to record")
    config.source.write_text(with_recorded_version(config.source.read_text(encoding="utf-8"), wanted), encoding="utf-8")
    return f"{RECORD_KEY} = {wanted}"


def note(config: Config) -> List[str]:
    """The one informational line for a repository that records no template version yet."""
    version = template_version(bundled_stamp())
    if version < 1 or RECORD_KEY in (config.records if isinstance(config.records, dict) else {}):
        return []
    return [f"note: no template version recorded; run `esoi version --record` to record that these records follow template "
            f"version {version} ([records] {RECORD_KEY} in esoi.toml), so a later template change is reported (rule S34)"]


def report(config: Optional[Config], package_version: str) -> List[str]:
    """The lines of ``esoi version``; the caller names the package version (the front door ``esoi/__init__.py`` holds it)."""
    stamp = bundled_stamp()
    skill, template = stamp.get("skill", {}), stamp.get("template", {})
    lines = [f"esoi {package_version}"]
    if skill:
        state = "" if skill.get("committed") else ", source had uncommitted changes"
        lines.append(f"skill: commit {skill.get('commit', '')[:7] or 'unknown'} ({skill.get('date', '')}{state}), "
                     f"SKILL.md sha256 {skill.get('skill_md_sha256', '')[:12]}")
    else:
        lines.append("skill: no stamp (this library has not synced the skill)")
    lines.append(f"template: version {template.get('version', 'none')}, sha256 {template.get('sha256', 'none')}")
    if config is not None:
        recorded, problem = recorded_version(config)
        lines.append(f"records: {problem}" if problem else f"records: template version {recorded}" if recorded
                     else "records: no template version recorded (run `esoi version --record`)")
    return lines
