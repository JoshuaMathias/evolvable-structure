"""VALIDITY: the regex checks alone as a judge (every ``must_have`` matches, no ``must_not``). Zero model calls. It agrees
with the author's labels by construction, because the same author wrote the recorded replies and the regexes, so it is the
metric's own check that the labels are consistent and a comparator that makes the circularity visible. It is not evidence
the regexes are right and never a rival to a judge."""
from esoi import behaviour


def build(meter):
    def grade(case):
        problems = behaviour.regex_problems(case["reply"], case["behavior_case"])
        return {"verdict": "fail" if problems else "pass", "reason": "; ".join(problems)[:80]}
    return grade
