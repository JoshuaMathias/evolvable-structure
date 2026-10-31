"""Score one public-evidence case against its declarative ``expect`` (see ``esoi.expect``)."""
from esoi import expect


def score_case(fn, case):
    return expect.score_kind_case(fn, case)
