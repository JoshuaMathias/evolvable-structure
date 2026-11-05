"""BASELINE: the naive scorer. It reads nothing, calls every project at the reference with the top score and flags no dimension, so an incident goes
unnoticed and the balanced real structure cannot be told from the same project cut into tiny files. Zero model calls."""


def build(meter):
    def run(kind, args):
        return {"score": 1.0, "verdict": "at_reference", "flagged": []}
    return run
