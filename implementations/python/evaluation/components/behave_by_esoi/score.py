"""Score one ESOI behaviour case: a regex check, or a model judge with the regexes as its prefilter. The grading lives in
``esoi.behaviour``; ``aggregate`` reports pass counts per primary principle and, for a judged run, where the regexes and
the judge disagree."""
from esoi import behaviour


def score_case(fn, case):
    return behaviour.score_reply(fn(case), case, getattr(fn, "judge", None))


def aggregate(rows):
    return behaviour.aggregate(rows)
