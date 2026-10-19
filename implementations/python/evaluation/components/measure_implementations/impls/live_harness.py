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


def cost(args):
    """The ``cost_usd`` a recorded run carries: reported, priced from the table, zero for a run that called no model,
    or blank when the model has no price."""
    with harness_fixture.mini_component() as (config, name):
        config.prices = args.get("prices", {})
        summary = dict(component=name, impl="good", cases=3, passed=3, dev="3/3", heldout="0/0",
                       model_calls=args.get("model_calls", 0), tokens_in=args.get("tokens_in", 0),
                       tokens_out=args.get("tokens_out", 0), cli_reported_cost_usd=args.get("reported", 0.0), seconds=0.1,
                       model=args.get("model"))
        harness.record_result(summary, config, date="2026-10-16")
        return {"cost_usd": list(csv.DictReader(config.results_path.open()))[-1]["cost_usd"]}


def paid(args):
    """Whether an arm may spend money: it declares ``PAID = True``, is listed in ``paid_arms``, or its last run called a model."""
    with harness_fixture.mini_component() as (config, name):
        if args.get("declares"):
            impl = config.evaluation / name / "impls" / "good.py"
            impl.write_text("PAID = True\n" + impl.read_text())
        config.paid_arms = [f"{name}/good"] if args.get("listed") else []
        row = {"model_calls": args["row_calls"]} if "row_calls" in args else None
        reason = harness.paid_reason(config, name, "good", row)
    return {"paid": bool(reason)}


def external(args):
    """Staleness of a result whose measured code sits in another repository (a ``code_paths`` entry outside this one)."""
    import os
    import subprocess
    import tempfile
    from pathlib import Path

    def git(folder, *a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], cwd=folder, check=True,
                       capture_output=True)

    with harness_fixture.mini_component() as (config, name), tempfile.TemporaryDirectory(prefix="esoi_sibling_") as other:
        sibling = Path(other)
        (sibling / "lib").mkdir()
        (sibling / "lib" / "a.py").write_text("X = 1\n")
        git(sibling, "init", "-q")
        git(sibling, "add", "-A")
        git(sibling, "commit", "-q", "-m", "init")
        config.code_paths = ["mini_pkg", os.path.relpath(sibling / "lib", config.root)]
        summary = dict(component=name, impl="good", cases=3, passed=3, dev="2/2", heldout="1/1", model_calls=0,
                       tokens_in=0, tokens_out=0, cli_reported_cost_usd=0.0, seconds=0.1)
        row = harness.record_result(summary, config, date="2026-10-16")
        if args.get("change"):
            (sibling / "lib" / "a.py").write_text("X = 2\n")
        if args.get("commit"):
            git(sibling, "commit", "-q", "-am", "change")
        return {"recorded": "@" in row["code_shas"], "stale": bool(harness.stale_reason(config, name, row)),
                "stale_outside_strict": bool(harness.stale_reason(config, name, row, strict=False))}


def simulated(args):
    """An arm that meters a deterministic stand-in for a model (one call per case, no tokens, no price): what a real run
    records for it and whether the harness would treat it as paid. ``declares`` marks the module ``SIMULATED = True``;
    ``also_paid`` adds ``PAID = True``."""
    with harness_fixture.mini_component() as (config, name):
        impl = config.evaluation / name / "impls" / "spender.py"
        marks = ("SIMULATED = True\n" if args.get("declares") else "") + ("PAID = True\n" if args.get("also_paid") else "")
        impl.write_text(marks + impl.read_text())
        score = importlib.import_module(f"{name}.score")
        with contextlib.redirect_stdout(io.StringIO()):
            harness.run_component(name, score.score_case, ["--impl", "spender", "--record"], config)
        row = list(csv.DictReader(config.results_path.open()))[-1]
        return {"model": row["model"], "cost_usd": row["cost_usd"], "model_calls": int(row["model_calls"]),
                "paid": bool(harness.paid_reason(config, name, "spender", row))}


KINDS = {"record": record, "run": run, "validity": validity, "cost": cost, "paid": paid, "external": external, "simulated": simulated}


def build(meter):
    def measure(kind, args):
        return KINDS[kind](args)
    return measure
