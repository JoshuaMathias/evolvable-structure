"""``esoi lock``: write, update, diff or report the lock file that pins each solution's selected implementation."""
from __future__ import annotations

import argparse
import sys


def run_lock(config, args: argparse.Namespace) -> int:
    """``esoi lock``: write the lock, or with --update / --diff / --status move it, show what would change, or give an agent the plan.
    Exit codes: 0 done (--status: up to date), 2 error, and for --status only 3 (safe updates available) and 4 (blocked by requirements)."""
    import importlib
    import json
    import os
    from esoi.runtime.implementation_selection import lock
    from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
    try:
        name = args.package or args.scope or config.package
        if not name:
            raise ValueError("name a package with --package (or --scope), or set `package` in the configuration")
        module = importlib.import_module(name)
        found = getattr(module, "assembler", None) or getattr(module, "ASSEMBLER", None)
        assembler = found() if callable(found) else found
        if assembler is None:
            raise ValueError(f"{name} has no assembler() or ASSEMBLER")
        cfg = AssemblyConfig(consumer_environ=dict(os.environ))
        solutions = tuple(args.solution or ())
        package = args.package or ""
        if args.status:
            code, plan = lock.status(assembler, args.file, cfg, solutions, package=package, file=args.file)
            if args.json:
                print(json.dumps(plan, indent=1))
            else:
                print(f"lock {args.file}: {plan['state']}")
                for item in plan["updates"]:
                    change = lock.Change(item["solution"], item["old_arm"], item["new_arm"], item["verdict"], item["p"], item["evidence"],
                                         item["requirements_added"], item["requirements_removed"])
                    print("\n".join(change.lines()))
                    if item["blocked"]:
                        for step in item["steps"]:
                            print(f"    {step['order']}. {step['action']}: {step.get('command') or step['detail']}" + (" (ask a person)" if step["human"] else ""))
                if plan.get("apply_safe"):
                    print(f"apply every safe update: {plan['apply_safe']}")
            return code
        if args.diff:
            changes = lock.diff(assembler, args.file, cfg, solutions)
            if args.json:
                print(json.dumps({"schema": lock.STATUS_SCHEMA, "changes": [c.to_dict() for c in changes]}, indent=1))
            elif not changes:
                print("the lock is up to date: the latest selections equal the locked ones")
            for change in changes:
                print("\n".join(change.lines()))
            return 0
        if args.update:
            safe = True if args.safe else False if args.latest else None
            result = lock.update(assembler, args.file, cfg, solutions, safe)
            for change in result.moved:
                print("moved " + "\n".join(change.lines()))
            for change in result.blocked:
                print("left locked " + "\n".join(change.lines()))
                for step in lock.steps_for(change, package, args.file):
                    print(f"    {step['order']}. {step['action']}: {step.get('command') or step['detail']}")
            if not result.moved and not result.blocked:
                print("the lock is up to date")
            return 0
        data = lock.write(assembler, args.file, cfg, solutions, args.policy)
        print(f"wrote {args.file}: {len(data['solutions'])} solutions")
        for sid, entry in data["solutions"].items():
            p = f", p={entry['p']:.3g}" if entry.get("p") is not None else ""
            print(f"  {sid}: {entry['arm']} ({entry.get('verdict') or 'no verdict'}{p})")
        return 0
    except (ValueError, ImportError, AttributeError, RuntimeError, OSError) as exc:
        print(f"esoi: {exc}", file=sys.stderr)
        return 2
