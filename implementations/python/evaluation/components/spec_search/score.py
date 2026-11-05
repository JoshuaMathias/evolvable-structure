"""Score one spec-search case against its declarative ``expect`` (see ``esoi.optimization.measurement_harness.expect``)."""
from esoi.optimization.measurement_harness import expect


def score_case(fn, case):
    return expect.score_kind_case(fn, case)
