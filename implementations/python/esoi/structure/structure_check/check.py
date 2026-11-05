"""Run every rule over a repository and report problems, one per line: ``RULE path: message``.

``esoi check [--strict] [--write-docs]``. Exit 0 is clean, 1 is violations. The registry is data, not code:
``components.csv`` (placement), the intent records (``problems.csv``, ``ideals.csv``, ``solutions.csv``,
``implementations.csv``, ``metrics.csv``), ``waivers.csv`` (justified exceptions, each of which must still
apply: rule S9) and the results log. The rules themselves are listed by ``esoi rules``; a repository adds its own
through ``plugins`` in its configuration (``esoi.structure.structure_check.rules.base``).

``--strict`` also rejects results recorded on uncommitted code. ``--write-docs`` first regenerates the generated
files (``COMPONENTS.md``, the tracker tabs, and anything a plugin's ``write_docs(ctx)`` produces).
"""
from __future__ import annotations

from concurrent.futures import wait
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from esoi.structure.intent_registry import intents
from esoi.optimization.leaderboard import results_log
from esoi.understanding.readable_records import readme
from esoi.structure.structure_check import rules
from esoi.structure.intent_registry.template_sync import template, versioning
from esoi.understanding.review_tracker import tracker
from esoi.structure.intent_registry.config import Config
from esoi.structure.intent_registry.registry import load as load_registry
from esoi.structure.structure_check.rules import entry_rules
from esoi.structure.structure_check.rules.base import Context
from esoi.structure.structure_check.rules.generated import render_components_doc
from esoi.runtime.implementation_selection.select import load_table
from esoi.structure.intent_registry.tables import repo_files


def build_context(config: Config, strict: bool = False, files: Optional[List[str]] = None) -> Context:
    registry = load_registry(config)
    table, error = None, ""
    if config.selection_table:
        try:
            table = dict(load_table(config.selection_table, config.root))
        except Exception as exc:   # any failure to load is the finding, reported as S14
            error = f"{type(exc).__name__}: {exc}"
    return Context(config=config, registry=registry, files=repo_files(config.root) if files is None else files,
                   template=template.load_for(config), results=results_log.latest_results(config.results_path),
                   history=results_log.all_results(config.results_path),
                   table=table, table_error=error, strict=strict)


def rule_id(line: str) -> str:
    return line.split(" ", 1)[0]


def check(config: Config, strict: bool = False, files: Optional[List[str]] = None) -> List[str]:
    """All problem lines for the repository, with disabled rules dropped and unused waivers reported (S9). Advisory findings of
    opt-in rules (S36 to S39 unless a rule is strict) are not in this list: ``check_all`` returns them beside it."""
    return check_all(config, strict, files)[0]


def check_all(config: Config, strict: bool = False, files: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
    """``(problems, advisory)``: the problem lines that fail the check, and the to-do lines of enabled opt-in rules that are not
    strict (each says its next action)."""
    with intents.session():   # the record folders are found once for the whole check (finding them globs the tree)
        return check_in_session(config, strict, files)


def check_in_session(config: Config, strict: bool, files: Optional[List[str]]) -> Tuple[List[str], List[str]]:
    """``check_all`` inside an open ``intents.session``."""
    ctx = build_context(config, strict, files)
    entry_rules.start_background(ctx)   # the entry checks wait on child processes: they run beside the other rules
    bad: List[str] = []
    for group in rules.all_groups(config):
        if all(config.is_disabled(rid) for rid in group.summaries):
            continue
        bad.extend(line for line in group.run(ctx) if not config.is_disabled(rule_id(line)))
    wait(list(ctx.background.values()))   # a started check no rule collected still ends before the check does
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
    return bad, list(ctx.advisory)


LEGACY_NOTE = ("note: this repository uses the legacy two-level layout (`overall` and detailed records); the intent layout "
               "makes intents folders and sub-intents subfolders. See docs/how-to/migrate-to-intents.md in the esoi "
               "repository, or run `esoi intent migrate`")


def notes(config: Config) -> List[str]:
    """Lines that are information, not violations: they never change the exit code."""
    return ([LEGACY_NOTE] if config.overall and not config.intent_mode else []) + versioning.note(config) + cascade_notes(config) + coherence_notes(config)


def coherence_notes(config: Config) -> List[str]:
    """Notes for intents whose solution coherence paragraph leaves out solutions (``esoi.structure.intent_registry.intents.coherence_notes``)."""
    try:
        return intents.coherence_notes(config, load_registry(config))
    except Exception:   # noqa: BLE001  a note must never be the reason the check fails
        return []


def cascade_notes(config: Config) -> List[str]:
    """One note per metric whose cascading conditionals depart from the expected order (``cascade.expectation_notes``)."""
    from esoi.optimization.leaderboard import cascade_stages
    try:
        metrics = load_registry(config).metrics
    except Exception:   # noqa: BLE001  a note must never be the reason the check fails
        return []
    return [f"note: metrics.csv {m.get('metric_id', '')}: {line}" for m in metrics
            for line in cascade_stages.expectation_notes(cascade_stages.parse(m.get("cascading_conditionals", ""))[0])]


def write_docs(config: Config, say: Callable[[str], None] = print) -> None:
    """Regenerate the generated files, then the plugins' own."""
    registry = load_registry(config)
    config.structure.mkdir(parents=True, exist_ok=True)
    (config.structure / "COMPONENTS.md").write_text(render_components_doc(registry.components, config.structure_dir), encoding="utf-8")
    if config.intent_mode:
        readme.write(config, registry, say=lambda text: None)
        from esoi.understanding.readable_records import diagram
        diagram.write(config, registry, say=lambda text: None)
    if config.tracker_dir.is_dir() or registry.solutions:
        tracker.write(config, registry, say=lambda text: None)
    ctx = build_context(config)
    for module in rules.plugins(config):
        hook = getattr(module, "write_docs", None)
        if hook:
            hook(ctx)


def run_cli(config: Config, strict: bool, write: bool, say: Callable[[str], None] = print, findings: bool = False) -> int:
    """Print the problems (they decide the exit code), then the findings of the opt-in rules S36 to S39: a count per rule, and with
    ``findings`` every line. Those findings are information: they never change the exit code."""
    if write:
        write_docs(config, say)
    bad, advisory = check_all(config, strict)
    for line in bad:
        say(line)
    if advisory:
        counts: dict = {}
        for line in advisory:
            counts[rule_id(line)] = counts.get(rule_id(line), 0) + 1
        total = ", ".join(f"{rule} {n}" for rule, n in sorted(counts.items()))
        say(f"to do: {len(advisory)} finding(s) of the advisory rules ({total}); they inform and never fail the check")
        if findings:
            for line in advisory:
                say("  " + line)
        else:
            say("  list them with `esoi check --findings`")
    elif findings:
        say("to do: no findings of the advisory rules")
    for line in notes(config):
        say(line)
    say(f"structure check: {'FAIL, ' + str(len(bad)) + ' problem(s)' if bad else 'ok'}")
    return 1 if bad else 0
