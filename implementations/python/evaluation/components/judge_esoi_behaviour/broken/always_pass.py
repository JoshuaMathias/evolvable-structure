"""BASELINE: a judge that passes every reply, as a first draft that only looks for a confident answer would. It agrees with
every good reply and none of the bad ones, so the cases must fail it. Zero model calls."""


def build(meter):
    return lambda case: {"verdict": "pass", "reason": "looks confident"}
