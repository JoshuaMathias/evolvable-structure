"""The ``esoi`` command line. Each subcommand is a thin call into the module that owns the behaviour.

    esoi init [DIR] [--package NAME]       scaffold a passing example repository
    esoi check [--strict] [--findings] [--write-docs]   run every rule (esoi rules lists them)
    esoi rules [--markdown]                list the rules and what each one means
    esoi template sync|check               keep the parsed intent template in step with its source
    esoi skill sync|check|install          the public copy of the author's skill: generate, verify, install
    esoi records [check|sync]              check only the intent records, or write the rows the code declares and they lack
    esoi records place|gather [--apply]    move records beside the code they describe (or into the structure folder); a dry run without --apply
    esoi admit SOLUTION NAME --why TEXT    register a newly found technology as an implementation of a solution (a rival with no arm until its code is declared);
                                           with --changed WHAT instead of NAME: record a justified change to the specification
    esoi new solution ID [--intent ID]     a solution in one command: records, code with declarations, evaluation folder
    esoi run COMPONENT --impl NAME [--record]   run and record one implementation over a component's cases
    esoi stale --explain COMPONENT | --count   which changed files a recorded result measures, and how many rows each staleness rule calls stale
    esoi leaderboard [--strict]            rank the implementations of every evaluated solution
    esoi select SOLUTION [--name NAME]     show which implementation runs now, and which layer of the cascade chose it
    esoi cascade [SOLUTION] [--strict]     a metric's cascading conditionals: each stage's results, the chosen implementation, what to run next
    esoi evidence-table [--file F]         Markdown table of arms, Wilson intervals, paired verdicts; written between markers in F
    esoi evidence [list|grade|rank|table]  public evidence others measured, graded A to D; complementary, never a result row
    esoi select --promote [SOLUTION]       switch `selected` to the rival shown better on the solution's own metric
    esoi select --snapshot FILE            write the defaults and modules for a package shipped without the records
    esoi tracker build|check               build or verify the review tracker tabs
    esoi consumer check --registry CSV     check a consuming repository's integration registry
    esoi fields migrate [--apply]          split scoped_purpose into the new solution and metric fields in every records folder (dry run without --apply)
    esoi intent migrate [--apply]          move a legacy overall layout to the intent layout (dry run without --apply)
    esoi spec index [--out FILE]|find TEXT [-k N] [--expand N]|show ID [--tier 0|1|2]|related ID [--depth N]|intent [ID] [--cache FILE]   the specification index: find the few records a new use case needs
    esoi projects init|add|list|check|index|where   the local ESOI index (a folder named by ESOI_HOME, else ~/.esoi)
    esoi version [--record]                the package version, the skill it follows, the template version; --record writes the template version into esoi.toml
    esoi hygiene [--staged] [--history]    scan for secrets, machine paths and real addresses
    esoi requirements [--package P | --scope S] [--solution ID] [--check] [--json] [--env-template FILE] [--install-script FILE]   what the implementations need from their environment
    esoi install [--package P | --scope S] [--solution ID ...] [--assembly] [--yes]   install only what the solutions in use need (dry run without --yes)
    esoi lock [--package P | --scope S] [--file esoi.lock.json] [--update [--safe|--latest]] [--diff] [--status] [--solution ID ...] [--json]   pin the selected implementations; see and take newer ones on your schedule
    esoi attest COMPONENT IMPL --reason TEXT [--through SHA] [--author NAME]   record that an arm's own code changed but not what its result measures
    esoi docs check|wiki [--out DIR] [--repo-url URL] [--push WIKI_GIT_URL]   the four-category docs standard; generate the wiki from docs/
    esoi sheet-sync sync|push|pull|check   two-way sync of the tracker with a Google Sheet (esoi[sheets])

``--config PATH`` (before the subcommand) names the configuration file or folder; by default the nearest
``esoi.toml`` or ``[tool.esoi]`` table from the current folder upward is used.
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from esoi import __version__
from esoi.optimization import commands as optimization_commands
from esoi.runtime import commands as runtime_commands
from esoi.structure import commands as structure_commands
from esoi.understanding import commands as understanding_commands

CONTAINERS = (understanding_commands, structure_commands, optimization_commands, runtime_commands)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="esoi", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None, help="the config file, or the folder that holds it")
    parser.add_argument("--version", action="version", version=f"esoi {__version__}")
    parser.set_defaults(needs_config=True, package_version=__version__)   # the front door names the version; a command reads it from args
    sub = parser.add_subparsers(dest="cmd", required=True)
    for container in CONTAINERS:
        container.register(sub)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if "run" in argv:   # everything after `run` belongs to the harness, flags included
        position = argv.index("run")
        args = build_parser().parse_args(argv[:position + 1])
        args.rest = argv[position + 1:]
    else:
        args = build_parser().parse_args(argv)
    config = None
    needs = args.needs_config(args) if callable(args.needs_config) else args.needs_config
    if needs:
        from esoi.structure.intent_registry import config as config_module
        try:
            config = config_module.load(args.config)
        except config_module.ConfigError as exc:
            print(f"esoi: {exc}", file=sys.stderr)
            return 2
    return args.handler(config, args)


if __name__ == "__main__":
    sys.exit(main())
