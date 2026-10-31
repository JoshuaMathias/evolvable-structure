"""The ``esoi`` command line. Each subcommand is a thin call into the module that owns the behaviour.

    esoi init [DIR] [--package NAME]       scaffold a passing example repository
    esoi check [--strict] [--write-docs]   run every rule (esoi rules lists them)
    esoi rules [--markdown]                list the rules and what each one means
    esoi template sync|check               keep the parsed intent template in step with its source
    esoi skill sync|check|install          the public copy of the author's skill: generate, verify, install
    esoi records [check|sync]              check only the intent records, or write the rows the code declares and they lack
    esoi new solution ID [--intent ID]     a solution in one command: records, code with declarations, evaluation folder
    esoi run COMPONENT --impl NAME [--record]   run and record one implementation over a component's cases
    esoi leaderboard [--strict]            rank the implementations of every evaluated solution
    esoi select SOLUTION [--name NAME]     show which implementation runs now, and which layer of the cascade chose it
    esoi cascade [SOLUTION] [--strict]     a metric's cascading conditionals: each stage's results, the chosen implementation, what to run next
    esoi evidence [list|grade|rank|table]  public evidence others measured, graded A to D; complementary, never a result row
    esoi select --promote [SOLUTION]       switch `selected` to the rival that clearly wins on the solution's own metric
    esoi select --snapshot FILE            write the defaults and modules for a package shipped without the records
    esoi tracker build|check               build or verify the review tracker tabs
    esoi consumer check --registry CSV     check a consuming repository's integration registry
    esoi fields migrate [--apply]          split scoped_purpose into the new solution and metric fields in every records folder (dry run without --apply)
    esoi intent migrate [--apply]          move a legacy overall layout to the intent layout (dry run without --apply)
    esoi spec index [--out FILE]|find TEXT [-k N] [--expand N]|show ID [--tier 0|1|2]|related ID [--depth N]|intent [ID] [--cache FILE]   the specification index: find the few records a new use case needs
    esoi projects init|add|list|check|index|where   the local ESOI index (a folder named by ESOI_HOME, else ~/.esoi)
    esoi version [--record]                the package version, the skill it follows, the template version; --record writes the template version into esoi.toml
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
    p = sub.add_parser("skill", help="the public copy of the author's skill")
    p.add_argument("action", choices=["sync", "check", "install"])
    p.add_argument("--source", default=None, help="sync, check: the author's skill folder (else $ESOI_SKILL_SOURCE)")
    p.add_argument("--denylist", default=None, help="check: a file of private terms (else $ESOI_SKILL_DENYLIST)")
    p.add_argument("--project", default=None, help="install: a project folder; the skill goes in its .claude/skills")
    p.add_argument("--dest", default=None, help="install: a skills folder of another agent")
    p.add_argument("--from", dest="from_dir", default=None, help="install: a skill folder to install instead of the bundled one")
    p.add_argument("--force", action="store_true", help="install: replace a different skill already there")
    p = sub.add_parser("records", help="check only the intent records, or sync the rows the code declares")
    p.add_argument("action", nargs="?", default="check", choices=["check", "sync"])
    p.add_argument("--intent", default=None, help="sync: the intent whose folder receives new rows (default: the top intent)")
    p.add_argument("--dry-run", action="store_true", help="sync: list the rows without writing them")
    p = sub.add_parser("new", help="create something new from one command")
    p.add_argument("what", choices=["solution"])
    p.add_argument("id")
    p.add_argument("--intent", default=None, help="the intent whose folder receives the records (default: the top intent)")
    p = sub.add_parser("run", help="run one implementation over a component's cases", add_help=False)
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p = sub.add_parser("leaderboard", help="rank implementations")
    p.add_argument("--strict", action="store_true", help="exit 1 when a rival beats a selected implementation")
    p = sub.add_parser("select", help="show which implementation runs, or promote a winner")
    p.add_argument("solution", nargs="?", default=None)
    p.add_argument("--name", default=None, help="per-call choice to explain (the `using=` layer)")
    p.add_argument("--promote", action="store_true", help="switch `selected` to the rival that wins on the solution's metric")
    p.add_argument("--dry-run", action="store_true", help="promote: print what would change without writing it")
    p.add_argument("--snapshot", default=None, metavar="FILE", help="write the defaults and modules as JSON for a package without the records")
    p = sub.add_parser("cascade", help="the stages of a costly metric, what each implementation reached, and what to run next")
    p.add_argument("solution", nargs="?", default="")
    p.add_argument("--strict", action="store_true", help="exit 1 when the cascade chooses another implementation than `selected`")
    p = sub.add_parser("evidence", help="public evidence: list, grade or rank what others measured, never counted as a result")
    p.add_argument("action", nargs="?", default="list", choices=["list", "grade", "rank", "table"])
    p.add_argument("--candidate", default="", help="only this candidate")
    p.add_argument("--dimension", default="", help="only this dimension")
    p.add_argument("--weights", default="", help="rank: dimension=weight pairs, such as quality=2,cost=1 (default: every dimension present, equal)")
    p.add_argument("--file", default="", help="read this evidence CSV instead of the configured one")
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
    p = sub.add_parser("spec", help="the specification index: a deterministic, non-AI map of the records")
    p.add_argument("action", choices=["index", "find", "show", "related", "intent"])
    p.add_argument("target", nargs="?", default="", help="find: the words of the use case or input; show: a record id")
    p.add_argument("-k", type=int, default=8, help="find: how many records to return")
    p.add_argument("--expand", type=int, default=0, help="find: linked records to add per hit")
    p.add_argument("--tier", type=int, default=1, choices=[0, 1, 2], help="show: 0 one line, 1 plus summary and links, 2 the full record")
    p.add_argument("--out", default=None, help="index: write the JSON here instead of printing it")
    p.add_argument("--depth", type=int, default=1, help="related: how many link steps to follow")
    p.add_argument("--cache", default=None, help="read the index from this file when the records have not changed, else rebuild it there")
    p = sub.add_parser("intent", help="the intent layout")
    p.add_argument("action", choices=["migrate"])
    p.add_argument("--apply", action="store_true", help="migrate: write the files (without it, only report the plan)")
    p = sub.add_parser("fields", help="the 2026-10-26 field change")
    p.add_argument("action", choices=["migrate"])
    p.add_argument("--apply", action="store_true", help="migrate: write the files (without it, only report the plan)")
    p = sub.add_parser("projects", help="the local ESOI index: the projects ESOI is applied to on this machine")
    p.add_argument("action", choices=["init", "add", "list", "check", "index", "where"])
    p.add_argument("target", nargs="?", default=None, help="add: a local path or URL; where: a path (default: the current folder)")
    p.add_argument("--id", default="", help="add: the project id (default: from the name)")
    p.add_argument("--name", default="")
    p.add_argument("--vision", default="", help="add: the vision statement (default: from the project's top intent)")
    p.add_argument("--kind", default="", choices=["", "repository", "folder", "file", "board"])
    p.add_argument("--specifications", default="", help="add: where its ESOI specifications are, relative to the location")
    p.add_argument("--start-here", default="", help="add: the file to read first when applying ESOI there")
    p.add_argument("--relations", default="", help="add: ';'-separated kind:project_id (uses, used-by, sub-intent-of, example-of, related)")
    p.add_argument("--notes", default="")
    p.add_argument("--replace", action="store_true", help="add: update a project that is already listed")
    p = sub.add_parser("version", help="the package, skill and template versions")
    p.add_argument("--record", action="store_true", help="record the library's template version under [records] in esoi.toml")
    p = sub.add_parser("hygiene", help="scan for secrets and private data")
    p.add_argument("--root", default=".")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--history", action="store_true", help="also scan every line ever added in git history")
    p = sub.add_parser("sheet-sync", help="sync the tracker with a Google Sheet")
    p.add_argument("mode", choices=["sync", "push", "pull", "check"])
    p.add_argument("--dry-run", action="store_true")
    return parser


def spec_command(config, args: argparse.Namespace) -> int:
    """``esoi spec``: build, search and read the specification index (no model is called)."""
    import json
    from . import spec_index
    index = spec_index.cached(config, Path(args.cache)) if args.cache else spec_index.build(config)
    if args.action == "intent":
        for entry in spec_index.of_intent(index, args.target):
            print(spec_index.line(entry))
        return 0
    if args.action == "index":
        text = json.dumps(index, indent=1, sort_keys=True) + "\n"
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out} ({index['n']} entries, digest {index['digest']})")
        else:
            print(text, end="")
        return 0
    if not args.target:
        print(f"esoi: spec {args.action} needs a {'record id' if args.action == 'show' else 'use case text'}", file=sys.stderr)
        return 2
    if args.action == "find":
        print(spec_index.render_scan(index, spec_index.find_specs(index, args.target, args.k, args.expand)))
        return 0
    if args.action == "related":
        try:
            hits = spec_index.related(index, args.target, args.depth, max(args.k, 1))
        except KeyError:
            print(f"esoi: no record {args.target!r}", file=sys.stderr)
            return 1
        by_id = {e["id"]: e for e in index["entries"]}
        print("\n".join(f"{spec_index.line(by_id[h['id']])}  (step {h['depth']} via {h['via']})" for h in hits))
        return 0
    try:
        print(spec_index.show(config, index, args.target, args.tier))
    except KeyError:
        print(f"esoi: no record {args.target!r}", file=sys.stderr)
        return 1
    return 0


def projects_command(args: argparse.Namespace) -> int:
    """``esoi projects``: the one place the index folder is resolved from ``ESOI_HOME``."""
    import os
    from . import projects
    home = projects.resolve_home(os.environ, Path.home())
    if args.action == "init":
        made = projects.init(home)
        print(f"{home}: " + (", ".join(made) + " created" if made else "already set up"))
        return 0
    if args.action == "add":
        if not args.target:
            print("esoi: projects add needs a path or URL", file=sys.stderr)
            return 2
        try:
            row = projects.add(home, args.target, args.id, args.name, args.vision, args.kind, args.specifications,
                               args.start_here, args.relations, args.notes, args.replace)
        except ValueError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        print(f"added {row['project_id']} ({row['kind']}, {row['location']})")
        if not projects.resolve([row])[0]["vision_statement"]:
            print("note: no vision statement found in the project's top intent.csv; add one there (or with --vision --replace)")
        return 0
    if args.action == "list":
        for line in projects.render_list(projects.resolve(projects.read_projects(home))):
            print(line)
        return 0
    if args.action == "check":
        bad = projects.check(home)
        for line in bad:
            print(line)
        print("esoi projects: " + (f"{len(bad)} problem(s)" if bad else "ok"))
        return 1 if bad else 0
    if args.action == "index":
        print(f"wrote {projects.index(home)}")
        return 0
    found = projects.where(home, Path(args.target or "."))
    if found is None:
        print("no listed project contains that path")
        return 1
    for line in projects.render_where(found):
        print(line)
    return 0


def select_command(config, args: argparse.Namespace) -> int:
    """``esoi select``: explain the cascade for a solution, promote a winner, or write a snapshot."""
    import json
    from . import runtime
    from .select import Selector
    if args.promote:
        from . import promote
        return promote.run_cli(config, args.solution or "", args.dry_run)
    if args.snapshot:
        Path(args.snapshot).write_text(json.dumps(runtime.snapshot(config), indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.snapshot}")
        return 0
    if not args.solution:
        print("esoi: name a solution, or use --promote or --snapshot", file=sys.stderr)
        return 2
    try:
        if config.selection_table:
            selector = Selector.from_config(config)
            if args.solution in selector.table:
                name = selector.chosen_name(args.solution, args.name)
                print(f"{args.solution}: {name} (choices: {', '.join(selector.names(args.solution))})")
                return 0
        import os
        environ = dict(os.environ, **{runtime.ROOT_ENV: str(config.root)})
        try:
            picked = runtime.choose(args.solution, args.name, environ)
        except runtime.SelectionError:
            if config.selection_table:
                Selector.from_config(config).chosen_name(args.solution, args.name)   # says "no selection table entry ..."
            raise
        print(f"{args.solution}: {picked.name} (chosen by the {picked.layer} layer; choices: "
              f"{', '.join(runtime.names(args.solution, environ))})")
        for layer, value, source in runtime.explain(args.solution, args.name, environ):
            print(f"  {layer}: {value} ({source})")
        return 0
    except (ValueError, OSError, ImportError, AttributeError) as exc:   # unknown solution or name, table cannot load
        print(f"esoi: {exc}", file=sys.stderr)
        return 2


def version_command(args: argparse.Namespace, config_module) -> int:
    """``esoi version``: works without a configuration; ``--record`` needs one."""
    from . import versioning
    try:
        config = config_module.load(args.config)
    except config_module.ConfigMissing:
        config = None
    except config_module.ConfigError as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return 2
    if args.record:
        if config is None:
            print("esoi: no esoi.toml found to record the template version in", file=sys.stderr)
            return 2
        try:
            print(f"wrote {versioning.record(config)} under [records] in {config.source.name}")
        except versioning.VersionError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        return 0
    for line in versioning.report(config):
        print(line)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if "run" in argv:   # everything after `run` belongs to the harness, flags included
        position = argv.index("run")
        args = build_parser().parse_args(argv[:position + 1])
        args.rest = argv[position + 1:]
    else:
        args = build_parser().parse_args(argv)
    from . import config as config_module
    if args.cmd == "init":
        from .scaffold import init
        init(Path(args.dir), args.package, args.force)
        print("next: write the top intent (the name and vision statement in intent.csv say why your project exists), "
              "git init && git add . && git commit, then `esoi run greet_a_person --impl live --record` and `esoi check --strict`")
        return 0
    if args.cmd == "projects":
        return projects_command(args)
    if args.cmd == "skill" and args.action == "install":
        from . import skill
        return skill.install(args.project, args.dest, args.from_dir, args.force)
    if args.cmd == "version":
        return version_command(args, config_module)
    if args.cmd == "hygiene":
        from . import hygiene
        table = {}
        try:
            table = config_module.load(args.config, Path(args.root)).hygiene
        except config_module.ConfigMissing:
            pass   # a folder with no configuration is scanned with the built-in allowances
        except config_module.ConfigError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        try:
            allow = hygiene.allowances_from(table)
        except hygiene.HygieneError as exc:
            print(f"esoi hygiene: {exc}", file=sys.stderr)
            return 2
        return hygiene.run_cli(Path(args.root), args.staged, args.history, allow)
    try:
        config = config_module.load(args.config)
    except config_module.ConfigError as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "spec":
        return spec_command(config, args)
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
    if args.cmd == "skill":
        from . import skill
        if args.action == "sync":
            return skill.sync(config, args.source)
        return skill.check(config, args.source, args.denylist)
    if args.cmd == "fields":
        from . import fields, intents
        done = fields.migrate_tree([folder for _, folder in intents.folders(config)], args.apply)
        for line in done:
            print(line)
        print(f"esoi fields migrate: {len(done)} file(s) " + ("migrated" if args.apply else "would change (dry run; pass --apply)") if done
              else "esoi fields migrate: records already use the current fields")
        return 0
    if args.cmd == "intent":
        from . import migrate
        return migrate.run_cli(config, args.apply)
    if args.cmd == "records" and args.action == "sync":
        from . import declarations, registry
        try:
            done = declarations.sync(config, registry.load(config), declarations.scan(config), args.intent, not args.dry_run)
        except ValueError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        for line in done:
            print(line)
        print("esoi records sync: " + (f"{len(done)} change(s)" + (" (dry run)" if args.dry_run else ", now fill the text only a person can write; `esoi check` names it") if done else "records already match the declarations"))
        return 0
    if args.cmd == "new":
        from . import newsolution
        try:
            written = newsolution.create(config, args.id, args.intent)
        except ValueError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        for rel in written:
            print(f"wrote {rel}")
        print("next: write the text only you can (esoi check names it), then `esoi check --write-docs`, commit, and "
              "`esoi run <component> --impl simple --record`")
        return 0
    if args.cmd == "records":
        from . import registry, template
        from .records import check_records, check_headers, overall_ids, tables_of
        if config.intent_mode:
            from . import intents
            loaded, tpl = registry.load(config), template.load_for(config)
            tree = tables_of(loaded)
            every = {e: {r.get(k, "") for r in tree[e]} - {""} for e, k in
                     {"problem": "problem_id", "ideal": "ideal_id", "solution": "solution_id",
                      "implementation": "implementation_id", "metric": "metric_id"}.items()}
            problems = [line for _, folder in intents.folders(config) for line in check_headers(folder, tpl, approved=config.approved_fields, metric_command=config.metric_command)]
            problems += check_records(config.structure, tpl, overall=every, tables=tree, retired={"overall_solution_ids"}, scope="the intent tree",
                                     approved=config.approved_fields, metric_command=config.metric_command)
            for line in problems:
                print(line)
            return 1 if problems else 0
        overall = overall_ids(config.root / config.overall) if config.overall and (config.root / config.overall).is_dir() else None
        problems = check_records(config.structure, template.load_for(config), overall=overall, approved=config.approved_fields, metric_command=config.metric_command)
        for line in problems:
            print(line)
        return 1 if problems else 0
    if args.cmd == "run":
        from . import harness
        return harness.run_cli(args.rest, config)
    if args.cmd == "leaderboard":
        from . import harness, leaderboard, registry
        return leaderboard.board(config, registry.load(config), args.strict, stale=harness.stale_reason)
    if args.cmd == "select":
        return select_command(config, args)
    if args.cmd == "cascade":
        from . import cascade
        return cascade.run_cli(config, args.solution, args.strict)
    if args.cmd == "evidence":
        from . import evidence
        return evidence.run_cli(config, args.action, args.candidate, args.dimension, args.weights, args.file)
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
        try:
            options = consumer.Options.from_config(config, args.library)
        except ValueError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
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
