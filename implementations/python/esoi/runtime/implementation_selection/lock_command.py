"""``esoi lock``: write, update, diff or report the lock file that pins each solution's selected implementation."""
from __future__ import annotations

import argparse
import json
import sys


def find_assembler(config, args: argparse.Namespace):
    """The consumer's assembler, from its package's ``assembler()`` or ``ASSEMBLER``."""
    from esoi.runtime.assemble_by_name.interface import package_assembler
    name = args.package or args.scope or config.package
    if not name:
        raise ValueError("name a package with --package (or --scope), or set `package` in the configuration")
    return package_assembler(name)


def print_step(step: dict, with_human: bool) -> None:
    """One numbered step of a blocked update's plan."""
    print(f"    {step['order']}. {step['action']}: {step.get('command') or step['detail']}" + (" (ask a person)" if with_human and step["human"] else ""))


def run_status(lock, assembler, cfg, args: argparse.Namespace, solutions: tuple) -> int:
    """``--status``: print the lock's state and its updates; the exit code says up to date, safe updates or blocked."""
    code, plan = lock.status(assembler, args.file, cfg, solutions, package=args.package or "", file=args.file)
    if args.json:
        print(json.dumps(plan, indent=1))
        return code
    print(f"lock {args.file}: {plan['state']}")
    for item in plan["updates"]:
        change = lock.Change(item["solution"], item["old_arm"], item["new_arm"], item["verdict"], item["p"], item["evidence"],
                             item["requirements_added"], item["requirements_removed"])
        print("\n".join(change.lines()))
        for step in (item["steps"] if item["blocked"] else []):
            print_step(step, True)
    if plan.get("apply_safe"):
        print(f"apply every safe update: {plan['apply_safe']}")
    return code


def run_diff(lock, assembler, cfg, args: argparse.Namespace, solutions: tuple) -> int:
    """``--diff``: show what an update would change."""
    changes = lock.diff(assembler, args.file, cfg, solutions)
    if args.json:
        print(json.dumps({"schema": lock.STATUS_SCHEMA, "changes": [c.to_dict() for c in changes]}, indent=1))
    elif not changes:
        print("the lock is up to date: the latest selections equal the locked ones")
    for change in changes:
        print("\n".join(change.lines()))
    return 0


def run_update(lock, assembler, cfg, args: argparse.Namespace, solutions: tuple) -> int:
    """``--update``: move the lock to the latest selections that are safe (or every one with ``--latest``)."""
    result = lock.update(assembler, args.file, cfg, solutions, True if args.safe else False if args.latest else None)
    for change in result.moved:
        print("moved " + "\n".join(change.lines()))
    for change in result.blocked:
        print("left locked " + "\n".join(change.lines()))
        for step in lock.steps_for(change, args.package or "", args.file):
            print_step(step, False)
    if not result.moved and not result.blocked:
        print("the lock is up to date")
    return 0


def run_write(lock, assembler, cfg, args: argparse.Namespace, solutions: tuple) -> int:
    """No flag: write the lock from the current selections."""
    data = lock.write(assembler, args.file, cfg, solutions, args.policy)
    print(f"wrote {args.file}: {len(data['solutions'])} solutions")
    for sid, entry in data["solutions"].items():
        p = f", p={entry['p']:.3g}" if entry.get("p") is not None else ""
        print(f"  {sid}: {entry['arm']} ({entry.get('verdict') or 'no verdict'}{p})")
    return 0


def run_lock(config, args: argparse.Namespace) -> int:
    """``esoi lock``: write the lock, or with --update / --diff / --status move it, show what would change, or give an agent the plan.
    Exit codes: 0 done (--status: up to date), 2 error, and for --status only 3 (safe updates available) and 4 (blocked by requirements)."""
    import os
    from esoi.runtime.implementation_selection import lock
    from esoi.runtime.assemble_by_name.interface import AssemblyConfig
    try:
        assembler = find_assembler(config, args)
        cfg = AssemblyConfig(consumer_environ=dict(os.environ))
        solutions = tuple(args.solution or ())
        action = run_status if args.status else run_diff if args.diff else run_update if args.update else run_write
        return action(lock, assembler, cfg, args, solutions)
    except (ValueError, ImportError, AttributeError, RuntimeError, OSError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return 2
