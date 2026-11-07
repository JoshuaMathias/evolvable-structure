"""The sub-commands of the runtime container: lock, requirements, install, consumer check and follow."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from esoi import command_table

from esoi.runtime.implementation_selection.interface import run_lock


def run_follow(config, args: argparse.Namespace) -> int:
    from esoi.runtime.consumer_check.interface import follow
    return follow.run_cli(config, args.parent, tuple(args.solution or ()), args.plan, args.run_free, args.json, args.lock)


def print_consumer_report(report) -> None:
    """Print a consumer check report: problems, then notes, then the row counts."""
    for line in report.problems:
        print(line)
    for line in report.notes:
        print(f"note: {line}")
    if report.counts:
        print("rows by kind: " + ", ".join(f"{k}={v}" for k, v in sorted(report.counts.items())))


def run_consumer(config, args: argparse.Namespace) -> int:
    from esoi.runtime.consumer_check.interface import consumer
    try:
        options = consumer.Options.from_config(config, args.library)
    except ValueError as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return 2
    report = consumer.check_consumer(Path(args.registry), Path(args.root), options,
                                     Path(args.requirements) if args.requirements else None,
                                     Path(args.solutions) if args.solutions else None,
                                     Path(args.results) if args.results else None)
    print_consumer_report(report)
    return 1 if report.problems or (args.fail_on_lag and report.pin_lag) else 0


def assembly_closure(args: argparse.Namespace, environ):
    """``(assembler, members, config)`` for ``--package``: the closure follows the assembly (selected arms, the arms filling their needs)."""
    import importlib
    from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
    solutions = tuple(getattr(args, "solution", None) or ())
    module = importlib.import_module(args.package)
    found = getattr(module, "assembler", None) or getattr(module, "ASSEMBLER", None)
    assembler = found() if callable(found) else found
    if assembler is None:
        raise ValueError(f"{args.package} has no assembler() or ASSEMBLER")
    arms = dict(item.split("=", 1) for item in (getattr(args, "arm", None) or ()) if "=" in item)
    cfg = AssemblyConfig(solutions=solutions, names=arms, consumer_environ=environ)
    return assembler, assembler.closure(cfg, None, solutions, getattr(args, "all_arms", False)), cfg


def scope_closure(config, args: argparse.Namespace):
    """``(None, members, None)`` for ``--scope``: every declared arm of the scope."""
    import importlib
    from esoi.runtime.assemble_by_name.interface import closure
    from esoi.runtime.implementation_selection import selection_registry
    solutions = tuple(getattr(args, "solution", None) or ())
    if config.package:
        importlib.import_module(config.package)
    scope = args.scope or config.package
    members = [closure.Member(f"{sid}:{name}", target, "declared") for (where, sid), entry in sorted(selection_registry.REGISTRY.items())
               if where == scope and (not solutions or sid in solutions)
               for name, target in sorted(entry.implementations.items()) if not isinstance(target, str)]
    return None, members, None


def closure_for(config, args: argparse.Namespace, environ):
    """``(assembler or None, members, assembly config or None)`` for the CLI's ``--package`` / ``--scope`` / ``--solution`` choice.
    With ``--package`` the closure follows the assembly; with ``--scope`` it is every declared arm of the scope."""
    if args.package:
        return assembly_closure(args, environ)
    return scope_closure(config, args)


def print_coherence(args: argparse.Namespace, assembler, cfg, environ) -> int:
    """``esoi requirements --coherence``: print whether the selected arms' requirements resolve together."""
    import json
    from esoi.runtime.assemble_by_name.interface import assembly_plan, plan_report, report, resolvers
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


def print_requirements(args: argparse.Namespace, entries, checks, notes) -> None:
    """Print the requirements report as JSON or text, then its notes."""
    import json
    from esoi.runtime.assemble_by_name.interface import report
    if args.json:
        print(json.dumps(report.as_json(entries, checks, notes), indent=1))
        return
    print(report.report(entries, checks), end="")
    for note in notes:
        print(f"note: {note}")


