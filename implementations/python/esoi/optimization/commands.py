"""The sub-commands of the optimization container: run, stale, attest, leaderboard, cascade, evidence, cassette and select (which promotes winners)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from esoi import command_table


def run_run(config, args: argparse.Namespace) -> int:
    from esoi.optimization.measurement_harness import interface as harness
    return harness.run_cli(args.rest, config)


def run_cassette(config, args: argparse.Namespace) -> int:
    from esoi.optimization.measurement_harness.interface import cassette
    return cassette.run_cli(args.rest, str(config.harness.get("cassette", "")), config.root)


def run_attest(config, args: argparse.Namespace) -> int:
    from esoi.optimization.when_metrics_are_run.interface import attest
    return attest.run_cli(config, args.component, args.impl, args.reason, args.through, args.author)


def run_stale(config, args: argparse.Namespace) -> int:
    from esoi.optimization.when_metrics_are_run.interface import ownership_index, staleness
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
    from esoi.optimization.when_metrics_are_run.interface import attest
    from esoi.optimization.measurement_harness import interface as harness
    from esoi.optimization.leaderboard.interface import board_report
    from esoi.structure.intent_registry import registry
    from esoi.structure.intent_registry import intents
    with intents.session():
        return board_report.board(config, registry.load(config), args.strict, stale=harness.stale_reason, attested=attest.note)


def run_cascade(config, args: argparse.Namespace) -> int:
    from esoi.optimization.leaderboard.interface import cascade_report
    return cascade_report.run_cli(config, args.solution, args.strict)


def run_evidence(config, args: argparse.Namespace) -> int:
    from esoi.optimization.when_metrics_are_run.interface import evidence_report
    return evidence_report.run_cli(config, args.action, args.candidate, args.dimension, args.weights, args.file)


def run_evidence_table(config, args: argparse.Namespace) -> int:
    from esoi.optimization.leaderboard.interface import evidence_table
    return evidence_table.run_cli(config, args.file, args.begin or evidence_table.BEGIN, args.end or evidence_table.END, args.solution)


def run_select(config, args: argparse.Namespace) -> int:
    """``esoi select``: explain the cascade for a solution, promote a winner, or write a snapshot."""
    import json
    from esoi.runtime.assemble_by_name.interface import intent_map
    from esoi.runtime.implementation_selection import selection_cascade
    from esoi.runtime.implementation_selection import selection_registry
    from esoi.runtime.implementation_selection.select import Selector
    if args.promote:
        from esoi.optimization.promote_the_winner.interface import promote
        return promote.run_cli(config, args.solution or "", args.dry_run, args.apply)
    if args.snapshot:
        Path(args.snapshot).write_text(json.dumps(intent_map.snapshot(config), indent=1, sort_keys=True) + "\n", encoding="utf-8")
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


TABLE = """
run | add_help=False | run one implementation over a component's cases
    rest | nargs=REMAINDER |
stale | | which changed files a recorded result measures (what makes a row stale, and who owns each changed file)
    --explain | metavar=COMPONENT default= | the changed files that count for each arm of the component, and the ones that are ignored
    --rule | default= | judge by this staleness rule instead of the configured one (repo_wide, component_paths, import_closure)
    --count | action=store_true | count the rows each rule calls stale now (measured code changed)
attest | | record that an arm's own code changed but not what its result measures (the result counts as current for that commit range)
    component | |
    impl | |
    --reason | default= | required: what changed and why the result still measures the same thing
    --through | default= | the last commit the attestation covers (default HEAD)
    --author | default= | who attests (default: git user.name and user.email)
leaderboard | | rank implementations
    --strict | action=store_true | exit 1 when a rival beats a selected implementation
cascade | | the stages of a costly metric, what each implementation reached, and what to run next
    solution | nargs=? default= |
    --strict | action=store_true | exit 1 when the cascade chooses another implementation than `selected`
evidence | | public evidence: list, grade or rank what others measured, never counted as a result
    action | nargs=? default=list choices=list,grade,rank,table |
    --candidate | default= | only this candidate
    --dimension | default= | only this dimension
    --weights | default= | rank: dimension=weight pairs, such as quality=2,cost=1 (default: every dimension present, equal)
    --file | default= | read this evidence CSV instead of the configured one
evidence-table | | a Markdown table of every evaluated solution's arms with Wilson intervals and verdicts
    --file | default= | write the table between the marker lines of this file instead of printing it
    --begin | default=None | the line that opens the block (default: <!-- esoi:evidence-table:begin -->)
    --end | default=None | the line that closes the block (default: <!-- esoi:evidence-table:end -->)
    --solution | default= | only this solution
cassette | | the cassette of recorded model calls: stats
    rest | nargs=REMAINDER |
select | | show which implementation runs, or promote a winner
    solution | nargs=? default=None |
    --name | default=None | per-call choice to explain (the `using=` layer)
    --promote | action=store_true | switch `selected` to the rival that wins on the solution's metric
    --apply | action=store_true | promote: apply the proposals of solutions whose `promotion` is not automatic (a person ran this)
    --dry-run | action=store_true | promote: print what would change without writing it
    --snapshot | default=None metavar=FILE | write the defaults and modules as JSON for a package without the records
"""


def register(sub) -> None:
    """Add this container's sub-commands to the ``esoi`` parser."""
    command_table.register(sub, TABLE, globals())
