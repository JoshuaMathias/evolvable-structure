"""BASELINE: the same model with no ESOI instructions at all, so the gain from the skill is a number. One model call per
case plus the judge call, which costs money: run only after Joshua has approved the spend (structure/metric-run-policy.md)."""
import model_arms

PAID = True
SYSTEM = "You are a helpful assistant."


def build(meter):
    chosen = model_arms.provider(meter)

    def respond(case):
        return chosen.answer([{"role": "user", "content": case["scenario"]}], model=model_arms.model(), system=SYSTEM)
    respond.judge = model_arms.judge(meter)
    return respond