def write_requirement_files(args: argparse.Namespace, entries, environ) -> None:
    """Write the files ``--env-template``, ``--env-file`` and ``--install-script`` ask for."""
    from esoi.runtime.assemble_by_name.interface import generated_files
    if args.env_template:
        print(generated_files.write_env_file(Path(args.env_template), entries), file=sys.stderr)
    if args.env_file:
        print(generated_files.write_env_file(Path(args.env_file), entries), file=sys.stderr)
    if args.install_script:
        Path(args.install_script).write_text(generated_files.install_script(entries, environ), encoding="utf-8")
        print(f"wrote {args.install_script}", file=sys.stderr)


def run_requirements(config, args: argparse.Namespace) -> int:
    """``esoi requirements``: report, check and generate files for what the implementations need from their environment.
    Exit codes: 0 all met, 1 something unmet (or, with --coherence, selected arms that conflict), 2 error."""
    import os
    from esoi.runtime.assemble_by_name.interface import checking, closure, declarations, report
    environ = dict(os.environ)
    try:
        assembler, members, cfg = closure_for(config, args, environ)
        notes: list = []
        entries = declarations.gather(closure.members_pairs(members, notes))
        if args.coherence:
            return print_coherence(args, assembler, cfg, environ)
    except (ValueError, ImportError, AttributeError, RuntimeError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return report.EXIT_ERROR
    checks = checking.check(entries, environ, args.probe, args.offline) if args.check else None
    print_requirements(args, entries, checks, notes)
    try:
        write_requirement_files(args, entries, environ)
    except (ValueError, OSError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return report.EXIT_ERROR
    return report.EXIT_UNMET if checks and any(one.failing for one in checks) else report.EXIT_MET


def install_plan(config, args: argparse.Namespace, environ):
    """``(plan, members)`` for ``esoi install``: the assembly's plan, or the resolution ladder over the declared closure."""
    from esoi.runtime.assemble_by_name.interface import assembly_plan, closure, declarations, resolution_ladder
    assembler, members, cfg = closure_for(config, args, environ)
    notes: list = []
    if assembler is not None:
        return assembly_plan.assembly_plan(assembler, cfg, environ, tuple(args.solution or ()), args.all_arms, None, project=Path(args.project))
    entries = declarations.gather(closure.members_pairs(members, notes))
    return resolution_ladder.make_plan(entries, environ, None, None, Path(args.project), notes), members


def print_install_plan(args: argparse.Namespace, chosen, members) -> None:
    """Print the install plan as JSON or text."""
    import json
    from esoi.runtime.assemble_by_name.interface import plan_report
    if args.json:
        print(json.dumps(plan_report.plan_json(chosen, members), indent=1))
    else:
        print(plan_report.plan_text(chosen, members), end="")


def dry_run_code(chosen) -> int:
    """The exit code of an install without ``--yes``: unmet when the plan has something to do or something is still missing."""
    from esoi.runtime.assemble_by_name.interface import report
    if not chosen.empty or chosen.conflicts:
        print("dry run: nothing was changed; run again with --yes to apply this plan", file=sys.stderr)
    return report.EXIT_UNMET if (not chosen.empty or chosen.conflicts or chosen.binaries or chosen.missing) else report.EXIT_MET


def apply_install(chosen, members, environ) -> int:
    """Run the plan (``--yes``), print what happened and return the exit code."""
    from esoi.runtime.assemble_by_name.interface import execution, report
    done = execution.execute(chosen, execution.package_roots(members), environ)
    for line in done.warnings:
        print(f"warning: {line}", file=sys.stderr)
    for line in done.reports:
        print(line)
    if chosen.substitutions:
        print("note: install used the substituted arms above; to run them, select them (AssemblyConfig names / esoi select)")
    return report.EXIT_UNMET if (done.code or chosen.binaries or chosen.missing) else report.EXIT_MET


def run_install(config, args: argparse.Namespace) -> int:
    """``esoi install``: the closure of what the solutions use, the plan, and (only with --yes) the install.
    Exit codes: 0 done or nothing to do, 1 something to do (dry run), failed, or still missing, 2 error."""
    import os
    from esoi.runtime.assemble_by_name.interface import report
    environ = dict(os.environ)
    try:
        chosen, members = install_plan(config, args, environ)
    except (ValueError, ImportError, AttributeError, RuntimeError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return report.EXIT_ERROR
    print_install_plan(args, chosen, members)
    return apply_install(chosen, members, environ) if args.yes else dry_run_code(chosen)


TABLE = """
lock | | pin the selected implementations per solution, see what a newer release would change, update on your schedule
    --package | default=None | an importable package whose assembler() (or ASSEMBLER) gives the solutions to lock
    --scope | default=None | the scope (the package's top-level name) to lock; default: the configured package
    --file | default=esoi.lock.json | the lock file (default: esoi.lock.json)
    --solution | action=append | only this solution id (repeatable)
    --update | action=store_true group=mode | move the lock to the latest selections, printing each change with its evidence
    --diff | action=store_true group=mode | show what --update would change, with the requirement changes; changes nothing
    --status | action=store_true group=mode | the plan for an agent: exit 0 up to date, 3 safe updates, 4 blocked by requirements, 2 error
    --safe | action=store_true | with --update, move only solutions whose new closure adds no unmet requirement
    --latest | action=store_true | with --update, move everything even when the lock file says update = safe
    --policy | choices=latest,safe default=None | when writing, record this update policy in the lock file
    --json | action=store_true |
requirements | | what implementations need from their environment: report, check, .env template, install script, coherence
    --package | default=None | an importable package whose assembler() (or ASSEMBLER) gives the arms an assembly would use
    --scope | default=None | the registry scope whose declared arms to report (default: the configured package)
    --solution | action=append | only this solution id (repeatable)
    --all-arms | action=store_true | every named arm, not only the selected ones
    --arm | action=append metavar=SOLUTION=NAME | use this arm for a solution instead of the package default (repeatable)
    --check | action=store_true | check against the process environment; exit 1 when a required one is unmet
    --coherence | action=store_true | check that the selected implementations' requirements resolve together; exit 1 with the proposed fix if not
    --online | action=store_true | with --coherence, ask pip for a dry run in a temporary virtualenv (network)
    --probe | action=store_true | with --check, call each requirement's declared cheap probe (network)
    --offline | action=store_true | never touch the network, whatever else is asked
    --json | action=store_true |
    --env-template | default=None metavar=FILE | write a .env template (secrets blank)
    --env-file | default=None metavar=FILE | add the missing variables, commented out, to this env file (never overwrites; mode 600)
    --install-script | default=None metavar=FILE | write an install script
install | | install only what the solutions in use need (dry run unless --yes)
    --package | default=None |
    --scope | default=None |
    --solution | action=append | a solution id to install for (repeatable); default: what a default assembly would use
    --assembly | action=store_true | what a default assembly would use (the default when no --solution is given)
    --all-arms | action=store_true | every named arm of the solutions, not only the selected ones
    --arm | action=append metavar=SOLUTION=NAME | use this arm for a solution instead of the package default (repeatable)
    --project | default=. | the project folder; isolated environments go under <project>/.esoi/venvs
    --yes | action=store_true | actually run the plan (pip in the current environment, and the files inside the package)
    --json | action=store_true |
consumer | | check a consuming repository
    action | choices=check |
    --registry | required=True |
    --root | default=. |
    --library | default=None | the importable library (default: [consumer] library)
    --requirements | default=None |
    --solutions | default=None |
    --results | default=None |
    --fail-on-lag | action=store_true |
follow | | compare the parent repository's current selections with this one's lock and overrides, judged on this repository's own metric (advice only)
    --parent | default= metavar=PACKAGE_OR_PATH | the parent's records folder or esoi_selection.json, or an importable package with an assembler() (default: [parent] in the configuration)
    --solution | action=append | only this solution id (repeatable)
    --plan | action=store_true | print only what would be run; run nothing
    --run-free | action=store_true | record the arms that are free (offline, no model); a paid arm is never run
    --lock | default=esoi.lock.json | this repository's lock file (default: esoi.lock.json)
    --json | action=store_true |
"""


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    command_table.register(sub, TABLE, globals())
