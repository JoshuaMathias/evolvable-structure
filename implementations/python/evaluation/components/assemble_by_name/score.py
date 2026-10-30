"""Score one assembly case against its declarative ``expect`` (see ``esoi.expect``); ``aggregate`` reports pass counts per kind."""
from esoi import expect


def score_case(fn, case):
    return expect.score_kind_case(fn, case)


def aggregate(rows):
    return expect.aggregate_by_kind(rows)
