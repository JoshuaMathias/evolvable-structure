"""The model judge of ``esoi.behaviour``: one model call per recorded reply, graded against the case's expected behavior and
failure mode (never the regexes or the other reply). It costs money: run only after Joshua has approved the spend
(structure/metric-run-policy.md). The judge and the model that wrote a reply may be the same model, and then the judge may
favour its own phrasing; this metric measures agreement with the labels and does not remove that risk."""
import model_arms
from esoi import behaviour

PAID = True


def build(meter):
    judge = behaviour.build_judge(model_arms.provider(meter), model_arms.judge_model())

    def grade(case):
        passed, reason = judge(case["behavior_case"], case["reply"])
        return {"verdict": "pass" if passed else "fail", "reason": reason}
    return grade
