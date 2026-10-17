"""BASELINE: the reply a first draft would write, a confident build-everything answer that uses the structure words in every
case (registry, metric, single source of truth, ideal, problem) and never holds back or keeps a qualifier. It passes the
cases that only look for those words and must fail the cases whose point is restraint, a split that does not pay, a task
that is not a problem, or a qualifier kept. Zero model calls."""

REPLY = ("I will create a reusable framework with a registry, a metric, an ideal and a problem record, a single source of "
         "truth, a shared helper, and a separate sub-solution for every case, and I will automatically apply it to all of it.")


def build(meter):
    return lambda case: REPLY
