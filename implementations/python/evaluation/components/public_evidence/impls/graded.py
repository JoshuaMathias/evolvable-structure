"""CURRENT: ``esoi.optimization.when_metrics_are_run.public_evidence.evidence_grading.estimates`` and ``esoi.optimization.when_metrics_are_run.public_evidence.evidence_ranking.rank``. Zero model calls."""
from esoi.optimization.when_metrics_are_run.public_evidence.interface import evidence_grading, evidence_ranking
from . import live


def build(meter):
    return live.runner(evidence_grading.estimates, lambda rows, dims, today: evidence_ranking.rank(rows, dims, today=today))
