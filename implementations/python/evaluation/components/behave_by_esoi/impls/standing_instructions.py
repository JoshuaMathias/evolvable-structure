"""The author's skill loaded as standing instructions: the bundled SKILL.md is the system text of every call, then the
model judge grades the reply (the regex ``must_not`` patterns are a prefilter). One model call per case plus the judge
call, which costs money: run only after Joshua has approved the spend (structure/metric-run-policy.md). The setting is a
bare chat with no tools, so it measures the instruction layer alone."""
import model_arms
from esoi import skill

PAID = True
SKILL_FILE = skill.BUNDLED / "evolvable-structure" / skill.SKILL_FILE


def build(meter):
    chosen = model_arms.provider(meter)
    system = SKILL_FILE.read_text(encoding="utf-8")

    def respond(case):
        return chosen.answer([{"role": "user", "content": case["scenario"]}], model=model_arms.model(), system=system)
    respond.judge = model_arms.judge(meter)
    return respond
