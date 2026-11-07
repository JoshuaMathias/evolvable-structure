"""CURRENT: the live leaderboard. ``leaderboard.rank``, ``challengers``, ``verdict``, ``arm_kind``, ``unverified`` and
``board`` over synthetic results tables (and, for arm tags, a mini component in a temporary folder). Zero model calls."""
import contextlib
import io
import tempfile
from pathlib import Path

from shared_fixtures.interface import harness_fixture
from esoi.optimization.leaderboard import arm_kinds, case_identity, ranking, rival_decisions, switching_policy
from esoi.optimization.leaderboard.interface import board_report, verdict_labels


def rank(args):
    rows = {r["impl"]: dict(date="d", **r) for r in args["rows"]}
    return {"ranked": [r["impl"] for r in ranking.rank(rows)],
            "beats": [r["impl"] for r in rival_decisions.challengers(rows, args["selected"], policy=switching_policy.Policy(require_significance=args.get("require_significance", False)))],
            "unverified": [i for i, r in rows.items() if case_identity.unverified(r)]}


def case_rows(name: str, rows: dict, outcomes: dict) -> list:
    """One per-case row for each recorded outcome of each implementation."""
    return [{"component": name, "impl": impl, "cases_sha": rows[impl].get("cases_sha", ""), "sample": rows[impl].get("sample", ""),
             "case_id": f"k{i}", "ok": "1" if ok else "0"} for impl, found in outcomes.items() for i, ok in enumerate(found)]


def verdict(args):
    listed = [{"date": "d", "component": "mini", **r} for r in args["rows"]]   # in the order recorded
    history = {}
    for r in sorted(listed, key=lambda r: r["date"]):
        history.setdefault(r["impl"], []).append(r)
    rows = {impl: arms[-1] for impl, arms in history.items()}
    with harness_fixture.mini_component(markers=args.get("markers")) as (config, name):
        for row in rows.values():
            row["component"] = name
        per_case = case_rows(name, rows, args.get("outcomes") or {})
        policy = switching_policy.Policy(alpha=args.get("alpha", switching_policy.ALPHA), require_significance=args.get("require_significance", False))
        label, detail = verdict_labels.verdict(rows, args["selected"], config.evaluation, history, per_case, policy)
        return {"verdict": label, "text": detail,
                "arms": {i: arm_kinds.arm_kind(r, config.evaluation) for i, r in rows.items()}}


def board(args):
    with tempfile.TemporaryDirectory(prefix="esoi_board_") as tmp:
        config = harness_fixture.Config(root=Path(tmp), results="results.csv")
        harness_fixture.write_results(config.results_path, args["rows"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = board_report.board(config, harness_fixture.registry_selecting(args["selected"]), bool(args.get("strict")))
        text = out.getvalue()
    return {"exit": code, "text": text,
            "beats": [ln.split()[1] for ln in text.splitlines() if ln.strip().startswith("!")],
            "incomparable": [ln.split()[1] for ln in text.splitlines() if ln.strip().startswith("?")]}


KINDS = {"rank": rank, "verdict": verdict, "board": board}


def build(meter):
    def run(kind, args):
        return KINDS[kind](args)
    return run
