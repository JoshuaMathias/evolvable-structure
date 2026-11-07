"""The author's skill loaded as standing instructions: the bundled SKILL.md is the system text of every call, then the
model judge grades the reply (the regex ``must_not`` patterns are a prefilter). One model call per case plus the judge
call, which costs money: run only after Joshua has approved the spend (structure/metric-run-policy.md). The setting is a
bare chat with no tools, so it measures the instruction layer alone."""
from shared_fixtures.interface import model_arms
from esoi.understanding.the_standard.skill_distribution.interface import BUNDLED, skill_SKILL_FILE

PAID = True
SKILL_FILE = BUNDLED / "evolvable-structure" / skill_SKILL_FILE


def build(meter):
    chosen = model_arms.provider(meter)
    system = SKILL_FILE.read_text(encoding="utf-8")

    def respond(case):
        return chosen.answer([{"role": "user", "content": case["scenario"]}], model=model_arms.model(), system=system)
    respond.judge = model_arms.judge(meter)
    return respond
