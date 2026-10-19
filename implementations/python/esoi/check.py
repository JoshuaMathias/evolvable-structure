"""Run every rule over a repository and report problems, one per line: ``RULE path: message``.

``esoi check [--strict] [--write-docs]``. Exit 0 is clean, 1 is violations. The registry is data, not code:
``components.csv`` (placement), the intent records (``problems.csv``, ``ideals.csv``, ``solutions.csv``,
``implementations.csv``, ``metrics.csv``), ``waivers.csv`` (justified exceptions, each of which must still
apply: rule S9) and the results log. The rules themselves are listed by ``esoi rules``; a repository adds its own
through ``plugins`` in its configuration (``esoi.rules.base``).

``--strict`` also rejects results recorded on uncommitted code. ``--write-docs`` first regenerates the generated
files (``COMPONENTS.md``, the tracker tabs, and anything a plugin's ``write_docs(ctx)`` produces).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from . import intents, leaderboard, readme, rules, template, tracker
from .config import Config
from .registry import load as load_registry
from .rules.base import Context
from .rules.generated import render_components_doc
from .select import load_table
from .tables import repo_files


def build_context(config: Config, strict: bool = False, files: Optional[List[str]] = None) -> Context:
    registry = load_registry(config)
    table, error = None, ""
    if config.selection_table:
        try:
            table = dict(load_table(config.selection_table, config.root))
        except Exception as exc:   # any failure to load is the finding, reported as S14
            error = f"{type(exc).__name__}: {exc}"
    return Context(config=config, registry=registry, files=repo_files(config.root) if files is None else files,
                   template=template.load_for(config), results=leaderboard.latest_results(config.results_path),
                   history=leaderboard.all_results(config.results_path),
                   table=table, table_error=error, strict=strict)


def rule_id(line: str) -> str:
    return line.split(" ", 1)[0]


def check(config: Config, strict: bool = False, files: Optional[List[str]] = None) -> List[str]:
    """All problem lines for the repository, with disabled rules dropped and unused waivers reported (S9)."""
    ctx = build_context(config, strict, files)
    bad: List[str] = []
    for group in rules.all_groups(config):
        if all(config.is_disabled(rid) for rid in group.summaries):
            continue
        bad.extend(line for line in group.run(ctx) if not config.is_disabled(rule_id(line)))
    if not config.is_disabled("S9"):
        for w in ctx.registry.waivers:
            if config.is_disabled(w["rule"]):
                continue
            if (w["rule"], w["path"]) not in ctx.used_waivers:
                bad.append(f"S9 {w['rule']} {w['path']}: waiver no longer needed, delete it")
            if not w["reason"].strip():
                bad.append(f"S9 {w['rule']} {w['path']}: waiver has no reason")
    if ctx.modules is not None:
        ctx.modules.save(keep=set(ctx.files))
    return bad


LEGACY_NOTE = ("note: this repository uses the legacy two-level layout (`overall` and detailed records); the intent layout "
               "makes intents folders and sub-intents subfolders. See docs/guides/migrate-to-intents.md in the esoi "
               "repository, or run `esoi intent migrate`")


def notes(config: Config) -> List[str]:
    """Lines that are information, not violations: they never change the exit code."""
    return [LEGACY_NOTE] if config.overall and not config.intent_mode else []


def write_docs(config: Config, say: Callable[[str], None] = print) -> None:
    """Regenerate the generated files, then the plugins' own."""
    registry = load_registry(config)
    config.structure.mkdir(parents=True, exist_ok=True)
    (config.structure / "COMPONENTS.md").write_text(render_components_doc(registry.components, config.structure_dir), encoding="utf-8")
    if config.intent_mode:
        for intent in intents.discover(config):
            (intent.folder / "README.md").write_text(readme.render(registry, intent), encoding="utf-8")
    if config.tracker_dir.is_dir() or registry.solutions:
        tracker.write(config, registry, say=lambda text: None)
    ctx = build_context(config)
    for module in rules.plugins(config):
        hook = getattr(module, "write_docs", None)
        if hook:
            hook(ctx)


def run_cli(config: Config, strict: bool, write: bool, say: Callable[[str], None] = print) -> int:
    if write:
        write_docs(config, say)
    bad = check(config, strict)
    for line in bad:
        say(line)
    for line in notes(config):
        say(line)
    say(f"structure check: {'FAIL, ' + str(len(bad)) + ' problem(s)' if bad else 'ok'}")
    return 1 if bad else 0
