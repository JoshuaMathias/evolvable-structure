"""The sub-commands of the runtime container: lock, requirements, install, consumer check and follow."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from esoi.runtime.implementation_selection.lock_command import run_lock


def run_follow(config, args: argparse.Namespace) -> int:
    from esoi.runtime.consumer_check import follow
    return follow.run_cli(config, args.parent, tuple(args.solution or ()), args.plan, args.run_free, args.json, args.lock)


def run_consumer(config, args: argparse.Namespace) -> int:
    from esoi.runtime.consumer_check import consumer
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


def closure_for(config, args: argparse.Namespace, environ):
    """``(assembler or None, members)`` for the CLI's ``--package`` / ``--scope`` / ``--solution`` choice. With ``--package`` the
    closure follows the assembly (selected arms, the arms filling their needs); with ``--scope`` it is every declared arm of the scope."""
    import importlib
    from esoi.runtime.assemble_by_name.environment_needs import closure
    from esoi.runtime.implementation_selection import selection_cascade
    from esoi.runtime.implementation_selection import selection_registry
    from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
    solutions = tuple(getattr(args, "solution", None) or ())
    if args.package:
        module = importlib.import_module(args.package)
        found = getattr(module, "assembler", None) or getattr(module, "ASSEMBLER", None)
        assembler = found() if callable(found) else found
        if assembler is None:
            raise ValueError(f"{args.package} has no assembler() or ASSEMBLER")
        arms = dict(item.split("=", 1) for item in (getattr(args, "arm", None) or ()) if "=" in item)
        cfg = AssemblyConfig(solutions=solutions, names=arms, consumer_environ=environ)
        return assembler, assembler.closure(cfg, None, solutions, getattr(args, "all_arms", False)), cfg
    if config.package:
        importlib.import_module(config.package)
    scope = args.scope or config.package
    members = [closure.Member(f"{sid}:{name}", target, "declared") for (where, sid), entry in sorted(selection_registry.REGISTRY.items())
               if where == scope and (not solutions or sid in solutions)
               for name, target in sorted(entry.implementations.items()) if not isinstance(target, str)]
    return None, members, None


def run_requirements(config, args: argparse.Namespace) -> int:
    """``esoi requirements``: report, check and generate files for what the implementations need from their environment.
    Exit codes: 0 all met, 1 something unmet (or, with --coherence, selected arms that conflict), 2 error."""
    import json
    import os
    from esoi.runtime.assemble_by_name.installation import assembly_plan, plan_report, resolvers
    from esoi.runtime.assemble_by_name.environment_needs import checking, closure, declarations, generated_files, report
    environ = dict(os.environ)
    try:
        assembler, members, cfg = closure_for(config, args, environ)
        notes: list = []
        entries = declarations.gather(closure.members_pairs(members, notes))
        if args.coherence:
            if assembler is None:
                print("esoi: --coherence needs --package (an assembly to check)", file=sys.stderr)
                return 2
            cleanup = None
            resolver = None
            if args.online and not args.offline:
                resolver, cleanup = resolvers.venv_resolver()
            try:
                chosen, plan_members = assembly_plan.assembly_plan(assembler, cfg, environ, tuple(args.solution or ()), args.all_arms, resolver)
            finally:
                if cleanup:
                    cleanup()
            if args.json:
                print(json.dumps(plan_report.plan_json(chosen, plan_members), indent=1))
            else:
                print("coherence: " + ("the selected implementations' requirements resolve together" if not chosen.adjusted else "CONFLICT in the selected implementations"))
                print(plan_report.plan_text(chosen, plan_members), end="")
            return report.EXIT_UNMET if chosen.adjusted else report.EXIT_MET
    except (ValueError, ImportError, AttributeError, RuntimeError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return report.EXIT_ERROR
    checks = checking.check(entries, environ, args.probe, args.offline) if args.check else None
    if args.json:
        print(json.dumps(report.as_json(entries, checks, notes), indent=1))
    else:
        print(report.report(entries, checks), end="")
        for note in notes:
            print(f"note: {note}")
    try:
        if args.env_template:
            print(generated_files.write_env_file(Path(args.env_template), entries), file=sys.stderr)
        if args.env_file:
            print(generated_files.write_env_file(Path(args.env_file), entries), file=sys.stderr)
        if args.install_script:
            Path(args.install_script).write_text(generated_files.install_script(entries, environ), encoding="utf-8")
            print(f"wrote {args.install_script}", file=sys.stderr)
    except (ValueError, OSError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return report.EXIT_ERROR
    return report.EXIT_UNMET if checks and any(one.failing for one in checks) else report.EXIT_MET


def run_install(config, args: argparse.Namespace) -> int:
    """``esoi install``: the closure of what the solutions use, the plan, and (only with --yes) the install.
    Exit codes: 0 done or nothing to do, 1 something to do (dry run), failed, or still missing, 2 error."""
    import json
    import os
    from esoi.runtime.assemble_by_name.installation import assembly_plan, execution, plan_report, resolution_ladder
    from esoi.runtime.assemble_by_name.environment_needs import closure, declarations, report
    environ = dict(os.environ)
    try:
        assembler, members, cfg = closure_for(config, args, environ)
        notes: list = []
        if assembler is not None:
            chosen, members = assembly_plan.assembly_plan(assembler, cfg, environ, tuple(args.solution or ()), args.all_arms, None, project=Path(args.project))
        else:
            entries = declarations.gather(closure.members_pairs(members, notes))
            chosen = resolution_ladder.make_plan(entries, environ, None, None, Path(args.project), notes)
    except (ValueError, ImportError, AttributeError, RuntimeError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return report.EXIT_ERROR
    if args.json:
        print(json.dumps(plan_report.plan_json(chosen, members), indent=1))
    else:
        print(plan_report.plan_text(chosen, members), end="")
    if not args.yes:
        if not chosen.empty or chosen.conflicts:
            print("dry run: nothing was changed; run again with --yes to apply this plan", file=sys.stderr)
        return report.EXIT_UNMET if (not chosen.empty or chosen.conflicts or chosen.binaries or chosen.missing) else report.EXIT_MET
    done = execution.execute(chosen, execution.package_roots(members), environ)
    for line in done.warnings:
        print(f"warning: {line}", file=sys.stderr)
    for line in done.reports:
        print(line)
    if chosen.substitutions:
        print("note: install used the substituted arms above; to run them, select them (AssemblyConfig names / esoi select)")
    return report.EXIT_UNMET if (done.code or chosen.binaries or chosen.missing) else report.EXIT_MET


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    p = sub.add_parser("lock", help="pin the selected implementations per solution, see what a newer release would change, update on your schedule")
    p.add_argument("--package", default=None, help="an importable package whose assembler() (or ASSEMBLER) gives the solutions to lock")
    p.add_argument("--scope", default=None, help="the scope (the package's top-level name) to lock; default: the configured package")
    p.add_argument("--file", default="esoi.lock.json", help="the lock file (default: esoi.lock.json)")
    p.add_argument("--solution", action="append", help="only this solution id (repeatable)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--update", action="store_true", help="move the lock to the latest selections, printing each change with its evidence")
    mode.add_argument("--diff", action="store_true", help="show what --update would change, with the requirement changes; changes nothing")
    mode.add_argument("--status", action="store_true", help="the plan for an agent: exit 0 up to date, 3 safe updates, 4 blocked by requirements, 2 error")
    p.add_argument("--safe", action="store_true", help="with --update, move only solutions whose new closure adds no unmet requirement")
    p.add_argument("--latest", action="store_true", help="with --update, move everything even when the lock file says update = safe")
    p.add_argument("--policy", choices=["latest", "safe"], default=None, help="when writing, record this update policy in the lock file")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=run_lock)
    p = sub.add_parser("requirements", help="what implementations need from their environment: report, check, .env template, install script, coherence")
    p.add_argument("--package", default=None, help="an importable package whose assembler() (or ASSEMBLER) gives the arms an assembly would use")
    p.add_argument("--scope", default=None, help="the registry scope whose declared arms to report (default: the configured package)")
    p.add_argument("--solution", action="append", help="only this solution id (repeatable)")
    p.add_argument("--all-arms", action="store_true", help="every named arm, not only the selected ones")
    p.add_argument("--arm", action="append", metavar="SOLUTION=NAME", help="use this arm for a solution instead of the package default (repeatable)")
    p.add_argument("--check", action="store_true", help="check against the process environment; exit 1 when a required one is unmet")
    p.add_argument("--coherence", action="store_true", help="check that the selected implementations' requirements resolve together; exit 1 with the proposed fix if not")
    p.add_argument("--online", action="store_true", help="with --coherence, ask pip for a dry run in a temporary virtualenv (network)")
    p.add_argument("--probe", action="store_true", help="with --check, call each requirement's declared cheap probe (network)")
    p.add_argument("--offline", action="store_true", help="never touch the network, whatever else is asked")
    p.add_argument("--json", action="store_true")
    p.add_argument("--env-template", default=None, metavar="FILE", help="write a .env template (secrets blank)")
    p.add_argument("--env-file", default=None, metavar="FILE", help="add the missing variables, commented out, to this env file (never overwrites; mode 600)")
    p.add_argument("--install-script", default=None, metavar="FILE", help="write an install script")
    p.set_defaults(handler=run_requirements)
    p = sub.add_parser("install", help="install only what the solutions in use need (dry run unless --yes)")
    p.add_argument("--package", default=None)
    p.add_argument("--scope", default=None)
    p.add_argument("--solution", action="append", help="a solution id to install for (repeatable); default: what a default assembly would use")
    p.add_argument("--assembly", action="store_true", help="what a default assembly would use (the default when no --solution is given)")
    p.add_argument("--all-arms", action="store_true", help="every named arm of the solutions, not only the selected ones")
    p.add_argument("--arm", action="append", metavar="SOLUTION=NAME", help="use this arm for a solution instead of the package default (repeatable)")
    p.add_argument("--project", default=".", help="the project folder; isolated environments go under <project>/.esoi/venvs")
    p.add_argument("--yes", action="store_true", help="actually run the plan (pip in the current environment, and the files inside the package)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=run_install)
    p = sub.add_parser("consumer", help="check a consuming repository")
    p.add_argument("action", choices=["check"])
    p.add_argument("--registry", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--library", default=None, help="the importable library (default: [consumer] library)")
    p.add_argument("--requirements", default=None)
    p.add_argument("--solutions", default=None)
    p.add_argument("--results", default=None)
    p.add_argument("--fail-on-lag", action="store_true")
    p.set_defaults(handler=run_consumer)
    p = sub.add_parser("follow", help="compare the parent repository's current selections with this one's lock and overrides, judged on this repository's own metric (advice only)")
    p.add_argument("--parent", default="", metavar="PACKAGE_OR_PATH", help="the parent's records folder or esoi_selection.json, or an importable package with an assembler() (default: [parent] in the configuration)")
    p.add_argument("--solution", action="append", help="only this solution id (repeatable)")
    p.add_argument("--plan", action="store_true", help="print only what would be run; run nothing")
    p.add_argument("--run-free", action="store_true", help="record the arms that are free (offline, no model); a paid arm is never run")
    p.add_argument("--lock", default="esoi.lock.json", help="this repository's lock file (default: esoi.lock.json)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=run_follow)
