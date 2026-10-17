"""CURRENT: the live leaderboard. ``leaderboard.rank``, ``challengers``, ``verdict``, ``arm_kind``, ``unverified`` and
``board`` over synthetic results tables (and, for arm tags, a mini component in a temporary folder). Zero model calls."""
import contextlib
import io
import tempfile
from pathlib import Path

import harness_fixture
from esoi import leaderboard


def rank(args):
    rows = {r["impl"]: dict(date="d", **r) for r in args["rows"]}
    return {"ranked": [r["impl"] for r in leaderboard.rank(rows)],
            "beats": [r["impl"] for r in leaderboard.challengers(rows, args["selected"])],
            "unverified": [i for i, r in rows.items() if leaderboard.unverified(r)]}


def verdict(args):
    rows = {r["impl"]: dict(date="d", component="mini", **r) for r in args["rows"]}
    with harness_fixture.mini_component(markers=args.get("markers")) as (config, name):
        for row in rows.values():
            row["component"] = name
        label, detail = leaderboard.verdict(rows, args["selected"], config.evaluation)
        return {"verdict": label, "text": detail,
                "arms": {i: leaderboard.arm_kind(r, config.evaluation) for i, r in rows.items()}}


def board(args):
    with tempfile.TemporaryDirectory(prefix="esoi_board_") as tmp:
        config = harness_fixture.Config(root=Path(tmp), results="results.csv")
        harness_fixture.write_results(config.results_path, args["rows"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = leaderboard.board(config, harness_fixture.registry_selecting(args["selected"]), bool(args.get("strict")))
        text = out.getvalue()
    return {"exit": code, "text": text,
            "beats": [ln.split()[1] for ln in text.splitlines() if ln.strip().startswith("!")],
            "incomparable": [ln.split()[1] for ln in text.splitlines() if ln.strip().startswith("?")]}


KINDS = {"rank": rank, "verdict": verdict, "board": board}


def build(meter):
    def run(kind, args):
        return KINDS[kind](args)
    return run
