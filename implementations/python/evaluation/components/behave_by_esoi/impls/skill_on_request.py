"""The author's skill available on request: the agent sees only the skill's name and description and decides whether to
load it (one call); when it does, the full SKILL.md is the system text of the answer (a second call); then the model judge
grades the reply. Two to three model calls per case, which costs money: run only after Joshua has approved the spend
(structure/metric-run-policy.md). It measures the loading decision as well as the instructions."""
import model_arms
from esoi import behaviour, skill

PAID = True
SKILL_PATH = skill.BUNDLED / "evolvable-structure" / skill.SKILL_FILE
DECIDE = ("You are a helpful assistant. You may load a skill before answering. The skill is {description}\n\n"
          "Reply with only YES if the skill applies to the message below, otherwise only NO.")


def build(meter):
    chosen = model_arms.provider(meter)
    text = SKILL_PATH.read_text(encoding="utf-8")
    decide_system = DECIDE.format(description=behaviour.skill_description(text))

    def respond(case):
        message = [{"role": "user", "content": case["scenario"]}]
        loads = chosen.answer(message, model=model_arms.model(), system=decide_system).strip().upper().startswith("YES")
        system = text if loads else "You are a helpful assistant."
        return chosen.answer(message, model=model_arms.model(), system=system)
    respond.judge = model_arms.judge(meter)
    return respond
