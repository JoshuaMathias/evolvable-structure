"""The ``esoi`` command line. Each subcommand is a thin call into the module that owns the behaviour.

    esoi init [DIR] [--package NAME]       scaffold a passing example repository
    esoi check [--strict] [--write-docs]   run every rule (esoi rules lists them)
    esoi rules [--markdown]                list the rules and what each one means
    esoi template sync|check               keep the parsed intent template in step with its source
    esoi records                           check only the intent records
    esoi run COMPONENT --impl NAME [--record]   run and record one implementation over a component's cases
    esoi leaderboard [--strict]            rank the implementations of every evaluated solution
    esoi select SOLUTION [--name NAME]     show which implementation a selection table resolves
    esoi tracker build|check               build or verify the review tracker tabs
    esoi consumer check --registry CSV     check a consuming repository's integration registry
    esoi hygiene [--staged] [--history]    scan for secrets, machine paths and real addresses
    esoi sheet-sync sync|push|pull|check   two-way sync of the tracker with a Google Sheet (esoi[sheets])

``--config PATH`` (before the subcommand) names the configuration file or folder; by default the nearest
``esoi.toml`` or ``[tool.esoi]`` table from the current folder upward is used.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="esoi", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None, help="the config file, or the folder that holds it")
    parser.add_argument("--version", action="version", version=f"esoi {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="scaffold a passing example repository")
    p.add_argument("dir", nargs="?", default=".")
    p.add_argument("--package", default="", help="the package name (default: the folder name)")
    p.add_argument("--force", action="store_true", help="overwrite files that exist")
    p = sub.add_parser("check", help="run every rule")
    p.add_argument("--strict", action="store_true", help="also reject results recorded on uncommitted code")
    p.add_argument("--write-docs", action="store_true", help="regenerate the generated files first")
    p = sub.add_parser("rules", help="list the rules")
    p.add_argument("--markdown", action="store_true")
    p = sub.add_parser("template", help="the intent template")
    p.add_argument("action", choices=["sync", "check"])
    p.add_argument("--source", default=None, help="the SKILL.md-style file holding the template")
    sub.add_parser("records", help="check only the intent records")
    p = sub.add_parser("run", help="run one implementation over a component's cases", add_help=False)
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p = sub.add_parser("leaderboard", help="rank implementations")
    p.add_argument("--strict", action="store_true", help="exit 1 when a rival beats a selected implementation")
    p = sub.add_parser("select", help="show what a selection table resolves")
    p.add_argument("solution")
    p.add_argument("--name", default=None)
    p = sub.add_parser("tracker", help="the review tracker")
    p.add_argument("action", choices=["build", "check"])
    p = sub.add_parser("consumer", help="check a consuming repository")
    p.add_argument("action", choices=["check"])
    p.add_argument("--registry", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--library", default=None, help="the importable library (default: [consumer] library)")
    p.add_argument("--requirements", default=None)
    p.add_argument("--solutions", default=None)
    p.add_argument("--results", default=None)
    p.add_argument("--fail-on-lag", action="store_true")
    p = sub.add_parser("hygiene", help="scan for secrets and private data")
    p.add_argument("--root", default=".")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--history", action="store_true", help="also scan every line ever added in git history")
    p = sub.add_parser("sheet-sync", help="sync the tracker with a Google Sheet")
    p.add_argument("mode", choices=["sync", "push", "pull", "check"])
    p.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    from . import config as config_module
    if args.cmd == "init":
        from .scaffold import init
        init(Path(args.dir), args.package, args.force)
        print("next: git init && git add . && git commit, then `esoi run greet_a_person --impl live --record` "
              "and `esoi check --strict`")
        return 0
    if args.cmd == "hygiene":
        from . import hygiene
        table = {}
        try:
            table = config_module.load(args.config, Path(args.root)).hygiene
        except config_module.ConfigError:
            pass
        return hygiene.run_cli(Path(args.root), args.staged, args.history, hygiene.allowances_from(table))
    try:
        config = config_module.load(args.config)
    except config_module.ConfigError as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "check":
        from . import check
        return check.run_cli(config, args.strict, args.write_docs)
    if args.cmd == "rules":
        from . import rules
        for rid, text in rules.summaries(config).items():
            print(f"- **{rid}** {text}" if args.markdown else f"{rid:<5}{text}")
        return 0
    if args.cmd == "template":
        from . import templates
        return templates.sync(config, args.source, check=args.action == "check")
    if args.cmd == "records":
        from . import template
        from .records import check_records, overall_ids
        overall = overall_ids(config.root / config.overall) if config.overall and (config.root / config.overall).is_dir() else None
        problems = check_records(config.structure, template.load_for(config), overall=overall)
        for line in problems:
            print(line)
        return 1 if problems else 0
    if args.cmd == "run":
        from . import harness
        return harness.run_cli(args.rest, config)
    if args.cmd == "leaderboard":
        from . import leaderboard, registry
        return leaderboard.board(config, registry.load(config), args.strict)
    if args.cmd == "select":
        from .select import Selector, load_table
        if not config.selection:
            print("esoi: no selection table configured (set `selection` in the config)", file=sys.stderr)
            return 2
        selector = Selector(load_table(config.selection, config.root))
        name = selector.chosen_name(args.solution, args.name)
        print(f"{args.solution}: {name} (choices: {', '.join(selector.names(args.solution))})")
        return 0
    if args.cmd == "tracker":
        from . import registry, tracker
        loaded = registry.load(config)
        if args.action == "build":
            tracker.write(config, loaded)
            return 0
        bad = tracker.stale(config, loaded)
        print("tracker out of date: " + ", ".join(bad) if bad else "tracker ok")
        return 1 if bad else 0
    if args.cmd == "consumer":
        from . import consumer
        options = consumer.Options.from_config(config, args.library)
        report = consumer.check_consumer(Path(args.registry), Path(args.root), options,
                                         Path(args.requirements) if args.requirements else None,
                                         Path(args.solutions) if args.solutions else None,
                                         Path(args.results) if args.results else None)
        for line in report.problems:
            print(line)
        for line in report.notes:
            print(f"note: {line}")
        if report.counts:
            print("rows by kind: " + ", ".join(f"{k}={v}" for k, v in sorted(report.counts.items())))
        return 1 if report.problems or (args.fail_on_lag and report.pin_lag) else 0
    if args.cmd == "sheet-sync":
        from . import sheets
        return sheets.run_cli(config, args.mode, args.dry_run)
    return 2


if __name__ == "__main__":
    sys.exit(main())
