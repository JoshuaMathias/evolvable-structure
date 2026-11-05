"""ALTERNATIVE: the size dimension alone as the number, the single-factor scorer a balanced number must beat. Shrinking files wins it, which is why it is the
bound for the Goodhart cases. Zero model calls."""
import structure_fixture
from esoi.structure.structure_quality import assess
from esoi.structure.structure_quality.balance import Budgets


def build(meter):
    def run(kind, args):
        report = assess.assess(str(structure_fixture.project(args["shape"])), args["stage"], Budgets(consumers=tuple(args.get("consumers", ()))))
        size = report["dimensions"]["size"]
        verdict = "unmeasured" if size["score"] is None else ("sound" if size["score"] >= 0.8 else "unsound")
        return {"score": size["score"], "verdict": verdict, "flagged": ["size"] if size["offenders"] else []}
    return run
