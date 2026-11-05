"""The command line of the one-line check: ``python -m esoi.runtime.assemble_by_name.entry_cli [root] [--readme [--installed]] [--gate]``."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from esoi.runtime.assemble_by_name.entry_check import check_entries
from esoi.runtime.assemble_by_name.entry_outcome import ANSWERING, OUTCOMES
from esoi.runtime.assemble_by_name.readme_example import readme_check, run_block


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="esoi.runtime.assemble_by_name.entry_cli", description="One line for any solution or intent: check that each runs.")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--readme", action="store_true", help="run the README's first example that calls <package>.run (rule S37)")
    ap.add_argument("--installed", action="store_true", help="with --readme: build the wheel, install it in a temporary venv, run it there")
    ap.add_argument("--readme-block", default="", help="run the doctest block in this file (used by the installed stage)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gate", action="store_true", help="exit 1 unless every id answers (ok, pending-key, pending-install or pending-network)")
    args = ap.parse_args(argv)
    if args.readme_block:
        found = run_block(Path(args.readme_block).read_text(encoding="utf-8"))
        print(json.dumps(found))
        return 1 if found["problems"] else 0
    root = Path(args.root).resolve()
    if args.readme:
        found = readme_check(root, installed=args.installed)
        if args.json:
            print(json.dumps(found))
        else:
            print("\n".join(found["problems"] + found["pending"]) or "README: ok")
        return 1 if (args.gate and found["problems"]) else 0
    rows = check_entries(root)
    if args.json:
        print(json.dumps(rows, default=str))
    else:
        for r in rows:
            print(f"{r['outcome']:16s} {r['level']:8s} {r['id']} ({r['kind'] or 'no kind'}): {r['detail']}")
        answering = sum(r["outcome"] in ANSWERING for r in rows)
        counts = ", ".join(f"{o} {sum(r['outcome'] == o for r in rows)}" for o in OUTCOMES if any(r["outcome"] == o for r in rows))
        print(f"summary: {answering} of {len(rows)} ids answer ({counts}); share {round(answering / (len(rows) or 1), 3)}")
    return 1 if args.gate and any(r["outcome"] not in ANSWERING for r in rows) else 0


if __name__ == "__main__":   # run through the imported module, so its classes are the ones the entries raise
    import sys
    from esoi.runtime.assemble_by_name import entry_cli
    sys.exit(entry_cli.main())
