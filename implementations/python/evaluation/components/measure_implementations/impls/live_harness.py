"""CURRENT: the live harness. ``harness.record_result``, ``harness.load_cases`` and ``harness.run_component`` over a
mini component and synthetic tables in a temporary folder with its own git repository. Zero model calls."""
import contextlib
import csv
import hashlib
import importlib
import io

import harness_fixture
from esoi import harness


def record(args):
    kind = args.get("cases_file", "json")
    with harness_fixture.mini_component(kind) as (config, name):
        summary = dict(component=name, impl="good", cases=3, passed=3, dev="2/2", heldout="1/1", model_calls=0,
                       tokens_in=0, tokens_out=0, cli_reported_cost_usd=0.0, seconds=0.1)
        if args.get("dirty"):
            (config.root / "mini_pkg" / "live.py").write_text("X = 2\n")
        harness.record_result(summary, config, date="2026-10-16")
        rows = list(csv.DictReader(config.results_path.open()))
        first = rows[-1]
        cases_path = config.evaluation / name / ("cases.json" if kind == "json" else "cases.csv")
        matches = first["cases_sha"] == hashlib.sha256(cases_path.read_bytes()).hexdigest()[:8]
        changes = False
        if args.get("edit_cases"):
            cases_path.write_text(cases_path.read_text() + (" " if cases_path.suffix == ".json" else "M9,echo,\n"))
            harness.record_result(summary, config, date="2026-10-17")
            changes = list(csv.DictReader(config.results_path.open()))[-1]["cases_sha"] != first["cases_sha"]
        rows = list(csv.DictReader(config.results_path.open()))
    return {"git_sha": bool(first["git_sha"].replace("-dirty", "")), "dirty": first["git_sha"].endswith("-dirty"),
            "cases_sha_matches": matches, "cases_sha_changes": changes, "rows": len(rows)}


def run(args):
    with harness_fixture.mini_component() as (config, name):
        argv = ["--impl", args["impl"]] + list(args.get("argv", []))
        score = importlib.import_module(f"{name}.score")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                summary, _ = harness.run_component(name, score.score_case, argv, config)
        except Exception as exc:
            return {"cases": 0, "passed": 0, "error": type(exc).__name__}
    return {"cases": summary["cases"], "passed": summary["passed"], "error": None, "model_calls": summary["model_calls"]}


def validity(args):
    good, bad = run({"impl": "good"}), run({"impl": "bad"})
    return {"cases": good["cases"], "good_passed": good["passed"], "bad_passed": bad["passed"]}


KINDS = {"record": record, "run": run, "validity": validity}


def build(meter):
    def measure(kind, args):
        return KINDS[kind](args)
    return measure
