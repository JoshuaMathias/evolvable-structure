"""ALTERNATIVE: the size dimension alone as the number, the single-factor scorer a balanced number must beat. Shrinking files wins it, which is why it is the
bound for the Goodhart cases. Zero model calls."""
from shared_fixtures.interface import structure_fixture

from esoi.structure.structure_quality.interface import REFERENCE_LINE, Budgets, assess


def build(meter):
    def run(kind, args):
        report = assess(str(structure_fixture.project(args["shape"])), args["stage"], Budgets(consumers=tuple(args.get("consumers", ()))))
        size = report["dimensions"]["size"]
        verdict = "unmeasured" if size["score"] is None else ("at_reference" if size["score"] >= REFERENCE_LINE else "below_reference")
        return {"score": size["score"], "verdict": verdict, "flagged": ["size"] if size["offenders"] else []}
    return run
