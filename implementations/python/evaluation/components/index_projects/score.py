"""Score one lookup case against its declarative ``expect`` (see ``esoi.optimization.measurement_harness.expect``); ``aggregate`` reports pass counts per
kind."""
from esoi.optimization.measurement_harness import expect


def score_case(fn, case):
    return expect.score_kind_case(fn, case)


def aggregate(rows):
    return expect.aggregate_by_kind(rows)
