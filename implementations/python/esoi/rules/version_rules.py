"""Rule S34: the template version a repository records is the one this library carries.

A repository records the template version its records follow under ``[records]`` in ``esoi.toml`` (``esoi version --record``).
A repository that records none is not failed: ``esoi check`` prints one informational line (``versioning.note``).
"""
from __future__ import annotations

from typing import List

from .. import fields, intents, versioning
from .base import Context, RuleGroup

SUMMARIES = {
    "S34": "The template version recorded under `[records] template_version` in `esoi.toml` is the version this library "
           "carries (`esoi version`). When the library's is newer, the finding names the fields that changed since and the "
           "migration command if one applies; when the record is ahead of the library, the library needs upgrading. "
           "Nothing recorded is not a finding.",
}


def run(ctx: Context) -> List[str]:
    recorded, problem = versioning.recorded_version(ctx.config)
    if problem:
        return [f"S34 esoi.toml: {problem}"]
    stamp = versioning.bundled_stamp()
    current = versioning.template_version(stamp)
    if recorded is None or not current or recorded == current:
        return []
    if recorded > current:
        return [f"S34 esoi.toml: the records follow template version {recorded}, but this esoi carries version {current}; "
                "upgrade esoi"]
    bad = [f"S34 esoi.toml: the records follow template version {recorded}; this esoi carries {current}. "
           + versioning.describe(entry) for entry in versioning.since(stamp, recorded)]
    pending = fields.migrate_tree([folder for _, folder in intents.folders(ctx.config)], False) if ctx.config.intent_mode else []
    bad.append("S34 esoi.toml: " + ("run `esoi fields migrate --apply`, then " if pending else "update the records by hand where a "
               "change above affects them, then ") + f"run `esoi version --record` to record version {current}")
    return bad


GROUP = RuleGroup(SUMMARIES, run)
