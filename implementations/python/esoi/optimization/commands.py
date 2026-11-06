"""The sub-commands of the optimization container: run, stale, attest, leaderboard, cascade, evidence, cassette and select (which promotes winners)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run_run(config, args: argparse.Namespace) -> int:
    from esoi.optimization.measurement_harness import interface as harness
    return harness.run_cli(args.rest, config)


def run_cassette(config, args: argparse.Namespace) -> int:
    from esoi.optimization.measurement_harness import cassette
    return cassette.run_cli(args.rest, str(config.harness.get("cassette", "")), config.root)


def run_attest(config, args: argparse.Namespace) -> int:
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import attest
    return attest.run_cli(config, args.component, args.impl, args.reason, args.through, args.author)


def run_stale(config, args: argparse.Namespace) -> int:
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import ownership_index, staleness
    if args.rule and args.rule not in ownership_index.RULES:
        print(f"esoi stale: --rule must be one of {', '.join(ownership_index.RULES)}")
        return 2
    if args.count:
        from esoi.structure.intent_registry import intents
        with intents.session():
            counts = {rule: staleness.count_stale(config, rule) for rule in ownership_index.RULES}
        for rule, found in counts.items():
            print(f"{rule}: {len(found)} row(s) stale because measured code changed")
        return 0
    if args.explain:
        from esoi.structure.intent_registry import intents
        with intents.session():
            return staleness.explain_cli(config, args.explain, print, args.rule)
    print("usage: esoi stale --explain COMPONENT [--rule RULE] | esoi stale --count")
    return 2


def run_leaderboard(config, args: argparse.Namespace) -> int:
    from esoi.optimization.when_metrics_are_run.know_what_a_result_measures import attest
    from esoi.optimization.measurement_harness import interface as harness
    from esoi.optimization.leaderboard import board_report
    from esoi.structure.intent_registry import registry
    from esoi.structure.intent_registry import intents
    with intents.session():
        return board_report.board(config, registry.load(config), args.strict, stale=harness.stale_reason, attested=attest.note)


def run_cascade(config, args: argparse.Namespace) -> int:
    from esoi.optimization.leaderboard import cascade_report
    return cascade_report.run_cli(config, args.solution, args.strict)


def run_evidence(config, args: argparse.Namespace) -> int:
    from esoi.optimization.when_metrics_are_run.public_evidence import evidence_report
    return evidence_report.run_cli(config, args.action, args.candidate, args.dimension, args.weights, args.file)


def run_evidence_table(config, args: argparse.Namespace) -> int:
    from esoi.optimization.leaderboard import evidence_table
    return evidence_table.run_cli(config, args.file, args.begin or evidence_table.BEGIN, args.end or evidence_table.END, args.solution)


def run_select(config, args: argparse.Namespace) -> int:
    """``esoi select``: explain the cascade for a solution, promote a winner, or write a snapshot."""
    import json
    from esoi.runtime.assemble_by_name.intent_map import snapshot
    from esoi.runtime.implementation_selection import selection_cascade
    from esoi.runtime.implementation_selection import selection_registry
    from esoi.runtime.implementation_selection.select import Selector
    if args.promote:
        from esoi.optimization.promote_the_winner import promote
        return promote.run_cli(config, args.solution or "", args.dry_run, args.apply)
    if args.snapshot:
        Path(args.snapshot).write_text(json.dumps(snapshot(config), indent=1, sort_keys=True) + "\n", encoding="utf-8")
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
        environ = dict(os.environ, **{selection_registry.ROOT_ENV: str(config.root)})
        try:
            picked = selection_cascade.choose(args.solution, args.name, environ)
        except selection_registry.SelectionError:
            if config.selection_table:
                Selector.from_config(config).chosen_name(args.solution, args.name)   # says "no selection table entry ..."
            raise
        print(f"{args.solution}: {picked.name} (chosen by the {picked.layer} layer; choices: "
              f"{', '.join(selection_cascade.names(args.solution, environ))})")
        for layer, value, source in selection_cascade.explain(args.solution, args.name, environ):
            print(f"  {layer}: {value} ({source})")
        return 0
    except (ValueError, OSError, ImportError, AttributeError) as exc:   # unknown solution or name, table cannot load
        print(f"esoi: {exc}", file=sys.stderr)
        return 2


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    p = sub.add_parser("run", help="run one implementation over a component's cases", add_help=False)
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p.set_defaults(handler=run_run)
    p = sub.add_parser("stale", help="which changed files a recorded result measures (what makes a row stale, and who owns each changed file)")
    p.add_argument("--explain", metavar="COMPONENT", default="", help="the changed files that count for each arm of the component, and the ones that are ignored")
    p.add_argument("--rule", default="", help="judge by this staleness rule instead of the configured one (repo_wide, component_paths, import_closure)")
    p.add_argument("--count", action="store_true", help="count the rows each rule calls stale now (measured code changed)")
    p.set_defaults(handler=run_stale)
    p = sub.add_parser("attest", help="record that an arm's own code changed but not what its result measures (the result counts as current for that commit range)")
    p.add_argument("component")
    p.add_argument("impl")
    p.add_argument("--reason", default="", help="required: what changed and why the result still measures the same thing")
    p.add_argument("--through", default="", help="the last commit the attestation covers (default HEAD)")
    p.add_argument("--author", default="", help="who attests (default: git user.name and user.email)")
    p.set_defaults(handler=run_attest)
    p = sub.add_parser("leaderboard", help="rank implementations")
    p.add_argument("--strict", action="store_true", help="exit 1 when a rival beats a selected implementation")
    p.set_defaults(handler=run_leaderboard)
    p = sub.add_parser("cascade", help="the stages of a costly metric, what each implementation reached, and what to run next")
    p.add_argument("solution", nargs="?", default="")
    p.add_argument("--strict", action="store_true", help="exit 1 when the cascade chooses another implementation than `selected`")
    p.set_defaults(handler=run_cascade)
    p = sub.add_parser("evidence", help="public evidence: list, grade or rank what others measured, never counted as a result")
    p.add_argument("action", nargs="?", default="list", choices=["list", "grade", "rank", "table"])
    p.add_argument("--candidate", default="", help="only this candidate")
    p.add_argument("--dimension", default="", help="only this dimension")
    p.add_argument("--weights", default="", help="rank: dimension=weight pairs, such as quality=2,cost=1 (default: every dimension present, equal)")
    p.add_argument("--file", default="", help="read this evidence CSV instead of the configured one")
    p.set_defaults(handler=run_evidence)
    p = sub.add_parser("evidence-table", help="a Markdown table of every evaluated solution's arms with Wilson intervals and verdicts")
    p.add_argument("--file", default="", help="write the table between the marker lines of this file instead of printing it")
    p.add_argument("--begin", default=None, help="the line that opens the block (default: <!-- esoi:evidence-table:begin -->)")
    p.add_argument("--end", default=None, help="the line that closes the block (default: <!-- esoi:evidence-table:end -->)")
    p.add_argument("--solution", default="", help="only this solution")
    p.set_defaults(handler=run_evidence_table)
    p = sub.add_parser("cassette", help="the cassette of recorded model calls: stats")
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p.set_defaults(handler=run_cassette)
    p = sub.add_parser("select", help="show which implementation runs, or promote a winner")
    p.add_argument("solution", nargs="?", default=None)
    p.add_argument("--name", default=None, help="per-call choice to explain (the `using=` layer)")
    p.add_argument("--promote", action="store_true", help="switch `selected` to the rival that wins on the solution's metric")
    p.add_argument("--apply", action="store_true", help="promote: apply the proposals of solutions whose `promotion` is not automatic (a person ran this)")
    p.add_argument("--dry-run", action="store_true", help="promote: print what would change without writing it")
    p.add_argument("--snapshot", default=None, metavar="FILE", help="write the defaults and modules as JSON for a package without the records")
    p.set_defaults(handler=run_select)
