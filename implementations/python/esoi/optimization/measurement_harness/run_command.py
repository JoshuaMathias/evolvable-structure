"""The `esoi run` command line: run one component's arm, or re-run what is stale."""
from __future__ import annotations

import importlib
from typing import Callable, List

from esoi.optimization.measurement_harness.component_folder import discover_components, prepare_path
from esoi.optimization.measurement_harness.rerun_stale import rerun_stale
from esoi.optimization.measurement_harness.run_component import run_component
from esoi.optimization.measurement_harness.run_errors import PendingNetwork, RunError
from esoi.structure.intent_registry.config import Config


def run_cli(argv: List[str], config: Config, say: Callable[[str], None] = print) -> int:
    """``esoi run <component> --impl <name> [flags]``, or ``esoi run --stale`` to re-run what is stale."""
    prepare_path(config)
    if argv and argv[0] == "--stale":
        include = [argv[i + 1] for i, word in enumerate(argv[:-1]) if word == "--include"]
        from esoi.structure.intent_registry import intents
        with intents.session():   # the record folders are found once for the whole listing
            return rerun_stale(config, say, record="--no-record" not in argv, include_paid="--include-paid" in argv,
                               include=include, full="--full" in argv, plan="--plan" in argv, run_all="--all" in argv,
                               for_decision="--for-decision" in argv)
    components = discover_components(config)
    if not argv or argv[0] not in components:
        say("usage: esoi run <component> --impl <name> [--only IDS | --failed] [--sample N] [--max-calls N] [--cassette DIR [--cassette-only]] [--keep-going] [--fresh] [--record] [--differs WHAT] [--force REASON]  |  esoi run --stale [--plan] [--full] [--for-decision | --all] [--include-paid | --include COMPONENT/IMPL]")
        say("components: " + (", ".join(components) or "none found under " + config.evaluation_dir))
        return 2
    score = importlib.import_module(f"{argv[0]}.score")
    try:
        run_component(argv[0], score.score_case, argv[1:], config, say)
    except PendingNetwork as exc:   # informs; it is not a failure
        say(f"esoi run: {exc}")
        return 0
    except RunError as exc:
        say(f"esoi run: {exc}")
        return 2
    return 0
