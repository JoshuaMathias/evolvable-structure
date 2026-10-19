"""CURRENT: the live promotion, ``esoi.promote.propose`` and ``esoi.promote.run_cli``, over synthetic results tables and
records in a temporary folder. Zero model calls."""
import tempfile
from pathlib import Path

import harness_fixture
from esoi import promote, registry as registry_module, tables
from esoi.config import Config

SOLUTION = "mini-solution"


def world(root, args):
    """Write the records and the results log of one case; returns (config, loaded registry)."""
    harness_fixture.write_results(root / "results.csv", args["rows"])
    selection = ""
    if args.get("table_default"):
        (root / "table.py").write_text('SELECTION = {"mini-solution": {"default": "a", "implementations": {"a": "collections:Counter", '
                                       '"b": "collections:OrderedDict"}}}\n')
        selection = "table.py:SELECTION"
    config = Config(root=root, results="results.csv", structure_dir="specs", evaluation_dir="evaluation/components",
                    selection=selection)
    selected = args["selected"]
    command = f"esoi run mini --impl {args.get('arm', selected.split('/')[-1].removesuffix('.py').split(':')[-1])}"
    (root / "specs").mkdir()
    tables.write_csv(root / "specs" / "solutions.csv", ["solution_id", "selected", "selected_by", "metric_ids", "metric_kind",
                                                       "implementations", "gap", "action", "promotion"],
                     [{"solution_id": SOLUTION, "selected": selected, "selected_by": "the only one so far", "metric_ids": "m",
                       "metric_kind": "eval", "implementations": "a;b", "promotion": args.get("promotion", "")}])
    tables.write_csv(root / "specs" / "metrics.csv", ["metric_id", "command"], [{"metric_id": "m", "command": command}])
    tables.write_csv(root / "specs" / "implementations.csv", ["implementation_id", "solution_id", "path"],
                     args.get("records", []))
    return config, registry_module.load(config)


def stale_for(args):
    stale = set(args.get("stale", []))
    return lambda config, component, row, strict: "uncommitted code" if row["impl"] in stale else ""


def decide(args):
    with tempfile.TemporaryDirectory(prefix="esoi_promote_") as tmp:
        config, loaded = world(Path(tmp), args)
        found = promote.propose(config, loaded, today="2026-10-18", stale=stale_for(args))
    if not found:
        return {"count": 0, "status": "none"}
    first = found[0]
    return {"count": len(found), "status": first.status, "winner": first.winner, "selected": first.selected,
            "command": first.command, "reason": first.reason, "text": first.reason}


def apply(args):
    with tempfile.TemporaryDirectory(prefix="esoi_promote_") as tmp:
        config, loaded = world(Path(tmp), args)
        for proposal in promote.propose(config, loaded, today="2026-10-18", stale=stale_for(args)):
            if proposal.status == "promote":
                promote.apply(config, loaded, proposal)
        solution = tables.read_csv(Path(tmp) / "specs" / "solutions.csv")[0]
        command = tables.read_csv(Path(tmp) / "specs" / "metrics.csv")[0]["command"]
    evidence = all(word in solution["selected_by"] for word in ("2026-10-18", "cases_sha x", "abc1234"))
    return {"applied": solution["selected"] != args["selected"], "selected": solution["selected"], "command": command,
            "evidence": evidence}


def build(meter):
    def run(kind, args):
        return {"decide": decide, "apply": apply}[kind](args)
    return run
