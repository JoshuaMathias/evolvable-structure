"""CURRENT: ``esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading.estimates`` and ``esoi.optimization.when_metrics_are_run.public_evidence.evidence_ranking.rank``. Zero model calls."""
from esoi.optimization.when_metrics_are_run.public_evidence.interface import estimates, rank
from . import live


def build(meter):
    return live.runner(estimates, lambda rows, dims, today: rank(rows, dims, today=today))
