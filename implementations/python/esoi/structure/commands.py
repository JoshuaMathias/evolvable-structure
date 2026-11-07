"""The sub-commands of the structure container: rules, records, template, intent layout, admission, new solutions, versions and hygiene."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from esoi import command_table


def run_check(config, args: argparse.Namespace) -> int:
    from esoi.structure.structure_check.interface import check
    from esoi.structure.intent_registry import intents
    with intents.session():
        return check.run_cli(config, args.strict, args.write_docs, findings=args.findings)


def run_rules(config, args: argparse.Namespace) -> int:
    from esoi.structure.structure_check import rules
    for rid, text in rules.summaries(config).items():
        print(f"- **{rid}** {text}" if args.markdown else f"{rid:<5}{text}")
    return 0


def run_structure_quality(config, args: argparse.Namespace) -> int:
    """Print the Structure Quality report of a path, or with ``--compare`` the comparison of two structures (advisory: the exit code is always 0)."""
    from esoi.structure.structure_check.interface import structure_quality_rules
    from esoi.structure.structure_quality.interface import compare, report
    if args.compare:
        try:
            result = structure_quality_rules.compare_refs(args.compare[0], args.compare[1], args.path, args.stage, not args.fast)
        except ValueError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
        for line in compare.lines(result):
            print(line)
        return 0
    for line in report.lines(structure_quality_rules.assess_path(Path(args.path), args.stage, not args.fast)):
        print(line)
    return 0


def run_template(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry.template_sync.interface import templates
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
    from esoi.structure.intent_registry.interface import migrate
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
        from esoi.structure.intent_registry import registry
        from esoi.structure.intent_registry.interface import besidecode
        from esoi.understanding.readable_records.interface import readme
        return besidecode.run_cli(config, "beside" if args.action == "place" else "gather", args.apply,
                                  after_apply=lambda moved: readme.write(moved, registry.load(moved), say=lambda text: None))
    if args.action == "sync":
        return records_sync(config, args)
    return records_check(config, args)


def run_admit(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry import registry
    from esoi.structure.intent_registry.interface import admit
    return admit.run_cli(config, registry.load(config), args.solution, args.name, args.why, args.uses, args.filepath, args.changed,
                         say=lambda text: print(text, file=sys.stderr if text.startswith("esoi:") else sys.stdout))


def run_new(config, args: argparse.Namespace) -> int:
    from esoi.structure.intent_registry.specify_from_code.interface import newsolution
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
    from esoi.structure.intent_registry.template_sync.interface import versioning
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
    from esoi.structure.structure_check.interface import hygiene
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


TABLE = """
check | | run every rule
    --strict | action=store_true | also reject results recorded on uncommitted code
    --findings | action=store_true | list every finding of the opt-in rules S36 to S39 with a count per rule (exit 0; they never fail the check)
    --write-docs | action=store_true | regenerate the generated files first
rules | | list the rules
    --markdown | action=store_true |
structure-quality | needs_config=False | score how well a project's code and records divide the work (advisory, never fails)
    path | nargs=? default=. | the project (with --compare: the repository that git references are read from)
    --stage | type=int choices=1,2 default=1 | 1: static code and records; 2: also co-change mined from git history
    --compare | nargs=2 metavar=BEFORE,AFTER | compare two structures, each a folder or a git reference (a restructuring is kept only when the number holds or rises)
    --fast | action=store_true | leave the flow dimension unmeasured (it reads the records and costs most of the time on a large project)
template | | the intent template
    action | choices=sync,check |
    --source | default=None | the SKILL.md-style file holding the template
records | | check only the intent records, or sync the rows the code declares
    action | nargs=? default=check choices=check,sync,place,gather |
    --apply | action=store_true | place, gather: move the records (a dry run without it)
    --intent | default=None | sync: the intent whose folder receives new rows (default: the top intent)
    --dry-run | action=store_true | sync: list the rows without writing them
admit | | take a newly found technology into the structure, or record a justified change to it
    solution | |
    name | nargs=? default= | the technology (an implementation of the solution)
    --why | required=True | why it is worth measuring, or why the specification changes
    --uses | action=append default=[] metavar=SOLUTION | a solution a composite arm is built over (repeatable)
    --filepath | default= | the file that holds the arm, when it exists
    --changed | default= | record a change to the specification (interface, merge, split, hierarchy) in the solution's knowledge
new | | create something new from one command
    what | choices=solution |
    id | |
    --intent | default=None | the intent whose folder receives the records (default: the top intent)
intent | | the intent layout
    action | choices=migrate |
    --apply | action=store_true | migrate: write the files (without it, only report the plan)
fields | | the 2026-10-26 field change
    action | choices=migrate |
    --apply | action=store_true | migrate: write the files (without it, only report the plan)
version | needs_config=False | the package, skill and template versions
    --record | action=store_true | record the library's template version under [records] in esoi.toml
hygiene | needs_config=False | scan for secrets and private data
    --root | default=. |
    --staged | action=store_true |
    --history | action=store_true | also scan every line ever added in git history
"""


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    command_table.register(sub, TABLE, globals())
