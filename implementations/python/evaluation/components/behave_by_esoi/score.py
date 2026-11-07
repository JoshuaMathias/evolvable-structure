"""Score one ESOI behaviour case: a regex check, or a model judge with the regexes as its prefilter. The grading lives in
``esoi.understanding.esoi_for_ai.behaviour``; ``aggregate`` reports pass counts per primary principle and, for a judged run, where the regexes and
the judge disagree."""
from esoi.understanding.esoi_for_ai.interface import behaviour_aggregate, score_reply


def score_case(fn, case):
    return score_reply(fn(case), case, getattr(fn, "judge", None))


def aggregate(rows):
    return behaviour_aggregate(rows)
