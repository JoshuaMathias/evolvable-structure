"""CURRENT: ``esoi.evidence.estimates`` and ``esoi.evidence.rank``. Zero model calls."""
from esoi import evidence
from . import live


def build(meter):
    return live.runner(evidence.estimates, lambda rows, dims, today: evidence.rank(rows, dims, today=today))
