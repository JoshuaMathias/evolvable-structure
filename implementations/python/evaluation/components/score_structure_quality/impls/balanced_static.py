"""CURRENT: ``esoi.structure.structure_quality.assess``, the seven dimensions read from the code and records and weighted into one number. Zero model calls."""
from shared_fixtures.interface import structure_fixture
from esoi.structure.structure_quality.interface import assess
from esoi.structure.structure_quality.interface import Budgets


def build(meter):
    def run(kind, args):
        report = assess.assess(str(structure_fixture.project(args["shape"])), args["stage"], Budgets(consumers=tuple(args.get("consumers", ()))))
        return {"score": report["score"], "verdict": report["verdict"], "flagged": report["flagged"]}
    return run
