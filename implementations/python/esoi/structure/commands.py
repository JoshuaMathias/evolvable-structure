"""The sub-commands of the structure container: rules, records, template, intent layout, admission, new solutions, versions and hygiene."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run_check(config, args: argparse.Namespace) -> int:
    from esoi.structure.structure_check import check
    from esoi.structure.intent_registry import intents
    with intents.session():
        return check.run_cli(config, args.strict, args.write_docs, findings=args.findings)


def run_rules(config, args: argparse.Namespace) -> int:
    from esoi.structure.structure_check import rules
    for rid, text in rules.summaries(config).items():
        print(f"- **{rid}** {text}" if args.markdown else f"{rid:<5}{text}")
    return 0


def run_structure_quality(config, args: argparse.Namespace) -> int:
    """Print the Structure Quality report of a path (advisory: the exit code is always 0)."""
    from esoi.structure.structure_check.rules import structure_quality_rules
    from esoi.structure.structure_quality import report
    for line in report.lines(structure_quality_rules.assess_path(Path(args.path), args.stage)):
        print(line)
    return 0


def run_template(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry.template_sync import templates
    return templates.sync(config, args.source, check=args.action == "check")


def run_fields(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import fields, intents
    done = fields.migrate_tree([folder for _, folder in intents.folders(config)], args.apply)
    for line in done:
        print(line)
    print(f"esoi fields migrate: {len(done)} file(s) " + ("migrated" if args.apply else "would change (dry run; pass --apply)") if done
          else "esoi fields migrate: records already use the current fields")
    return 0


def run_intent(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import migrate
    return migrate.run_cli(config, args.apply)


def records_sync(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry.specify_from_code import declarations
    from esoi.structure.intent_registry import registry
    try:
        done = declarations.sync(config, registry.load(config), declarations.scan(config), args.intent, not args.dry_run)
    except ValueError as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return 2
    for line in done:
        print(line)
    print("esoi records sync: " + (f"{len(done)} change(s)" + (" (dry run)" if args.dry_run else ", now fill the text only a person can write; `esoi check` names it") if done else "records already match the declarations"))
    return 0


def records_check(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import registry
    from esoi.structure.intent_registry.template_sync import template
    from esoi.structure.intent_registry.records import check_records, check_headers, overall_ids, tables_of
    if config.intent_mode:
        from esoi.structure.intent_registry import intents
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


def run_records(config, args: argparse.Namespace) -> int:
    if args.action in ("place", "gather"):
        from esoi.structure.intent_registry import besidecode
        return besidecode.run_cli(config, "beside" if args.action == "place" else "gather", args.apply)
    if args.action == "sync":
        return records_sync(config, args)
    return records_check(config, args)


def run_admit(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import admit, registry
    return admit.run_cli(config, registry.load(config), args.solution, args.name, args.why, args.uses, args.filepath, args.changed,
                         say=lambda text: print(text, file=sys.stderr if text.startswith("esoi:") else sys.stdout))


def run_new(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry.specify_from_code import newsolution
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


def run_version(config, args: argparse.Namespace) -> int:
    """``esoi version``: works without a configuration; ``--record`` needs one."""
    from esoi.structure.intent_registry import config as config_module
    from esoi.structure.intent_registry.template_sync import versioning
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


def run_hygiene(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import config as config_module
    from esoi.structure.structure_check import hygiene
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


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    p = sub.add_parser("check", help="run every rule")
    p.add_argument("--strict", action="store_true", help="also reject results recorded on uncommitted code")
    p.add_argument("--findings", action="store_true", help="list every finding of the opt-in rules S36 to S39 with a count per rule (exit 0; they never fail the check)")
    p.add_argument("--write-docs", action="store_true", help="regenerate the generated files first")
    p.set_defaults(handler=run_check)
    p = sub.add_parser("rules", help="list the rules")
    p.add_argument("--markdown", action="store_true")
    p.set_defaults(handler=run_rules)
    p = sub.add_parser("structure-quality", help="score how well a project's code and records divide the work (advisory, never fails)")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--stage", type=int, choices=[1, 2], default=1, help="1: static code and records; 2: also co-change mined from git history")
    p.set_defaults(handler=run_structure_quality, needs_config=False)
    p = sub.add_parser("template", help="the intent template")
    p.add_argument("action", choices=["sync", "check"])
    p.add_argument("--source", default=None, help="the SKILL.md-style file holding the template")
    p.set_defaults(handler=run_template)
    p = sub.add_parser("records", help="check only the intent records, or sync the rows the code declares")
    p.add_argument("action", nargs="?", default="check", choices=["check", "sync", "place", "gather"])
    p.add_argument("--apply", action="store_true", help="place, gather: move the records (a dry run without it)")
    p.add_argument("--intent", default=None, help="sync: the intent whose folder receives new rows (default: the top intent)")
    p.add_argument("--dry-run", action="store_true", help="sync: list the rows without writing them")
    p.set_defaults(handler=run_records)
    p = sub.add_parser("admit", help="take a newly found technology into the structure, or record a justified change to it")
    p.add_argument("solution")
    p.add_argument("name", nargs="?", default="", help="the technology (an implementation of the solution)")
    p.add_argument("--why", required=True, help="why it is worth measuring, or why the specification changes")
    p.add_argument("--uses", action="append", default=[], metavar="SOLUTION", help="a solution a composite arm is built over (repeatable)")
    p.add_argument("--filepath", default="", help="the file that holds the arm, when it exists")
    p.add_argument("--changed", default="", help="record a change to the specification (interface, merge, split, hierarchy) in the solution's knowledge")
    p.set_defaults(handler=run_admit)
    p = sub.add_parser("new", help="create something new from one command")
    p.add_argument("what", choices=["solution"])
    p.add_argument("id")
    p.add_argument("--intent", default=None, help="the intent whose folder receives the records (default: the top intent)")
    p.set_defaults(handler=run_new)
    p = sub.add_parser("intent", help="the intent layout")
    p.add_argument("action", choices=["migrate"])
    p.add_argument("--apply", action="store_true", help="migrate: write the files (without it, only report the plan)")
    p.set_defaults(handler=run_intent)
    p = sub.add_parser("fields", help="the 2026-10-26 field change")
    p.add_argument("action", choices=["migrate"])
    p.add_argument("--apply", action="store_true", help="migrate: write the files (without it, only report the plan)")
    p.set_defaults(handler=run_fields)
    p = sub.add_parser("version", help="the package, skill and template versions")
    p.add_argument("--record", action="store_true", help="record the library's template version under [records] in esoi.toml")
    p.set_defaults(handler=run_version, needs_config=False)
    p = sub.add_parser("hygiene", help="scan for secrets and private data")
    p.add_argument("--root", default=".")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--history", action="store_true", help="also scan every line ever added in git history")
    p.set_defaults(handler=run_hygiene, needs_config=False)
